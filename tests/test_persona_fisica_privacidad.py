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

    def test_titular_identificado_sin_pedir_dni_o_domicilio(self):
        self.assertEqual(build.LEGAL_NAME,"Iván Amador Dueñas")
        self.assertEqual(build.HOLDER_TYPE,"persona_fisica")
        legal=build.legal_pages()["aviso-legal"][1]
        privacy=build.legal_pages()["privacidad"][1]
        self.assertIn("Iván Amador Dueñas",legal)
        self.assertIn("Iván Amador Dueñas",privacy)
        self.assertNotIn("[NOMBRE Y APELLIDOS DEL TITULAR PENDIENTES]",privacy)
        self.assertNotIn("Es necesario identificar al titular",legal)
        self.assertTrue(self.config_em_brief()["public_launch"] is False)

    def config_em_brief(self):
        return json.loads((ROOT/"config"/"site.json").read_text(encoding="utf8"))

    def test_privacidad_revela_metodo_real_globaltempo_y_proveedores(self):
        text=build.legal_pages()["privacidad"][1]
        for item in ("Google Alerts","GitHub Actions","GitHub Pages","Gmail",
                     "incidencias","público","inscripciones",
                     "terceros países","no una consulta automática",
                     "plazo", "borrado automático"):
            with self.subTest(item=item):
                self.assertIn(item,text)
        self.assertIn("correradarandalucia@gmail.com",text)

    def test_auditoria_distingue_10_fuentes_y_permisos(self):
        from captacion import SOURCES
        audit=(ROOT/"docs"/"auditoria_fuentes_privacidad_2026-11-17.md").read_text(
            encoding="utf8")
        self.assertEqual(len(SOURCES),10)
        for key in SOURCES:
            self.assertIn(f"(`{key}`)",audit)
        self.assertIn("no se puede certificar",audit.lower())
        self.assertIn("artículo 133",audit)
        self.assertIn("Global Tempo",audit)
        self.assertIn("autorización",audit)

    def test_aviso_legal_usa_responsable_persona_fisica(self):
        page=build.legal_pages()["aviso-legal"][1]
        self.assertIn("Persona física responsable, en nombre propio",page)
        self.assertIn("Información legal en revisión",page)


if __name__=="__main__":
    unittest.main()
