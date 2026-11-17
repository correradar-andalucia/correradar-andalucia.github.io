"""Privacidad: titular persona física; nunca publicar datos no aportados."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build


class TitularPersonaFisica(unittest.TestCase):
    def test_configuracion_documenta_persona_fisica(self):
        config=json.loads((ROOT/"config"/"site.json").read_text(encoding="utf8"))
        self.assertEqual(config["holder_type"],"persona_fisica")
        self.assertFalse(config["public_launch"])
        self.assertFalse(config["legal_review_complete"])

    def test_privacidad_no_esconde_la_identidad_del_responsable(self):
        page=build.legal_pages()["privacidad"][1]
        self.assertIn("persona física que actúa en nombre propio",page)
        self.assertIn("no una sociedad ni una asociación",page)
        self.assertIn("CorreRadar Andalucía",page)
        self.assertIn("correradarandalucia@gmail.com",page)
        self.assertIn("ejercicio de derechos",page)

    def test_no_inventa_nombre_y_apellidos(self):
        page=build.legal_pages()["privacidad"][1]
        if not build.LEGAL_NAME:
            self.assertIn("[NOMBRE Y APELLIDOS DEL TITULAR PENDIENTES]",page)
            self.assertIn("antes del lanzamiento",page)

    def test_aviso_legal_usa_responsable_persona_fisica(self):
        page=build.legal_pages()["aviso-legal"][1]
        self.assertIn("Persona física responsable, en nombre propio",page)
        self.assertIn("Información legal en revisión",page)


if __name__=="__main__":
    unittest.main()
