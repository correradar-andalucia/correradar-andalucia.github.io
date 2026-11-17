"""Regresiones de cobertura: fichas documentadas, caducidad y seguridad editorial."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from oficiales import official_races
from deduplicacion import combine, verify_unique
from build import detail_page, slugify, km_parse


class FichasOficiales(unittest.TestCase):
    def test_sevilla_jaen_huelva(self):
        rows = official_races(date(2026, 11, 16))
        self.assertEqual(len(rows), 12)
        self.assertEqual(sum(r["provincia"] == "Sevilla" for r in rows), 7)
        self.assertEqual(sum(r["provincia"] == "Jaén" for r in rows), 3)
        self.assertEqual(sum(r["provincia"] == "Huelva" for r in rows), 2)
        self.assertTrue(all(r["fuente"].startswith("https://") for r in rows))
        self.assertTrue(all(r["fuente_directa"] for r in rows))

    def test_distancia_y_hora_cuando_documentadas(self):
        rows = official_races(date(2026, 11, 16))
        by_name = {r["nombre"]: r for r in rows}
        self.assertEqual(by_name["XXXI San Silvestre Sevillana"]["distancia"],
                         "5 km · 1 km · 250 m")
        self.assertEqual(by_name["XXXI San Silvestre Sevillana"]["hora"], "10:00")
        self.assertEqual(by_name["XXVII Carrera a los Puentes"]["distancia"],
                         "18 km aprox.")
        self.assertEqual(by_name["IX Carrera Nocturna Ciudad de Camas"]["distancia"],
                         "")  # Referencias externas contradictorias; no adivinar

    def test_caducidad_marca_fuente_anterior(self):
        rows = official_races(date(2026, 12, 20))
        self.assertTrue(rows)
        self.assertTrue(all(not r["fuente_directa"] for r in rows))
        self.assertTrue(all("reconfirmar" in r["estado"].lower() for r in rows))
        self.assertTrue(all(r["fecha"] >= "2026-12-20" for r in rows))

    def test_no_reetiquetar_revisiones_antiguas_como_lectura_hoy(self):
        rows = official_races(date(2026, 11, 16))
        result = combine([], rows, slugify, km_parse)
        carrera = next(r for r in result if r["nombre"] == "XXXI San Silvestre Sevillana")
        self.assertFalse(carrera["confirmada"])  # No confundir con la hoja editorial.
        self.assertEqual(carrera["fecha_origen"], "fuente")
        self.assertEqual(carrera["consultado"], "2026-11-16")
        self.assertEqual(carrera["distancia_origen"], "fuente")
        self.assertEqual(carrera["hora_origen"], "fuente")
        self.assertIn("Hora de salida", detail_page(carrera))
        self.assertTrue(verify_unique(result))

    def test_fichas_caducadas_no_simulan_actualidad(self):
        rows = official_races(date(2026, 12, 20))
        result = combine([], rows, slugify, km_parse)
        self.assertTrue(all(r["fecha_origen"] == "catalogo" for r in result))
        self.assertEqual({r["consultado"] for r in result}, {"2026-11-16", "2026-11-17"})

    def test_carreras_nuevas_solo_con_fuentes_primarias(self):
        rows = official_races(date(2026, 11, 17))
        self.assertEqual(len(rows), 23)
        self.assertEqual(len({(r["fecha"], r["nombre"], r["localidad"]) for r in rows}), 23)
        by_name = {r["nombre"]: r for r in rows}
        self.assertEqual(by_name["XXXII Medio Maratón de Sevilla"]["fecha"], "2026-12-13")
        self.assertEqual(by_name["XXXII Medio Maratón de Sevilla"]["hora"], "09:00")
        self.assertEqual(by_name["XLII Zurich Maratón de Sevilla"]["distancia"], "42,195 km")
        self.assertEqual(by_name["Unicaja Ultra Sierra Nevada 2027 — Maratón"]["localidad"], "Quéntar")
        self.assertEqual(by_name["101 km en 24 h de La Legión 2027 — marcha"]["fecha"],
                         "2027-05-08")
        self.assertEqual(by_name["XVI Cross El Hecho de Guadalcázar"]["distancia"], "6 km")
        self.assertTrue(all(r["cotejada"] in ("2026-11-16","2026-11-17") for r in rows))

    def test_agregador_no_puede_hacerse_pasar_por_organizador(self):
        bad = {"revision":"2026-11-17", "carreras":[{
            "fecha":"2026-12-27", "nombre":"Carrera de prueba", "localidad":"Sevilla",
            "provincia":"Sevilla", "modalidad":"RUNNING", "distancia":"10 km",
            "hora":"", "fuente":"https://www.runnea.com/carreras-populares/calendario/andalucia/",
            "fuente_nombre":"Un agregador", "tipo_fuente":"organizador"}]}
        with self.assertRaisesRegex(ValueError, "agregadora"):
            official_races(date(2026, 11, 17), bad)

    def test_inscripcion_real_no_es_importacion_de_agregador(self):
        rows=official_races(date(2026,11,17))
        original=next(r for r in rows if r["nombre"]=="III Carrera Popular de Navidad El Rubio")
        self.assertEqual(original["fecha"],"2026-12-20")
        self.assertEqual(original["tipo_fuente"],"cronometraje")
        # Un evento hipotético en ese mismo listado NO pasa como confirmado.
        wrong=dict(original)
        wrong["nombre"]="Carrera no corroborada"
        entry={k:wrong[k] for k in (
            "fecha","nombre","localidad","provincia","modalidad","distancia",
            "hora","fuente","fuente_nombre","tipo_fuente")}
        with self.assertRaisesRegex(ValueError,"agregadora"):
            official_races(date(2026,11,17),{"revision":"2026-11-17",
                                              "carreras":[entry]})

    def test_fuente_no_https_rechazada(self):
        bad = {
            "revision": "2026-11-16",
            "carreras": [{
                "fecha":"2026-12-27","nombre":"Carrera ejemplo",
                "localidad":"Sevilla","provincia":"Sevilla","modalidad":"RUNNING",
                "distancia":"5 km","hora":"10:00",
                "fuente":"javascript:alert(1)","fuente_nombre":"Evento",
                "tipo_fuente":"organizador"
            }]
        }
        with self.assertRaisesRegex(ValueError, "fuente inválido"):
            official_races(date(2026, 11, 16), bad)


if __name__ == "__main__":
    unittest.main()
