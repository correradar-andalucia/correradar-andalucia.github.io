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
from captacion import SOURCES, collect, fuentes_con_derechos_acreditados
from control_calidad import inspect_calendar


class DerechosDeFuentesTests(unittest.TestCase):
    def test_registro_completo_con_estados_reconocidos(self):
        doc = json.loads((ROOT / "config" / "derechos_fuentes.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["version"], 1)
        self.assertEqual(set(doc["fuentes"]), set(SOURCES))
        self.assertTrue(all(record["estado"] in {"pendiente", "autorizado"}
                            for record in doc["fuentes"].values()))
        for record in doc["fuentes"].values():
            if record["estado"] == "autorizado":
                self.assertTrue(record["referencia_evidencia"])
                self.assertTrue(record["fecha_revision"])

    def test_fichas_sin_permisos_no_se_descargan(self):
        with patch("captacion.fuentes_con_derechos_acreditados", return_value=set()), \
             patch("captacion.fetch_if_permitted", side_effect=AssertionError("No debe solicitar red")), \
             patch.dict(os.environ, {"CORRERADAR_FETCH": "1", "GLOBALTEMPO_AUTHORIZED": ""}):
            races, report = collect(date(2026, 11, 17))
        self.assertEqual(races, [])
        self.assertEqual(report["fuentes_habilitadas_por_derechos"], 0)
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
                fuentes_con_derechos_acreditados()

    def test_rechazar_registro_incompleto(self):
        with patch("captacion.json.loads", return_value={"version": 1, "fuentes": {}}):
            with self.assertRaisesRegex(ValueError, "incompleto"):
                fuentes_con_derechos_acreditados()

    def test_calidad_permite_pausa_real_y_la_comunica(self):
        race = {
            "fecha": "2026-12-20", "nombre": "Prueba de muestra",
            "localidad": "Sevilla", "provincia": "Sevilla",
            "modalidad": "RUNNING", "fecha_origen": "catalogo",
            "consultado": "2026-11-16", "enlace": "https://example.org/inscripcion",
            "fuente": "https://example.org/ficha", "slug": "prueba-de-muestra"
        }
        report = inspect_calendar([race], {
            "fuentes_habilitadas_por_derechos": 0,
            "fuentes": {key: {"estado": "sin consulta automática"} for key in SOURCES}
        }, date(2026, 11, 17))
        self.assertTrue(report["apto_para_desplegar"], report["bloqueos"])
        self.assertTrue(report["fuentes_pausadas_por_derechos"])
        self.assertTrue(any("pausada" in note for note in report["avisos"]))


if __name__ == "__main__":
    unittest.main()
