"""Regresión de seguridad: la San Antón 2027 es un cotejo, no un alta."""
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from oficiales import FILES

CANDIDATO = ROOT / "docs" / "candidatos_editoriales" / "san-anton-jaen-2027.json"


class CandidatoSanAntonJaenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registro = json.loads(CANDIDATO.read_text(encoding="utf-8"))

    def test_ficha_aislada_sin_autorizacion_de_publicacion(self):
        r = self.registro
        self.assertEqual(r["esquema"], 1)
        self.assertEqual(r["clasificacion"], "candidato_editorial_no_publicable")
        self.assertIs(r["aprobado"], False)
        self.assertIs(r["incorporacion_automatica"], False)
        self.assertNotIn(CANDIDATO, FILES)
        self.assertNotIn("data", CANDIDATO.relative_to(ROOT).parts)

    def test_campos_no_inventados_y_edicion_distinta(self):
        r = self.registro
        c = r["carrera"]
        self.assertEqual(date.fromisoformat(c["fecha"]), date(2027, 1, 16))
        self.assertEqual((c["localidad"], c["provincia"]), ("Jaén", "Jaén"))
        self.assertEqual(c["modalidad"], "RUNNING")
        for campo in ("hora", "distancia", "verificado"):
            self.assertEqual(c[campo], "")
        self.assertEqual(c["inscripcion_estado"], "desconocida")
        self.assertIn("pendiente_de_reglamento", c["fecha_certidumbre"])
        self.assertEqual(len(r["no_confundir_con"]), 2)
        self.assertTrue(all(
            (x["municipio"], x["provincia"]) != ("Jaén", "Jaén")
            for x in r["no_confundir_con"]
        ))

    def test_evidencias_separan_anuncio_y_licitacion(self):
        fuentes = self.registro["evidencias"]
        self.assertEqual(len(fuentes), 2)
        self.assertTrue(fuentes[0]["url"].startswith("https://patronatodeportesjaen.es/"))
        self.assertIn("2027", fuentes[0]["acredita"])
        self.assertIn("No fija fecha", fuentes[0]["no_acredita"])
        self.assertTrue(fuentes[1]["url_oficial"].startswith("https://contrataciondelestado.es/"))
        self.assertTrue(fuentes[1]["url_reproduccion"].startswith("https://contratos.gobierto.es/"))
        self.assertIn("rechazó", fuentes[1]["advertencia"])
        self.assertTrue(self.registro["por_comprobar"])


if __name__ == "__main__":
    unittest.main()
