"""Seguridad del visor privado: sin identidad validada no se sirve ningún archivo."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pack_private_worker import prepare


class PrivadoCloudflare(unittest.TestCase):
    def test_config_no_tiene_ruta_estatica_publica(self):
        text = (ROOT / "wrangler.jsonc").read_text(encoding="utf-8")
        text = "\n".join(line for line in text.splitlines()
                         if not line.lstrip().startswith("//"))
        conf = json.loads(text)
        self.assertEqual(conf["main"], "private/worker.mjs")
        self.assertNotIn("assets", conf)
        self.assertNotIn("routes", conf)

    def test_empaquetado_no_almacena_texto_plano_en_archivo_generado(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            site = root / "_site"
            (site / "data").mkdir(parents=True)
            (site / "index.html").write_text("<h1>Mi calendario</h1>", encoding="utf-8")
            (site / "data" / "carreras.json").write_text(
                '{"carreras":[{"nombre":"Carrera de prueba"}]}', encoding="utf-8")
            output = root / "private" / "generated.mjs"
            result = prepare(site, output)
            self.assertEqual(result["archivos"], 2)
            content = output.read_text(encoding="utf-8")
            self.assertIn("export const FILES", content)
            self.assertNotIn("Carrera de prueba", content)
            self.assertNotIn("Mi calendario", content)

    @unittest.skipUnless(shutil.which("node"), "Node necesario para probar el Worker")
    def test_anonimos_ajenos_y_fallos_no_acceden_a_json(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            site = root / "_site"
            (site / "data").mkdir(parents=True)
            (site / "index.html").write_text("privado", encoding="utf-8")
            (site / "data" / "carreras.json").write_text('{"carreras":[1]}', encoding="utf-8")
            dest = root / "private"
            dest.mkdir()
            shutil.copy2(ROOT / "private" / "worker.mjs", dest / "worker.mjs")
            prepare(site, dest / "generated.mjs")
            script = r"""
import { pathToFileURL } from 'node:url';
const worker = (await import(pathToFileURL(process.argv[1]).href)).default;
const env = {CORRERADAR_PRIVATE_EMAIL:'persona@example.org'};
const url = new Request('https://private.example.org/data/carreras.json');
const absent = await worker.fetch(url,env,{});
if (absent.status!==403) throw Error('JSON visible anónimamente');
const other = await worker.fetch(url,env,{
  access:{getIdentity:async()=>({email:'other@example.org'})}
});
if (other.status!==403) throw Error('Acceso desde otro correo');
const failed = await worker.fetch(url,env,{
  access:{getIdentity:async()=>{throw Error('identidad');}}
});
if (failed.status!==403) throw Error('Fallo de identidad abierto');
const noSecret = await worker.fetch(url,{CORRERADAR_PRIVATE_EMAIL:''},{
  access:{getIdentity:async()=>({email:'persona@example.org'})}
});
if (noSecret.status!==503) throw Error('Acceso sin configurar correo');
const good = await worker.fetch(url,env,{
  access:{getIdentity:async()=>({email:'PERSONA@example.org'})}
});
if (good.status!==200 || (await good.text())!=='{"carreras":[1]}')
  throw Error('Error al servir JSON autenticado');
if (good.headers.get('Cache-Control')!=='private, no-store')
  throw Error('Contenido privado cacheable');
const missing = await worker.fetch(new Request('https://private.example.org/absent'),env,{
  access:{getIdentity:async()=>({email:'persona@example.org'})}
});
if (missing.status!==404) throw Error('Ruta ausente mal gestionada');
console.log('Identidad obligatoria y JSON privado, OK');
"""
            result = subprocess.run(
                ["node", "--input-type=module", "-e", script, str(dest / "worker.mjs")],
                cwd=ROOT, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("JSON privado, OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
