"""La auditoría de grandes carreras no debe publicar ni descargar fuentes."""
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import auditar_prioritarios as auditor

ROOT = Path(__file__).resolve().parents[1]


class PrioritariosTest(unittest.TestCase):
    def test_inventario_ocho_provincias_y_fuentes_federativas(self):
        inventario = auditor.leer_inventario()
        self.assertEqual(
            {x["provincia"] for x in inventario["carreras"]},
            auditor.PROVINCIAS
        )
        self.assertGreaterEqual(len(inventario["carreras"]), 16)
        self.assertEqual(
            {x["sigla"] for x in inventario["fuentes_federativas"]},
            {"FAA", "FADMES"}
        )
        self.assertTrue(all(
            r["participacion_historica"]["cifra_referencia"] > 500
            for r in inventario["carreras"]
        ))

    def test_jaen_san_anton_no_confundir_otros_municipios(self):
        inv = auditor.leer_inventario()
        p = next(r for r in inv["carreras"] if r["id"] == "jaen-san-anton")
        base = {"fecha": "2027-01-16", "nombre": "XLIV Noche de San Antón",
                "localidad": "Jaén", "provincia": "Jaén"}
        self.assertTrue(auditor.coincide(base, p))
        self.assertFalse(auditor.coincide({
            **base, "nombre": "III San Antón Escañuela",
            "localidad": "Escañuela",
        }, p))
        self.assertFalse(auditor.coincide({
            **base, "nombre": "Canicross Pinar de San Antón",
            "provincia": "Cádiz", "localidad": "El Puerto de Santa María",
        }, p))
        self.assertFalse(auditor.coincide({
            **base, "nombre": "Resultados de San Antón",
        }, p))

    def test_sin_edicion_no_equivale_a_carrera_cancelada(self):
        p = {
            "id": "g", "nombre": "Carrera General", "provincia": "Granada",
            "municipio": "Granada", "alias": ["carrera general"], "excluir": [],
            "participacion_historica": {
                "anio": 2026, "cifra_referencia": 700, "tipo_cifra": "inscritos",
                "fuente": "https://ejemplo.org/edicion2026"
            },
        }
        ref = {"publicacion": {"fecha": "2026-11-22T01:00:00Z"},
               "sha256": "a" * 64, "pendiente": False}
        sin = auditor.auditar(
            {"revision": "2026-11-22", "carreras": [p],
             "fuentes_federativas": []},
            {"carreras": [{"nombre": "Otra carrera", "localidad": "Granada",
                          "provincia": "Granada", "fecha": "2027-01-11"}]}, ref
        )
        self.assertEqual(sin["resultados"][0]["estado"], "sin_ficha_actual")
        self.assertIn("NO prueba cancelación", sin["advertencia"])

    def test_comparar_edicion_de_2027_con_ficha_de_2026(self):
        p = {
            "id": "j", "nombre": "Noche de San Antón de Jaén", "provincia": "Jaén",
            "municipio": "Jaén", "alias": ["noche de san anton"], "excluir": [],
            "participacion_historica": {
                "anio": 2026, "cifra_referencia": 1000, "tipo_cifra": "inscritos",
                "fuente": "https://ejemplo.org/anuncio"
            },
            "edicion_anunciada": {"anio": 2027,
                                 "fuente": "https://ejemplo.org/edicion"},
        }
        ref = {"publicacion": {"fecha": "2026-11-22T01:00:00Z"},
               "sha256": "a" * 64, "pendiente": False}
        base = {"fecha": "2026-01-17", "nombre": "Noche de San Antón",
                "localidad": "Jaén", "provincia": "Jaén"}
        data = {"revision": "2026-11-22", "carreras": [p],
                "fuentes_federativas": []}
        viejo = auditor.auditar(data, {"carreras": [base]}, ref)
        self.assertEqual(viejo["resultados"][0]["estado"], "otra_edicion_localizada")
        nuevo = auditor.auditar(data, {"carreras": [
            {**base, "fecha": "2027-01-16"}]}, ref)
        self.assertEqual(nuevo["resultados"][0]["estado"], "edicion_cubierta")

    def test_integridad_sha_y_calendario_embebido(self):
        publicado = {"actualizado": "2026-11-22", "carreras": [
            {"nombre": "Noche de San Antón", "fecha": "2027-01-16",
             "localidad": "Jaén", "provincia": "Jaén"}]}
        bruto = json.dumps(publicado, ensure_ascii=False)
        estado = {
            "confirmado": {
                "calendario": bruto, "sha256": sha256(bruto.encode()).hexdigest(),
                "publicacion": {"fecha": "2026-11-22T01:00:00Z",
                                "commit": "abc", "ejecucion": "1",
                                "intento": "1"}},
            "pendiente": None
        }
        with tempfile.TemporaryDirectory() as temp:
            archivo = Path(temp) / "estado.json"
            archivo.write_text(json.dumps(estado), encoding="utf-8")
            calendario, ref = auditor.leer_calendario_confirmado(archivo)
            self.assertEqual(len(calendario["carreras"]), 1)
            self.assertFalse(ref["pendiente"])
            estado["confirmado"]["calendario"] = bruto.replace("Jaén", "Cádiz")
            archivo.write_text(json.dumps(estado), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Huella"):
                auditor.leer_calendario_confirmado(archivo)
            archivo.write_text('{"actualizado":"","carreras":[]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "No existe"):
                auditor.leer_calendario_confirmado(archivo)

    def test_diferenciar_maraton_de_sevilla_y_media(self):
        inventario = auditor.leer_inventario()
        maraton = next(x for x in inventario["carreras"]
                       if x["id"] == "sevilla-maraton")
        media = next(x for x in inventario["carreras"]
                     if x["id"] == "sevilla-media")
        r = {"nombre": "XXXII Medio Maratón de Sevilla", "localidad": "Sevilla",
             "provincia": "Sevilla", "fecha": "2026-12-13"}
        self.assertFalse(auditor.coincide(r, maraton))
        self.assertTrue(auditor.coincide(r, media))
        r["nombre"] = "XLII Zurich Maratón de Sevilla"
        self.assertTrue(auditor.coincide(r, maraton))
        self.assertFalse(auditor.coincide(r, media))


if __name__ == "__main__":
    unittest.main()
