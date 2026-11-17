"""Pruebas del bloqueo de lectores sin derechos de reutilización acreditados."""
import json
import os
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from captacion import SOURCES, collect, fuentes_habilitadas
from control_calidad import inspect_calendar


class DerechosDeFuentesTests(unittest.TestCase):
    def test_registro_completo_con_estados_reconocidos(self):
        doc = json.loads((ROOT / "config" / "derechos_fuentes.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["version"], 1)
        self.assertEqual(set(doc["fuentes"]), set(SOURCES))
        self.assertTrue(all(record["estado"] in {"pendiente", "consulta_minima", "autorizado"}
                            for record in doc["fuentes"].values()))
        for record in doc["fuentes"].values():
            if record["estado"] == "autorizado":
                self.assertTrue(record["referencia_evidencia"])
                self.assertTrue(record["fecha_revision"])

    def test_consulta_minima_de_las_diez_fuentes_y_reservas_explicitas(self):
        enabled = fuentes_habilitadas()
        self.assertEqual(len(enabled), 10)
        self.assertEqual(enabled, set(SOURCES))
        doc = json.loads((ROOT / "config" / "derechos_fuentes.json").read_text(encoding="utf-8"))
        for source in ("fadmes", "dipgra"):
            self.assertEqual(doc["fuentes"][source]["estado"], "consulta_minima")
            self.assertEqual(doc["fuentes"][source]["riesgo_aviso_legal"], "reserva_expresa")
            self.assertEqual(doc["fuentes"][source]["referencia_evidencia"], "")

    def test_fadmes_y_dipgra_se_consultan_solo_con_robots_permitido(self):
        # Sin descargar la red: simular la lectura de calendarios primarios.
        pages = {
            SOURCES["fadmes"]: ('<table><tr><td>22/11/2026</td><td>22/11/2026</td>'
                                '<td>CxM</td><td>Trail Costa 12 km</td><td>Otros</td>'
                                '<td>Almería</td><td>Almería</td></tr></table>'),
            SOURCES["dipgra"]: ('<table><tr><td>FECHA</td><td>MUNICIPIO</td></tr>'
                               '<tr><td>13/12/2026</td><td>Lecrín</td></tr></table>'),
        }
        def fetch(url):
            self.assertIn(url, pages)
            return pages[url]
        with patch("captacion.fuentes_habilitadas", return_value={"fadmes", "dipgra"}), \
             patch("captacion.fetch_if_permitted", side_effect=fetch) as call, \\
             patch.dict(os.environ, {"CORRERADAR_FETCH": "1", "GLOBALTEMPO_AUTHORIZED": ""}):
            races, report = collect(date(2026, 11, 17))
        self.assertEqual(call.call_count, 2)
        self.assertEqual(report["fuentes"]["fadmes"]["estado"], "leida")
        self.assertEqual(report["fuentes"]["dipgra"]["estado"], "leida")
        self.assertEqual(report["fuentes_con_reservas_documentadas"], ["dipgra", "fadmes"])
        self.assertTrue(any(r["origen"] == "fadmes" for r in races))
        self.assertTrue(any(r["origen"] == "dipgra" for r in races))

    def test_fichas_sin_permisos_no_se_descargan(self):
        with patch("captacion.fuentes_habilitadas", return_value=set()), \
             patch("captacion.fetch_if_permitted", side_effect=AssertionError("No debe solicitar red")), \
             patch.dict(os.environ, {"CORRERADAR_FETCH": "1", "GLOBALTEMPO_AUTHORIZED": ""}):
            races, report = collect(date(2026, 11, 17))
        self.assertEqual(races, [])
        self.assertEqual(report["fuentes_con_consulta_habilitada"], 0)
        self.assertEqual(report["nombres_fuentes_habilitadas"], [])
        self.assertEqual(set(SOURCES).issubset(set(report["fuentes"])), True)
        for source in SOURCES:
            self.assertEqual(report["fuentes"][source]["estado"], "sin consulta automática")
        self.assertEqual(report["fuentes"]["globaltempo"]["estado"], "sin consulta automática")

    def test_no_permitir_activar_sin_evidencia(self):
        records = {key: {"estado": "pendiente"} for key in SOURCES}
        records["fadmes"] = {"estado": "autorizado", "fecha_revision": "2026-11-17",
                             "referencia_evidencia": ""}
        with patch("captacion.json.loads", return_value={"version": 1, "fuentes": records}):
            with self.assertRaisesRegex(ValueError, "evidencia"):
                fuentes_habilitadas()

    def test_rechazar_registro_incompleto(self):
        with patch("captacion.json.loads", return_value={"version": 1, "fuentes": {}}):
            with self.assertRaisesRegex(ValueError, "incompleto"):
                fuentes_habilitadas()

    def test_feed_ajeno_no_reemplaza_una_fuente_autorizada_caida(self):
        race = {
            "fecha": "2026-12-20", "nombre": "Prueba de muestra",
            "localidad": "Sevilla", "provincia": "Sevilla",
            "modalidad": "RUNNING", "fecha_origen": "catalogo",
            "consultado": "2026-11-16",
            "enlace": "https://example.org/carrera",
            "fuente": "https://example.org/carrera", "slug": "prueba-de-muestra"
        }
        capture = {
            "fuentes_con_consulta_habilitada": 1,
            "nombres_fuentes_habilitadas": ["fadmes"],
            "fuentes": {"fadmes": {"estado": "no disponible"},
                         "globaltempo": {"estado": "leida"}}
        }
        quality = inspect_calendar([race], capture, date(2026, 11, 17))
        self.assertFalse(quality["apto_para_desplegar"])
        self.assertTrue(any("habilitadas insuficientes" in reason
                            for reason in quality["bloqueos"]))
        capture["fuentes"]["fadmes"]["estado"] = "leida"
        quality = inspect_calendar([race], capture, date(2026, 11, 17))
        self.assertTrue(quality["apto_para_desplegar"], quality["bloqueos"])

    def test_calidad_permite_pausa_real_y_la_comunica(self):
        race = {
            "fecha": "2026-12-20", "nombre": "Prueba de muestra",
            "localidad": "Sevilla", "provincia": "Sevilla",
            "modalidad": "RUNNING", "fecha_origen": "catalogo",
            "consultado": "2026-11-16", "enlace": "https://example.org/inscripcion",
            "fuente": "https://example.org/ficha", "slug": "prueba-de-muestra"
        }
        report = inspect_calendar([race], {
            "fuentes_con_consulta_habilitada": 0,
            "nombres_fuentes_habilitadas": [],
            "fuentes": {key: {"estado": "sin consulta automática"} for key in SOURCES}
        }, date(2026, 11, 17))
        self.assertTrue(report["apto_para_desplegar"], report["bloqueos"])
        self.assertTrue(report["fuentes_pausadas_por_derechos"])
        self.assertTrue(any("pausada" in note for note in report["avisos"]))


if __name__ == "__main__":
    unittest.main()
