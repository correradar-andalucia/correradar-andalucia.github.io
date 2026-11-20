"""Regresión de fuentes que devuelven HTTP 200 pero dejan de extraer carreras."""
from datetime import date, timedelta
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from salud_captacion import verificar_lecturas, DIAS_REFERENCIA, MIN_HISTORICO
from control_calidad import inspect_calendar

TODAY = date(2026, 11, 20)


def past_source(source="faa", count=5, **kwargs):
    result = []
    for n in range(count):
        row = dict(
            nombre=f"Carrera prueba {n}", fecha=f"2026-12-{n + 10:02d}",
            origen=source, localidad="Sevilla", provincia="Sevilla",
            modalidad="RUNNING", confirmada=False,
            fecha_origen="fuente", consultado="2026-11-19",
            fuentes_origen=[source],
        )
        row.update(kwargs)
        result.append(row)
    return result


def capture(faa=0, dorsalchip=1, faa_status="leida", **extra):
    sources = {
        "faa": {"estado": faa_status, "candidatas": faa},
        "dorsalchip": {"estado": "leida", "candidatas": dorsalchip},
    }
    sources["faa"].update(extra)
    return {
        "fuentes_con_consulta_habilitada": 2,
        "nombres_fuentes_habilitadas": ["faa", "dorsalchip"],
        "fuentes": sources,
    }


def live(source="dorsalchip", n=1):
    return [dict(origen=source, nombre=f"Actual {i}") for i in range(n)]


def race():
    return {
        "fecha": "2026-12-15", "nombre": "Carrera de prueba",
        "localidad": "Sevilla", "provincia": "Sevilla", "modalidad": "RUNNING",
        "fecha_origen": "fuente", "consultado": "2026-11-20",
        "fuente": "https://example.org/prueba", "enlace": "https://example.org/prueba",
        "slug": "carrera-de-prueba",
    }


class LecturasSilenciosasTests(unittest.TestCase):
    def test_faa_cero_con_historico_reciente_es_bloqueo_aunque_otra_fuente_este_bien(self):
        report = capture()
        audit = verificar_lecturas(live(), past_source(count=5), report, TODAY)
        self.assertEqual(audit["sospechosas"]["faa"]["futuras_previas"], 5)
        self.assertEqual(report["fuentes"]["faa"]["estado"], "lectura_sospechosa")
        quality = inspect_calendar([race()], report, TODAY)
        self.assertFalse(quality["apto_para_desplegar"])
        self.assertTrue(any("faa: lectura sospechosa" in x for x in quality["bloqueos"]))
        self.assertEqual(quality["fuentes_con_lectura_sospechosa"], ["faa"])

    def test_puede_detectarlo_aunque_las_fichas_figuren_por_otro_origen(self):
        before = past_source(source="dorsalchip", count=4, fuentes_origen=["dorsalchip", "faa"])
        report = capture()
        audit = verificar_lecturas(live(), before, report, TODAY)
        self.assertEqual(audit["sospechosas"]["faa"]["futuras_previas"], 4)

    def test_recuento_declarado_inconsistente_es_sospechoso(self):
        report = capture(faa=2)
        audit = verificar_lecturas(live(), [], report, TODAY)
        self.assertEqual(audit["sospechosas"]["faa"]["motivo"], "recuento_inconsistente")
        self.assertFalse(inspect_calendar([race()], report, TODAY)["apto_para_desplegar"])

    def test_lectura_parcial_da_aviso_y_no_bloquea_sin_perdida_residual(self):
        report = capture(faa=2)
        events = live() + live("faa", 2)
        audit = verificar_lecturas(events, past_source(count=5), report, TODAY)
        self.assertFalse(audit["sospechosas"])
        self.assertEqual(audit["avisos"]["faa"]["motivo"], "descenso_parcial")
        quality = inspect_calendar([race()], report, TODAY)
        self.assertTrue(quality["apto_para_desplegar"], quality["bloqueos"])
        self.assertTrue(any("descenso_parcial" in x for x in quality["avisos"]))

    def test_fuente_legitimamente_vacia_sin_referencia_no_bloquea(self):
        report = capture()
        audit = verificar_lecturas(live(), [], report, TODAY)
        self.assertEqual(audit["sospechosas"], {})
        self.assertEqual(audit["avisos"], {})
        self.assertTrue(inspect_calendar([race()], report, TODAY)["apto_para_desplegar"])

    def test_historico_pequeno_no_bloquea(self):
        report = capture()
        audit = verificar_lecturas(live(), past_source(count=MIN_HISTORICO - 1), report, TODAY)
        self.assertFalse(audit["sospechosas"])

    def test_no_basarse_en_carreras_pasadas_o_consultas_caducadas(self):
        for old in (
            {"fecha": "2026-11-19"},
            {"consultado": "2026-11-01"},
            {"consultado": "2026-11-21"},
            {"fecha_origen": "catalogo"},
            {"confirmada": True},
            {"respaldo_temporal": True},
        ):
            with self.subTest(old=old):
                report = capture()
                audit = verificar_lecturas(live(), past_source(count=5, **old), report, TODAY)
                self.assertFalse(audit["sospechosas"])
        self.assertEqual(DIAS_REFERENCIA, 7)

    def test_no_bloquear_fuente_pausada_ni_restringida(self):
        for status, fields in (
            ("sin consulta automática", {}),
            ("no disponible", {}),
            ("leida", {"acceso_restringido": True}),
            ("leida", {"detalle_restringido": True}),
        ):
            with self.subTest(status=status, fields=fields):
                report = capture(faa_status=status, **fields)
                audit = verificar_lecturas(live(), past_source(count=5), report, TODAY)
                self.assertFalse(audit["sospechosas"])

    def test_modo_offline_ignora_comparaciones(self):
        report = capture()
        report["modo"] = "Prueba local sin conexión"
        audit = verificar_lecturas(live(), past_source(count=5), report, TODAY)
        self.assertFalse(audit["sospechosas"])
        quality = inspect_calendar([race()], report, TODAY)
        self.assertTrue(quality["apto_para_desplegar"])

    def test_enlaces_que_no_producen_fichas_generan_aviso_sin_historico(self):
        report = capture(enlaces_detectados=5, incidencias_detalle=3)
        audit = verificar_lecturas(live(), [], report, TODAY)
        self.assertFalse(audit["sospechosas"])
        self.assertEqual(audit["avisos"]["faa"]["motivo"], "enlaces_sin_carreras")
        self.assertTrue(inspect_calendar([race()], report, TODAY)["apto_para_desplegar"])

    def test_fuente_saludable_no_provoca_sospecha(self):
        report = capture(faa=5)
        events = live() + live("faa", 5)
        audit = verificar_lecturas(events, past_source(count=5), report, TODAY)
        self.assertFalse(audit["sospechosas"])
        self.assertFalse(audit["avisos"])
        self.assertEqual(report["fuentes"]["faa"]["estado"], "leida")


if __name__ == "__main__":
    unittest.main()
