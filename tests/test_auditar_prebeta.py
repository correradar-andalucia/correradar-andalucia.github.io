"""Pruebas puramente locales de la auditoría de procedencia para el sprint beta."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from auditar_prebeta import auditar


def carrera(numero, fuentes, **extra):
    base = {
        "slug": f"slug-{numero}",
        "nombre": f"Carrera sintética {numero}",
        "fecha": "2027-01-10",
        "localidad": "Sevilla",
        "provincia": "Sevilla",
        "enlace": f"https://example.test/edicion/{numero}",
        "fecha_origen": "fuente",
        "fuentes_origen": list(fuentes),
    }
    base.update(extra)
    return base


DERECHOS = {
    "fuentes": {
        "fadmes": {"riesgo_aviso_legal": "reserva_expresa"},
        "gesconchip": {"riesgo_aviso_legal": "reserva_expresa"},
        "runnink": {"riesgo_aviso_legal": "reserva_expresa"},
        "dipgra": {"riesgo_aviso_legal": "reserva_expresa"},
        "faa": {"riesgo_aviso_legal": "reserva_general"},
        "dorsalchip": {"estado": "consulta_minima"},
        "gcc": {"estado": "consulta_minima"},
    }
}


class AuditoriaBeta(unittest.TestCase):
    def test_prioritarias_riesgos_y_solapamientos(self):
        rows = [
            carrera(1, ["fadmes"]),
            carrera(2, ["runnink", "oficial"]),
            carrera(3, ["gesconchip"]),
            carrera(4, ["faa"]),
            carrera(5, ["dipgra", "gcc"]),
            carrera(6, [], fecha_origen="editorial"),
            carrera(7, ["dorsalchip"]),
            carrera(8, ["FUENTE_PRIVADA_QUE_NO_DEBE_APARECER"]),
        ]
        resultado = auditar({"carreras": rows}, DERECHOS)
        s = resultado["resumen"]
        self.assertEqual(s["total"], 8)
        self.assertEqual(s["sin_fuentes_origen"], 1)
        self.assertEqual(s["fuente_unica"], 5)
        self.assertEqual(s["mas_de_una_fuente"], 2)
        self.assertEqual(s["con_prioritaria"], 3)
        self.assertEqual(s["solo_prioritarias"], 2)
        self.assertEqual(s["con_fuente_en_riesgo"], 5)
        self.assertEqual(s["solo_fuentes_en_riesgo"], 3)
        self.assertEqual(s["campos_esenciales_incompletos"], 0)
        self.assertEqual(resultado["fuentes_registradas"]["otra"], 1)
        self.assertEqual(resultado["origen_fecha"]["editorial"], 1)
        self.assertEqual(resultado["provincias"], {"Sevilla": 8})

    def test_ninguna_ficha_titulo_url_ni_identificador_en_resultados(self):
        marker = "DATO_PRIVADO_FICTICIO"
        r = carrera(1, ["fadmes"], nombre=marker,
                    enlace="https://example.test/" + marker,
                    slug=marker, localidad=marker)
        out = json.dumps(auditar({"carreras": [r]}, DERECHOS),
                         ensure_ascii=False)
        self.assertNotIn(marker, out)
        self.assertNotIn("example.test", out)
        self.assertIn("solo_prioritarias", out)

    def test_formato_duplicados_y_carreras_incompletas(self):
        a = carrera(1, ["dorsalchip"])
        b = carrera(2, [], slug=a["slug"], enlace="")
        c = carrera(3, [], slug="", provincia="ProvinciaDesconocida")
        s = auditar({"carreras": [a, b, c]}, DERECHOS)
        self.assertEqual(s["resumen"]["slugs_repetidos"], 2)
        self.assertEqual(s["resumen"]["campos_esenciales_incompletos"], 1)
        self.assertEqual(s["provincias"]["otra"], 1)

    def test_datos_invalidos_no_son_tratados_como_calendario(self):
        with self.assertRaises(ValueError):
            auditar({"carreras": "no-es-lista"}, DERECHOS)
        with self.assertRaises(ValueError):
            auditar({"carreras": [None]}, DERECHOS)
        with self.assertRaises(ValueError):
            auditar({"carreras": [carrera(1, "fadmes")]}, DERECHOS)
        with self.assertRaises(ValueError):
            auditar({"carreras": []}, {"no_firma": 3})


if __name__ == "__main__":
    unittest.main()
