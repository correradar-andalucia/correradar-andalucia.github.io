"""El artefacto de GitHub Pages debe ser completo y no indexable antes del lanzamiento."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from verificar_salida import verify_output

PRELAUNCH={"public_launch":False}
ROBOTS='<meta name="robots" content="noindex,nofollow">'


class VerificacionSalida(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.slug="carrera-sevilla-2026-12-20"
        for path in ("assets/app.js","assets/styles.css","robots.txt","sitemap.xml",
                     "data/estado_fuentes.json"):
            target=self.root/path
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text("prueba",encoding="utf-8")
        (self.root/"index.html").write_text(f"<html><head>{ROBOTS}</head></html>",
                                            encoding="utf-8")
        (self.root/"data"/"carreras.json").write_text(
            json.dumps({"carreras":[{"slug":self.slug}]}),encoding="utf-8")
        (self.root/"data"/"control_calidad.json").write_text(
            json.dumps({"apto_para_desplegar":True,"total_carreras":1}),
            encoding="utf-8")
        (self.root/"data"/"globaltempo_enlaces.json").write_text(
            json.dumps({"enlaces":[]}),encoding="utf-8")
        detail=self.root/"carreras"/self.slug/"index.html"
        detail.parent.mkdir(parents=True)
        detail.write_text(f"<html><head>{ROBOTS}</head></html>",encoding="utf-8")
        self.detail=detail

    def test_artefacto_completo(self):
        result=verify_output(self.root,PRELAUNCH)
        self.assertEqual(result["fichas_verificadas"],1)
        self.assertTrue(result["prelanzamiento_noindex"])

    def test_proteger_portada(self):
        (self.root/"index.html").write_text("<html><head></head></html>",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"Portada"):
            verify_output(self.root,PRELAUNCH)

    def test_proteger_detalle(self):
        self.detail.write_text("<html><head></head></html>",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"Ficha indexable"):
            verify_output(self.root,PRELAUNCH)

    def test_no_dejar_fichas_rotas(self):
        self.detail.unlink()
        with self.assertRaisesRegex(ValueError,"Ficha no generada"):
            verify_output(self.root,PRELAUNCH)

    def test_calidad_incorrecta_impide_publicar(self):
        (self.root/"data"/"control_calidad.json").write_text(
            json.dumps({"apto_para_desplegar":False,"total_carreras":1}),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"Informe de calidad"):
            verify_output(self.root,PRELAUNCH)

    def test_no_aceptar_lanzamiento_legal_sin_aprobacion(self):
        with self.assertRaisesRegex(ValueError,"LANZAMIENTO BLOQUEADO"):
            verify_output(self.root,{"public_launch":True})


if __name__=="__main__":
    unittest.main()
