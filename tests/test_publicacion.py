"""Regresión de continuidad desde Pages hasta el despliegue y los avisos."""
from contextlib import chdir, redirect_stdout
from copy import deepcopy
from datetime import date
from functools import partial
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build
from continuidad import ContinuityError, HTTPStatusError, PUBLICATION, snapshot, verified_snapshot
from control_calidad import inspect_calendar
from persistencia import restore_missing
import publicacion as publication
from test_continuidad import batch
from test_persistencia import TODAY, item, report

ORIGIN = {"esquema": 1, "commit": "a" * 40, "ejecucion": "123", "intento": "1",
          "fecha": "2026-11-18T09:00:00Z"}
RUN = {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_REF": publication.MAIN}
ROWS = [dict(row, fecha_origen="fuente", distancia_origen="fuente") for row in batch()]


def calendar(rows=ROWS, *, origin=None):
    doc = {"actualizado": "18/11/2026", "carreras": rows}
    if origin:
        doc[PUBLICATION] = origin
    return publication.encoded(doc)


def get_state(confirmed=None, pending=None):
    return {"esquema": 1, "confirmado": confirmed, "pendiente": pending}


class CalendarReferenceTests(unittest.TestCase):
    def setUp(self):
        self.raw = calendar()
        self.backup = snapshot(self.raw, ORIGIN)
        self.log = Mock()

    def select(self, page, backup):
        return publication.select_reference(page, backup, self.log)

    def test_pages_first_and_bootstrap(self):
        self.assertEqual(self.select(lambda: self.raw, None), self.raw)
        self.assertEqual(self.select(lambda: self.raw, dict(self.backup, calendario="rotura")), self.raw)
        self.log.assert_called_with("Referencia elegida: calendario público de GitHub Pages")

    def test_http_error_selects_confirmed_copy(self):
        with patch("continuidad.build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError(
                "https://example.org/data/carreras.json", 503, "Unavailable", {}, None)
            self.assertEqual(self.select(partial(publication.page_calendar, "123", "1"), self.backup), self.raw)
        self.assertIn("HTTP 503", self.log.call_args_list[0].args[0])

    def test_corrupt_empty_invalid_and_stale_pages_select_confirmed_copy(self):
        for bad in (b"no es JSON", b"", calendar([]), calendar([{}, None]),
                    calendar(ROWS[:1]), calendar([ROWS[0], ROWS[0]]),
                    b'{"actualizado":0,"carreras":null}', b'{"carreras":[],"carreras":[]}'):
            with self.subTest(bad=bad[:100]):
                self.assertEqual(self.select(lambda: bad, self.backup), self.raw)

    def test_no_valid_reference_blocks_and_removes_stale_local_file(self):
        invalid = dict(self.backup, sha256="0" * 64)
        for copy in (None, invalid, dict(self.backup, calendario="{}"),
                     dict(self.backup, publicacion=dict(ORIGIN, esquema=2))):
            with self.subTest(copy=bool(copy)), TemporaryDirectory() as tmp:
                path = Path(tmp) / "anterior.json"
                path.write_bytes(self.raw)
                journal = Mock()
                journal.load.return_value = ("", get_state(copy))
                with patch.dict(os.environ, RUN), patch("publicacion.page_calendar", return_value=b"{{"), \
                     patch("publicacion.log"):
                    with self.assertRaisesRegex(ContinuityError, "No hay una referencia válida"):
                        publication.resolve(journal, Mock(), path)
                self.assertFalse(path.exists())

    def test_build_blocks_before_capture_without_valid_reference(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "anterior.json"
            for raw in (None, b"corrupto", calendar([]), calendar([{}])):
                if raw is not None:
                    path.write_bytes(raw)
                with self.subTest(raw=raw), patch.dict(os.environ, {
                    "CORRERADAR_FETCH": "1", "CORRERADAR_PREVIOUS_CALENDAR": str(path),
                }), patch("captacion.collect") as collect:
                    with self.assertRaisesRegex(ContinuityError, "referencia de continuidad"):
                        build.main()
                    collect.assert_not_called()

    def test_six_missing_races_block_the_real_build_with_the_fallback(self):
        rep = report(fallo_temporal=False)
        rep.update(nombres_fuentes_habilitadas=["runnink", "faa", "dorsalchip"],
                   fuentes_con_consulta_habilitada=3)
        rep["fuentes"].update(faa={"estado": "leida"}, dorsalchip={"estado": "leida"})
        current = [item(nombre="Carrera presente", origen="faa", fecha_origen="fuente",
                        distancia_origen="fuente", slug="carrera-presente")]
        # La combinación aún parece apta con el anterior comportamiento de lista vacía.
        self.assertTrue(inspect_calendar(current, rep, TODAY)["apto_para_desplegar"])
        with TemporaryDirectory() as tmp:
            target = Path(tmp)
            prior, output = target / "anterior.json", target / "_site"
            output.mkdir()
            previous_site = output / "index.html"
            previous_site.write_text("Sitio anterior", encoding="utf-8")
            journal = Mock()
            journal.load.return_value = ("1" * 40, get_state(self.backup))
            env = RUN | {"GITHUB_OUTPUT": str(target / "output"), "CORRERADAR_FETCH": "1",
                         "CORRERADAR_PREVIOUS_CALENDAR": str(prior), "SHEET_CSV_URL": ""}
            with patch.dict(os.environ, env), patch("publicacion.page_calendar", return_value=b"{"), \
                 patch("publicacion.log"), patch("captacion.collect", return_value=([], rep)), \
                 patch("deduplicacion.combine", return_value=(current, {})), patch("build.OUT", output), \
                 patch("persistencia.restore_missing", wraps=partial(restore_missing, today=TODAY)), \
                 patch("control_calidad.inspect_calendar", wraps=partial(inspect_calendar, today=TODAY)):
                publication.resolve(journal, Mock(), prior)
                with self.assertRaisesRegex(ValueError, r"Pérdida anómala.*runnink: 6"):
                    build.main()
            self.assertEqual(previous_site.read_text(encoding="utf-8"), "Sitio anterior")

    def test_expired_and_restricted_sources_stay_out_of_the_recovery(self):
        rep = report(fallo_temporal=True)
        for restriction in ("acceso_restringido", "detalle_restringido"):
            rep["fuentes"]["runnink"][restriction] = True
        rows = []
        self.assertEqual(restore_missing(rows, ROWS, rep, build.slugify, build.km_parse, TODAY)["recuperadas"], 0)
        rep = report(fallo_temporal=True)
        self.assertEqual(restore_missing(rows, ROWS, rep, build.slugify, build.km_parse,
                                         date(2026, 11, 25))["recuperadas"], 0)
        checked = ROWS[0]
        new = dict(checked, distancia="")
        result = build.preserve_previous_distances([new], [checked], TODAY, capture_report=report(acceso_restringido=True))
        self.assertEqual(result["recuperadas"], 0)
        self.assertEqual(rows, [])


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        work = self.enterContext(TemporaryDirectory())
        self.enterContext(patch.dict(os.environ, RUN | {"GITHUB_OUTPUT": str(Path(work) / "outputs")}))
        self.enterContext(patch("publicacion.ensure_main"))
        self.enterContext(redirect_stdout(StringIO()))
        self.path = Path(work) / "carreras.json"
        self.path.write_bytes(calendar(origin=ORIGIN))
        self.previous = snapshot(calendar(ROWS[:1]), dict(ORIGIN, ejecucion="122"))
        self.journal = Mock()
        self.journal.load.return_value = ("1" * 40, get_state(deepcopy(self.previous)))
        self.writes = []
        self.journal.write.side_effect = self.write
        self.pages = Mock()
        self.pages.oidc_token.return_value = "token"
        self.pages.start.return_value = "ID-NATIVO"
        self.pages.wait.return_value = "succeed"

    def write(self, head, state):
        self.writes.append((head, deepcopy(state)))
        new = str(len(self.writes) + 1) * 40
        self.journal.load.return_value = (new, deepcopy(state))
        return new

    def deploy(self):
        publication.deploy(self.journal, self.pages, self.path, "42", "1" * 40, "1")

    def test_failed_deployment_never_becomes_backup(self):
        self.pages.wait.return_value = "deployment_content_failed"
        with self.assertRaisesRegex(ContinuityError, "fallido"):
            self.deploy()
        self.assertEqual(self.writes[-1][1], get_state(self.previous))
        self.assertEqual(self.writes[0][1]["pendiente"]["id"], None)
        self.assertEqual(self.writes[1][1]["pendiente"]["id"], "ID-NATIVO")

    def test_explicit_post_rejection_preserves_copy_and_ambiguous_failure_blocks(self):
        self.pages.start.side_effect = HTTPStatusError(403)
        with self.assertRaisesRegex(ContinuityError, "rechazó"):
            self.deploy()
        self.assertEqual(self.writes[-1][1], get_state(self.previous))
        self.journal.load.return_value = ("1" * 40, get_state(self.previous))
        self.pages.start.side_effect = HTTPStatusError(502)
        with self.assertRaises(HTTPStatusError):
            self.deploy()
        with self.assertRaisesRegex(ContinuityError, "sin identificador"):
            publication.reconcile(self.writes[-1][1], self.pages)

    def test_success_is_saved_even_if_notifications_fail(self):
        self.deploy()
        publication.guard_notices(self.journal, "1")
        with self.assertRaises(RuntimeError):
            Mock(side_effect=RuntimeError("Issues no disponible"))()
        saved = self.writes[-1][1]["confirmado"]
        self.assertEqual(verified_snapshot(saved), self.path.read_bytes())
        self.assertEqual(saved["sha256"], sha256(self.path.read_bytes()).hexdigest())

    def test_interruption_after_submit_uses_only_confirmed_native_status(self):
        self.pages.wait.side_effect = ContinuityError("Tiempo agotado")
        with self.assertRaisesRegex(ContinuityError, "Tiempo agotado"):
            self.deploy()
        state = self.writes[-1][1]
        self.assertEqual(state["confirmado"], self.previous)
        for status in ("deployment_in_progress", "deployment_lost"):
            self.pages.status.return_value = status
            with self.assertRaisesRegex(ContinuityError, "sin confirmación definitiva"):
                publication.reconcile(state, self.pages)
        self.pages.status.return_value = "deployment_failed"
        self.assertEqual(publication.reconcile(state, self.pages), get_state(self.previous))
        self.pages.status.return_value = "succeed"
        confirmed = publication.reconcile(state, self.pages)["confirmado"]
        raw = publication.select_reference(lambda: b"rotura", confirmed, Mock())
        self.assertEqual(raw, self.path.read_bytes())

    def test_failed_job_retry_and_changed_baseline_are_rejected_before_deploy(self):
        with patch.dict(os.environ, {"GITHUB_RUN_ATTEMPT": "2"}):
            with self.assertRaisesRegex(ContinuityError, "Re-run all jobs"):
                self.deploy()
        self.journal.load.return_value = ("2" * 40, get_state(self.previous))
        with self.assertRaisesRegex(ContinuityError, "referencia cambió"):
            self.deploy()
        self.journal.write.assert_not_called()
        self.pages.start.assert_not_called()

    def test_notice_retry_requires_the_latest_deployed_attempt(self):
        self.deploy()
        with patch.dict(os.environ, {"GITHUB_RUN_ATTEMPT": "2"}):
            publication.guard_notices(self.journal, "1")
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "124"}):
            with self.assertRaisesRegex(ContinuityError, "ya no corresponde"):
                publication.guard_notices(self.journal, "1")

    def test_legacy_initialization_requires_success_and_verified_bytes(self):
        args = Mock(estado="sin-inicializar", despliegue="ID-LEGADO", calendario=self.path,
                    descartar_intento_sin_id=False,
                    commit=ORIGIN["commit"], ejecucion="123", intento="1", fecha=ORIGIN["fecha"])
        self.journal.load.return_value = ("", get_state())
        self.path.write_bytes(calendar())
        args.sha256 = sha256(self.path.read_bytes()).hexdigest()
        with patch("publicacion.remote_head", return_value=""):
            self.pages.status.return_value = "deployment_failed"
            with self.assertRaisesRegex(ContinuityError, "haya tenido éxito"):
                publication.recover(self.journal, self.pages, args)
            self.pages.status.return_value = "succeed"
            with patch.object(args, "sha256", "0" * 64):
                with self.assertRaisesRegex(ContinuityError, "SHA-256 no coincide"):
                    publication.recover(self.journal, self.pages, args)
            publication.recover(self.journal, self.pages, args)
        self.assertEqual(verified_snapshot(self.writes[-1][1]["confirmado"]), calendar())


class PagesApiTests(unittest.TestCase):
    def test_native_pages_endpoint_and_signed_artifact_request(self):
        env = {"ACTIONS_ID_TOKEN_REQUEST_URL": "https://oidc.example.org/token",
               "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "runner-token", "GH_TOKEN": "repo-token",
               "GITHUB_API_URL": "https://api.github.com", "GITHUB_REPOSITORY": "org/calendario",
               "GITHUB_SHA": "d" * 40}
        pages = publication.Pages()
        with patch.dict(os.environ, env), patch("publicacion.read_http", side_effect=[
            b'{"value":"oidc"}', b'{"id":"clave","page_url":"https://org.github.io/"}',
            b'{"status":"succeed"}',
        ]) as http:
            native = pages.start("42", pages.oidc_token())
            self.assertEqual(pages.status(native), "succeed")
        oidc, submit, verify = http.call_args_list
        self.assertEqual(oidc.args[0], env["ACTIONS_ID_TOKEN_REQUEST_URL"])
        self.assertEqual(oidc.kwargs["headers"]["Authorization"], "Bearer runner-token")
        endpoint = "https://api.github.com/repos/org/calendario/pages/deployments"
        self.assertEqual(submit.args[0], endpoint)
        self.assertEqual(json.loads(submit.kwargs["data"]), {
            "artifact_id": 42, "oidc_token": "oidc", "pages_build_version": "d" * 40,
        })
        self.assertEqual(verify.args[0], f"{endpoint}/clave")
        self.assertIsNone(verify.kwargs["data"])


class JournalTests(unittest.TestCase):
    def test_git_compare_and_swap_and_one_version_retention(self):
        def run(*args):
            return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()

        with TemporaryDirectory() as tmp, chdir(tmp):
            run("init", "--bare", "remote.git")
            run("init", "writer")
            with chdir("writer"):
                run("remote", "add", "origin", "../remote.git")
                journal = publication.Journal()
                self.assertEqual(journal.load(), ("", get_state()))
                first = journal.write("", get_state())
                self.assertEqual(journal.load()[0], first)
                copy = snapshot(calendar(), ORIGIN)
                latest = journal.write(first, get_state(copy))
                self.assertEqual(journal.load(), (latest, get_state(copy)))
                self.assertEqual(run("rev-list", "--count", latest), "1")
                with self.assertRaisesRegex(ContinuityError, "No se pudo actualizar el diario"):
                    journal.write(first, get_state())
                self.assertEqual(journal.load(), (latest, get_state(copy)))


class WorkflowContractTests(unittest.TestCase):
    def test_both_publishers_share_continuity_and_notify_only_after_save(self):
        for name, deploy_job, notices in (("publicar", "deploy", "needs: [build, deploy]"),
                                         ("aprobar-enlace-globaltempo", "desplegar", "needs: [aprobar, desplegar]")):
            with self.subTest(workflow=name):
                workflow = (ROOT / ".github/workflows" / f"{name}.yml").read_text()
                self.assertIn("github-pages", workflow)
                self.assertIn("cancel-in-progress: false", workflow)
                self.assertIn(notices, workflow)
                self.assertIn("CORRERADAR_PREVIOUS_CALENDAR:", workflow)
                entry_points = ("publicacion.py resolver", "scripts/build.py", "scripts/verificar_salida.py",
                                "publicacion.py marcar", "actions/upload-pages-artifact@v4",
                                f"\n  {deploy_job}:", "publicacion.py desplegar", notices,
                                "publicacion.py avisos")
                positions = [workflow.index(entry) for entry in entry_points]
                self.assertEqual(positions, sorted(positions))
                self.assertIn("github-pages-${{ github.run_attempt }}", workflow)
                self.assertNotIn("data/carreras.json -o", workflow)


if __name__ == "__main__":
    unittest.main()
