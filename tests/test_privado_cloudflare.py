"""Seguridad del visor: sin identidad validada no se sirven archivos."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PrivadoCloudflare(unittest.TestCase):
    def test_config_siempre_procesa_worker_antes_que_assets(self):
        text = (ROOT / "wrangler.jsonc").read_text(encoding="utf-8")
        text = "\n".join(line for line in text.splitlines()
                         if not line.lstrip().startswith("//"))
        conf = json.loads(text)
        self.assertEqual(conf["assets"]["directory"], "./_site")
        self.assertEqual(conf["assets"]["binding"], "ASSETS")
        self.assertIs(conf["assets"]["run_worker_first"], True)

    @unittest.skipUnless(shutil.which("node"), "Node necesario para probar el Worker")
    def test_no_hay_bypass_ni_siquiera_para_json(self):
        script = r'''
const fs = require('fs');
(async () => {
 const js = fs.readFileSync('private/worker.js','utf8');
 const mod = await import('data:text/javascript,' + encodeURIComponent(js));
 let served = 0;
 const env = {
  CORRERADAR_PRIVATE_EMAIL: 'persona@example.org',
  ASSETS: {fetch: async () => {served++;return new Response('dato privado');}}
 };
 const url = new Request('https://demo.example.org/data/carreras.json');
 const noAccess = await mod.default.fetch(url,env,{});
 if (noAccess.status!==403 || served!==0) throw Error('Acceso anónimo permitido');
 const stranger = await mod.default.fetch(url,env,{
   access:{getIdentity:async()=>({email:'otro@example.org'})}
 });
 if (stranger.status!==403 || served!==0) throw Error('Acceso ajeno permitido');
 const broken = await mod.default.fetch(url,env,{
   access:{getIdentity:async()=>{throw Error('caído')}}
 });
 if (broken.status!==403 || served!==0) throw Error('Fallo de acceso abierto');
 const unconfigured = await mod.default.fetch(url,{
   ...env,CORRERADAR_PRIVATE_EMAIL:''
 },{access:{getIdentity:async()=>({email:'persona@example.org'})}});
 if (unconfigured.status!==503 || served!==0) throw Error('Secreto ausente permitido');
 const approved = await mod.default.fetch(url,env,{
   access:{getIdentity:async()=>({email:'PERSONA@example.org'})}
 });
 if (approved.status!==200 || served!==1) throw Error('Usuario válido bloqueado');
 if (approved.headers.get('Cache-Control')!=='private, no-store')
   throw Error('Respuesta cacheable');
 console.log('Worker privado: acceso cerrado salvo identidad verificada');
})().catch(e=>{console.error(e);process.exit(1)});
'''
        result = subprocess.run(["node", "-e", script], cwd=ROOT,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("acceso cerrado",result.stdout)


if __name__ == "__main__":
    unittest.main()
