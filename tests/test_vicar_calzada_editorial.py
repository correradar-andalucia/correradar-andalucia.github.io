"""La Calzada: distinguir evento 2027, municipio y cancelación de 2026.

Cotejo editorial fechado, sin red, sin estado de inscripción inferido.
"""
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from oficiales import official_races
from deduplicacion import combine, verify_unique
from build import slugify, km_parse


class LaCalzada2027Tests(unittest.TestCase):
    def test_2027_documentada_y_localidad_real(self):
        fichas = official_races(date(2026, 11, 20))
        matches = [x for x in fichas if x["nombre"] == "II CxM La Calzada 2027"]
        self.assertEqual(len(matches), 1)
        race = matches[0]
        self.assertEqual((race["fecha"], race["localidad"], race["provincia"]),
                         ("2027-02-07", "Vícar", "Almería"))
        self.assertEqual((race["modalidad"], race["hora"], race["distancia"]),
                         ("TRAIL", "09:30", "24,5 km · 15 km"))
        self.assertEqual(race["tipo_fuente"], "cronometraje")
        self.assertEqual(race["fuente"],
                         "https://inscrik.com/evento/ii-cxm-la-calzada-2027/")
        self.assertFalse(race.get("confirmada", False))

    def test_revision_fechada_no_afecta_revisiones_anteriores(self):
        previous = official_races(date(2026, 11, 19))
        self.assertFalse(any(x["nombre"] == "II CxM La Calzada 2027"
                             for x in previous))
        new = official_races(date(2026, 11, 20))
        self.assertEqual(sum(x["nombre"] == "II CxM La Calzada 2027"
                             for x in new), 1)

    def test_cancelacion_2026_no_se_transfiere_a_2027(self):
        fichas = official_races(date(2026, 11, 20))
        la_calzada = [x for x in fichas if "La Calzada" in x["nombre"]]
        self.assertEqual(len(la_calzada), 1)
        self.assertEqual(la_calzada[0]["fecha"], "2027-02-07")
        self.assertFalse(any(x["fecha"] == "2026-11-15"
                             for x in la_calzada))
        self.assertNotIn("cancelad", la_calzada[0]["estado"].lower())

    def test_no_copiar_senderismo_ni_inscripciones_caducables(self):
        race = next(x for x in official_races(date(2026, 11, 20))
                    if x["nombre"] == "II CxM La Calzada 2027")
        self.assertNotIn("18 km", race["distancia"])
        self.assertFalse(race.get("inscripcion_estado"))

    def test_ficha_publicable_con_fusion_y_procedencia(self):
        records = official_races(date(2026, 11, 20))
        merged = combine([], records, slugify, km_parse)
        self.assertTrue(verify_unique(merged))
        races = [x for x in merged if x["nombre"] == "II CxM La Calzada 2027"]
        self.assertEqual(len(races), 1)
        race = races[0]
        self.assertEqual(race["localidad"], "Vícar")
        self.assertEqual(race["fecha_origen"], "fuente")
        self.assertEqual(race["hora_origen"], "fuente")
        self.assertEqual(race["distancia_origen"], "fuente")
        self.assertFalse(race["confirmada"])


if __name__ == "__main__":
    unittest.main()
