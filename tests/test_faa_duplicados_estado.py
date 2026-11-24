"""Regresiones: disponibilidad en FAA no convierte una carrera en dos."""
from datetime import date
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from captacion import parse_faa
from deduplicacion import same_event, combine, canonical_name
from build import slugify, km_parse

FAA = "https://atletismofaa.es/carreraspopulares/"


def carrera(nombre, distancia="", modalidad="TRAIL", localidad="Antequera"):
    return {
        "nombre": nombre, "fecha": "2026-11-28",
        "localidad": localidad, "provincia": "Málaga",
        "modalidad": modalidad, "distancia": distancia,
        "enlace": FAA, "fuente": FAA, "origen": "faa",
    }


class DuplicadosFAA(unittest.TestCase):
    def test_antequera_trail_etiqueta_de_inscripcion_no_es_nombre(self):
        html = ('<div>PRÓXIMAS CARRERAS:</div>'
                '<h2>28 NOVIEMBRE 2026</h2><h1>Antequera Trail</h1>'
                '<h2>28 NOVIEMBRE 2026</h2>'
                '<h1>Antequera Trail (inscripciones cerradas)</h1>')
        rows = parse_faa(html, date(2026, 11, 24))
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["nombre"] for r in rows],
                         ["Antequera Trail", "Antequera Trail"])
        self.assertEqual(rows[1]["inscripcion_estado"], "cerrada")
        self.assertEqual(rows[0]["localidad"], "Antequera")

        # Ejemplo sintético de distancia proveniente de otra ficha de la misma
        # carrera: al fusionar no se pierde la distancia conocida.
        rows[0]["distancia"] = "24 km · 14 km"
        rows[0]["fuente_directa"] = True
        rows[1]["fuente_directa"] = True
        result, audit = combine([], rows, slugify, km_parse, with_audit=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(audit["duplicados_fusionados"], 1)
        self.assertEqual(result[0]["nombre"], "Antequera Trail")
        self.assertEqual(result[0]["distancia"], "24 km · 14 km")
        self.assertFalse(result[0]["confirmada"])

    def test_prefijo_similar_no_confunde_otra_edicion_localidad_o_modalidad(self):
        base = carrera("Antequera Trail", "24 km")
        etiqueta = carrera("Antequera Trail (inscripciones cerradas)")
        self.assertTrue(same_event(base, etiqueta))
        self.assertFalse(same_event(base, carrera(
            "Antequera Trail (inscripciones cerradas)", localidad="Álora")))
        self.assertFalse(same_event(base, carrera(
            "Antequera Trail (inscripciones cerradas)", modalidad="RUNNING")))
        self.assertFalse(same_event(base, carrera(
            "Antequera Trail (inscripciones cerradas)", distancia="14 km")))
        self.assertFalse(same_event(base, {
            **etiqueta, "fecha": "2027-11-28",
        }))

    def test_otro_duplicado_faa_de_aviso_de_dorsales(self):
        a = {**carrera("San Silvestre Aguilarense", modalidad="RUNNING"),
             "fecha": "2026-12-31", "localidad": "Aguilar de la Frontera",
             "provincia": "Córdoba"}
        b = {**a, "nombre": "San Silvestre Aguilarense (dorsales agotados)"}
        self.assertEqual(canonical_name(a["nombre"]),
                         canonical_name(b["nombre"]))
        self.assertTrue(same_event(a, b))
        r, audit = combine([], [a, b], slugify, km_parse, with_audit=True)
        self.assertEqual(len(r), 1)
        self.assertEqual(audit["duplicados_fusionados"], 1)

    def test_solo_sufijos_parenteticos_explicitos(self):
        self.assertNotEqual(canonical_name("Carrera de Inscripciones Cerradas"),
                            canonical_name("Carrera"))
        self.assertNotEqual(canonical_name("Carrera 5K"),
                            canonical_name("Carrera 21K"))
        self.assertNotEqual(canonical_name("Carrera Infantil"),
                            canonical_name("Carrera"))
        self.assertEqual(canonical_name("Prueba (plazas agotadas)"),
                         canonical_name("Prueba"))
        self.assertEqual(canonical_name("Prueba (inscripciones agotadas)"),
                         canonical_name("Prueba"))


if __name__ == "__main__":
    unittest.main()
