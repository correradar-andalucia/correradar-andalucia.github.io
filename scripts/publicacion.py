"""Coordina la referencia, el diario Git y el despliegue nativo de GitHub Pages."""
from argparse import ArgumentParser
from datetime import datetime, UTC
from functools import partial
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlparse

from continuidad import (
    COMMIT, PUBLICATION, RUN_NUMBER, SCHEMA, ContinuityError, HTTPStatusError, check_publication,
    decode_json, matches, page_calendar, parse_calendar, read_calendar, read_http, select_reference,
    snapshot, verified_snapshot,
)

REF = "refs/heads/estado-correradar-continuidad"
MAIN = "refs/heads/main"
DEPLOYMENT_ID = re.compile(r"[a-zA-Z0-9_-]{1,100}")
TERMINAL_FAILURES = {
    "deployment_failed", "deployment_perms_error", "deployment_content_failed",
    "deployment_cancelled",
}
REJECTED_REQUESTS = {400, 401, 403, 404, 422}
STATE_MAX_BYTES = 16_000_000


def log(message):
    print(message, flush=True)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as summary:
            summary.write(f"- {message}\n")


def encoded(document):
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode()


def git(*args, data=None):
    result = subprocess.run(["git", *args], input=data, capture_output=True, check=False)
    if result.returncode:
        raise ContinuityError(f"Git {args[0]} falló (código {result.returncode})")
    return result.stdout


def remote_head(ref):
    output = git("ls-remote", "--refs", "origin", ref).decode().splitlines()
    if not output:
        return ""
    fields = output[0].split()
    if len(output) != 1 or len(fields) != 2 or fields[1] != ref or not matches(COMMIT, fields[0]):
        raise ContinuityError("Git devolvió una referencia remota inválida")
    return fields[0]


class Journal:
    """Un único commit alcanzable con la última copia y, durante el despliegue, el candidato."""

    def load(self):
        head = remote_head(REF)
        if not head:
            return head, {"esquema": SCHEMA, "confirmado": None, "pendiente": None}
        git("fetch", "--quiet", "--no-tags", "--depth=1", "origin", REF)
        if git("rev-parse", "FETCH_HEAD").decode().strip() != head:
            raise ContinuityError("Cambió el diario mientras se leía. Repite la ejecución completa")
        if int(git("cat-file", "-s", f"{head}:estado.json")) > STATE_MAX_BYTES:
            raise ContinuityError("Diario de continuidad demasiado grande")
        state = decode_json(git("show", f"{head}:estado.json"), "Diario de continuidad")
        if (not isinstance(state, dict) or state.keys() != {"esquema", "confirmado", "pendiente"}
                or type(state["esquema"]) is not int or state["esquema"] != SCHEMA):
            raise ContinuityError("Diario de continuidad con esquema inválido")
        return head, state

    def write(self, head, state):
        blob = git("hash-object", "-w", "--stdin", data=encoded(state)).strip()
        tree = git("mktree", data=b"100644 blob " + blob + b"\testado.json\n").decode().strip()
        commit = git("-c", "user.name=github-actions[bot]",
                     "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                     "commit-tree", tree, "-m", "Actualizar continuidad de GitHub Pages").decode().strip()
        try:
            git("push", "--quiet", f"--force-with-lease={REF}:{head}", "origin", f"{commit}:{REF}")
        except ContinuityError as exc:
            raise ContinuityError("No se pudo actualizar el diario: revisa su SHA remoto, "
                                  "el permiso contents: write y las reglas de esa rama") from exc
        return commit


class Pages:
    """La API de Pages usa el artefacto oficial y el token OIDC del job github-pages."""

    def api(self, suffix="", data=None):
        origin = os.environ.get("GITHUB_API_URL", "https://api.github.com")
        url = f"{origin}/repos/{os.environ['GITHUB_REPOSITORY']}/pages/deployments{suffix}"
        headers = {"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                   "Accept": "application/vnd.github+json", "Content-Type": "application/json",
                   "X-GitHub-Api-Version": "2022-11-28"}
        result = decode_json(read_http(url, limit=100_000, headers=headers, data=data), "API de Pages")
        if not isinstance(result, dict):
            raise ContinuityError("La API de Pages devolvió un objeto inválido")
        return result

    def oidc_token(self):
        url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
        if urlparse(url).scheme != "https":
            raise ContinuityError("URL de OIDC insegura")
        headers = {"Authorization": f"Bearer {os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']}",
                   "Accept": "application/json"}
        result = decode_json(read_http(url, limit=100_000, headers=headers), "OIDC de GitHub")
        if not isinstance(result, dict) or not isinstance(result.get("value"), str) or not result["value"]:
            raise ContinuityError("OIDC de GitHub no devolvió un token")
        return result["value"]

    def start(self, artifact_id, token):
        response = self.api(data=encoded({"artifact_id": int(artifact_id), "oidc_token": token,
                                          "pages_build_version": os.environ["GITHUB_SHA"]}))
        value = response.get("id")
        if value is None and isinstance(response.get("status_url"), str):
            value = urlparse(response["status_url"]).path.rsplit("/", 1)[-1]
        if not matches(DEPLOYMENT_ID, str(value)) or value is None:
            raise ContinuityError("La API de Pages no devolvió un identificador de despliegue válido")
        return str(value)

    def status(self, deployment_id):
        if not matches(DEPLOYMENT_ID, deployment_id):
            raise ContinuityError("Identificador de despliegue inválido")
        status = self.api(f"/{deployment_id}").get("status")
        if not isinstance(status, str) or not re.fullmatch("[a-z_]{1,60}", status):
            raise ContinuityError("La API de Pages devolvió un estado inválido")
        return status

    def wait(self, deployment_id):
        deadline = time.monotonic() + 540
        previous = None
        while time.monotonic() < deadline:
            try:
                status = self.status(deployment_id)
            except ContinuityError as exc:
                status = f"consulta fallida ({exc})"
            if status != previous:
                log(f"Despliegue Pages {deployment_id}: {status}")
                previous = status
            if status == "succeed" or status in TERMINAL_FAILURES:
                return status
            time.sleep(5)
        raise ContinuityError(f"Despliegue Pages {deployment_id} sin resultado definitivo; "
                              "el siguiente intento consultará su estado")


def reconcile(state, pages):
    pending = state["pendiente"]
    if pending is None:
        return state
    if (not isinstance(pending, dict) or pending.keys() != {"id", "copia"}
            or not matches(DEPLOYMENT_ID, pending["id"])):
        raise ContinuityError("Hay un intento pendiente sin identificador verificable. "
                              "Consulta el procedimiento de recuperación en el manual")
    deployment_id = pending["id"]
    status = pages.status(deployment_id)
    log(f"Reconciliación del despliegue Pages {deployment_id}: {status}")
    if status == "succeed":
        if not isinstance(pending["copia"], dict):
            raise ContinuityError("Falta la copia del despliegue que Pages confirmó")
        return {**state, "confirmado": dict(pending["copia"], despliegue=deployment_id), "pendiente": None}
    if status in TERMINAL_FAILURES:
        return {**state, "pendiente": None}
    raise ContinuityError(f"El despliegue Pages {deployment_id} sigue sin confirmación definitiva "
                          f"({status}); se conserva la referencia previa")


def current_run():
    run_id = os.environ.get("GITHUB_RUN_ID")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    if not matches(RUN_NUMBER, run_id) or not matches(RUN_NUMBER, attempt):
        raise ContinuityError("Ejecución o intento de GitHub Actions inválidos")
    return run_id, attempt


def ensure_main(commit):
    if os.environ.get("GITHUB_REF") != MAIN or not matches(COMMIT, commit) or remote_head(MAIN) != commit:
        raise ContinuityError("El código generado no coincide con main. Ejecuta un flujo nuevo desde main")


def resolve(journal, pages, destination):
    run_id, attempt = current_run()
    destination.unlink(missing_ok=True)
    head, state = journal.load()
    state = reconcile(state, pages)
    raw = select_reference(partial(page_calendar, run_id, attempt), state["confirmado"], log)
    destination.write_bytes(raw)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"estado={head or 'sin-inicializar'}\nintento={attempt}\n")


def mark_generation(path):
    run_id, attempt = current_run()
    commit = git("rev-parse", "HEAD").decode().strip()
    ensure_main(commit)
    _, doc = read_calendar(path)
    publication = {"esquema": SCHEMA, "commit": commit, "ejecucion": run_id, "intento": attempt,
                   "fecha": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")}
    doc[PUBLICATION] = check_publication(publication)
    raw = encoded(doc)
    snapshot(raw, publication)
    path.write_bytes(raw)
    if output_path := os.environ.get("GITHUB_OUTPUT"):
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"commit={commit}\n")


def deploy(journal, pages, path, artifact_id, baseline_head, attempt):
    run_id, actual_attempt = current_run()
    if attempt != actual_attempt or not matches(RUN_NUMBER, artifact_id):
        raise ContinuityError("Artefacto ajeno a este intento. Usa Re-run all jobs o inicia un flujo nuevo")
    raw, doc = read_calendar(path)
    publication = check_publication(doc.get(PUBLICATION))
    if (publication["ejecucion"], publication["intento"]) != (run_id, attempt):
        raise ContinuityError("La copia candidata no se generó en este intento")
    head, state = journal.load()
    if (head or "sin-inicializar") != baseline_head:
        raise ContinuityError("La referencia cambió durante la generación. Repite el flujo completo")
    state = reconcile(state, pages)
    confirmed = state["confirmado"]
    if confirmed is not None:
        try:
            verified_snapshot(confirmed)
        except ContinuityError:
            previous = select_reference(partial(page_calendar, run_id, attempt), confirmed, log)
            origin = parse_calendar(previous).get(PUBLICATION, confirmed.get("publicacion"))
            repaired = snapshot(previous, origin)
            if "despliegue" in confirmed:
                repaired["despliegue"] = confirmed["despliegue"]
            state["confirmado"] = repaired
            log("Copia anterior reparada con los bytes de GitHub Pages")
    candidate = snapshot(raw, publication)
    ensure_main(publication["commit"])
    token = pages.oidc_token()
    # Antes de solicitar el despliegue queda registrada la intención. Un POST de
    # resultado ambiguo jamás permite usar una copia previa potencialmente obsoleta.
    state["pendiente"] = {"id": None, "copia": candidate}
    head = journal.write(head, state)
    try:
        deployment_id = pages.start(artifact_id, token)
    except HTTPStatusError as exc:
        if exc.code in REJECTED_REQUESTS:
            state["pendiente"] = None
            journal.write(head, state)
            raise ContinuityError(f"Pages rechazó el despliegue ({exc}); "
                                  "la copia confirmada anterior sigue disponible") from exc
        raise
    log(f"GitHub Pages aceptó el despliegue {deployment_id}, commit {publication['commit']}, "
        f"ejecución {run_id}, intento {attempt}")
    state["pendiente"]["id"] = deployment_id
    head = journal.write(head, state)
    status = pages.wait(deployment_id)
    state["pendiente"] = None
    if status != "succeed":
        journal.write(head, state)
        raise ContinuityError(f"Despliegue Pages {deployment_id} fallido ({status}). "
                              "La copia confirmada anterior sigue disponible")
    state["confirmado"] = dict(candidate, despliegue=deployment_id)
    journal.write(head, state)
    log(f"Copia confirmada de GitHub Pages: despliegue {deployment_id}, SHA-256 {candidate['sha256']}")
    if output_path := os.environ.get("GITHUB_OUTPUT"):
        with open(output_path, "a", encoding="utf-8") as output:
            output.write("page_url=https://correradar-andalucia.github.io/\n")


def guard_notices(journal, attempt):
    run_id, _ = current_run()
    _, state = journal.load()
    if state["pendiente"] is not None:
        raise ContinuityError("Hay un despliegue pendiente; detener avisos")
    confirmed = state["confirmado"]
    verified_snapshot(confirmed)
    publication = confirmed["publicacion"]
    if (publication["ejecucion"], publication["intento"]) != (run_id, attempt):
        raise ContinuityError("Este intento ya no corresponde a la web publicada; detener avisos")


def associate(journal, pages, args):
    head, state = journal.load()
    if head != args.estado or not head:
        raise ContinuityError("El SHA del diario cambió; vuelve a revisar la evidencia")
    pending = state["pendiente"]
    if not isinstance(pending, dict) or pending.keys() != {"id", "copia"} or pending["id"] is not None:
        raise ContinuityError("El diario no contiene un intento pendiente sin ID")
    status = pages.status(args.despliegue)
    if status not in TERMINAL_FAILURES | {"succeed"}:
        raise ContinuityError("El despliegue indicado por el operador sigue sin resultado definitivo")
    if status == "succeed":
        candidate = verified_snapshot(pending["copia"])
        origin = pending["copia"]["publicacion"]
        if page_calendar(origin["ejecucion"], origin["intento"]) != candidate:
            raise ContinuityError("Pages no sirve los mismos bytes que el intento pendiente")
    pending["id"] = args.despliegue
    journal.write(head, {
        **state, "pendiente": None,
        "confirmado": (dict(pending["copia"], despliegue=args.despliegue)
                       if status == "succeed" else state["confirmado"]),
    })
    log(f"Diario reconciliado con el despliegue Pages {args.despliegue}")


def recover(journal, pages, args):
    # Operación extraordinaria deliberada. Casar el SHA del diario protege frente
    # a otro operador o workflow que haya publicado desde que se revisó la evidencia.
    head = remote_head(REF)
    if (head or "sin-inicializar") != args.estado:
        raise ContinuityError("El SHA del diario cambió; vuelve a revisar la evidencia")
    try:
        _, state = journal.load()
    except ContinuityError:
        # El procedimiento permite también reemplazar un diario ilegible. El
        # operador verifica Pages y su historial, y el push conserva el lease.
        state = None
    pending = state["pendiente"] if state else None
    if pending is not None and (not args.descartar_intento_sin_id
                                or not isinstance(pending, dict) or pending.get("id") is not None):
        raise ContinuityError("Resuelve primero el intento pendiente del diario")
    if pages.status(args.despliegue) != "succeed":
        raise ContinuityError("Pages no confirma que el despliegue indicado haya tenido éxito")
    raw, _ = read_calendar(args.calendario)
    if sha256(raw).hexdigest() != args.sha256:
        raise ContinuityError("El SHA-256 no coincide con el calendario revisado")
    origin = {"esquema": SCHEMA, "commit": args.commit, "ejecucion": args.ejecucion,
              "intento": args.intento, "fecha": args.fecha}
    candidate = snapshot(raw, origin)
    if pending is not None and page_calendar(args.ejecucion, args.intento) != raw:
        raise ContinuityError("Para descartar el intento sin ID, Pages debe servir la copia revisada")
    journal.write(head, {"esquema": SCHEMA, "confirmado": dict(candidate, despliegue=args.despliegue),
                         "pendiente": None})
    log(f"Copia extraordinaria guardada para el despliegue {args.despliegue} (SHA-256 {args.sha256})")


def main():
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("resolver").add_argument("destino", type=Path)
    commands.add_parser("marcar").add_argument("calendario", type=Path)
    deploy_parser = commands.add_parser("desplegar")
    deploy_parser.add_argument("calendario", type=Path)
    deploy_parser.add_argument("--artefacto", required=True)
    deploy_parser.add_argument("--estado", required=True)
    deploy_parser.add_argument("--intento", required=True)
    commands.add_parser("avisos").add_argument("--intento", required=True)
    association = commands.add_parser("asociar")
    association.add_argument("--despliegue", required=True)
    association.add_argument("--estado", required=True)
    recovery = commands.add_parser("recuperar")
    recovery.add_argument("calendario", type=Path)
    recovery.add_argument("--descartar-intento-sin-id", action="store_true")
    for field in ("despliegue", "estado", "sha256", "commit", "ejecucion", "intento", "fecha"):
        recovery.add_argument(f"--{field}", required=True)
    args = parser.parse_args()
    journal, pages = Journal(), Pages()
    try:
        if args.command == "resolver":
            resolve(journal, pages, args.destino)
        elif args.command == "marcar":
            mark_generation(args.calendario)
        elif args.command == "desplegar":
            deploy(journal, pages, args.calendario, args.artefacto, args.estado, args.intento)
        elif args.command == "avisos":
            guard_notices(journal, args.intento)
        elif args.command == "asociar":
            associate(journal, pages, args)
        else:
            recover(journal, pages, args)
    except (ContinuityError, OSError, KeyError) as exc:
        log(f"CONTINUIDAD BLOQUEADA: {exc}")
        parser.exit(1)


if __name__ == "__main__":
    main()
