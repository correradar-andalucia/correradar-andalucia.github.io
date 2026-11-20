"""Regresión: una decisión editorial no puede reaparecer por fuentes o respaldos."""
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build
from vetos_editoriales import extract_vetoes, exclude_vetoed, is_vetoed
from persistencia import restore_missing
from test_persistencia import TODAY, item, report

SOURCE = "https://example.org/evento/monte-azul"


def editorial(**changes):
    row = {field: "" for field in build.HEADERS}
    row.update({
        "Fecha": "10/01/2027", "Nombre": "XI Carrera Monte Azul",
        "Localidad": "Moguer", "Provincia": "Huelva",
        "Modalidad": "RUNNING", "Distancia": "", "Estado": "Cancelada",
        "Fuente": SOURCE, "Verificado": "20/11/2026", "Publicar": "no",
    })
    row.update(changes)
    return row


def candidate(**changes):
    row = {
        "fecha": "2027-01-10", "nombre": "XI Carrera Monte Azul",
        "localidad": "Moguer", "provincia": "Huelva",
        "modalidad": "RUNNING", "distancia": "5 km",
        "origen": "faa", "fuente": "https://atletismofaa.es/carreras/otra-ficha",
        "enlace": "https://atletismofaa.es/carreras/otra-ficha",
        "estado": "Leída", "fuente_directa": True,
    }
    row.update(changes)
    return row


def vetoes(*rows):
    return extract_vetoes(rows, build.date_parse, build.MODES, build.norm)


class VetoEditorialTests(unittest.TestCase):
    def test_cancelada_no_publicar_tambien_es_veto_explicitamente_verificado(self):
        v = vetoes(editorial())
        self.assertEqual(len(v), 1)
        self.assertEqual(build.transform([editorial(Publicar="si")]), [])
        self.assertTrue(is_vetoed(candidate(), v))
        self.assertTrue(is_vetoed(candidate(nombre="XI Carrera Monte Ázul"), v))
        self.assertTrue(is_vetoed(candidate(distancia="21 km", fuente=SOURCE), v))

    def test_retirada_y_anulada_tambien_son_decisiones_explicitadas(self):
        for state in ("Anulada", "RETIRADA", "cancelado"):
            with self.subTest(state=state):
                self.assertTrue(is_vetoed(candidate(), vetoes(editorial(Estado=state))))

    def test_no_vetar_eventos_diferentes_ni_ediciones_posteriores(self):
        v = vetoes(editorial())
        for altered in (
            {"fecha": "2027-01-17"}, {"fecha": "2028-01-10"},
            {"localidad": "Almonte"}, {"provincia": "Sevilla"},
            {"modalidad": "TRAIL"}, {"nombre": "II Trail Parque del Río"},
        ):
            with self.subTest(change=altered):
                self.assertFalse(is_vetoed(candidate(**altered), v))

    def test_distancia_especifica_no_suprime_otra_modalidad_de_distancia(self):
        v = vetoes(editorial(Distancia="5 km"))
        self.assertTrue(is_vetoed(candidate(distancia="5 km"), v))
        self.assertFalse(is_vetoed(candidate(distancia="21 km"), v))
        # Si el lector omite la distancia, no hay prueba para descartar el veto.
        self.assertTrue(is_vetoed(candidate(distancia=""), v))

    def test_no_censurar_por_similitud_solo_de_url_o_nombre(self):
        v = vetoes(editorial())
        self.assertFalse(is_vetoed(candidate(localidad="Ayamonte", fuente=SOURCE), v))
        self.assertFalse(is_vetoed(candidate(fecha="2027-01-11", fuente=SOURCE), v))
        self.assertFalse(is_vetoed(candidate(nombre="Trail de la Sierra de Cazorla", fuente=SOURCE), v))

    def test_registro_incompleto_bloquea_en_lugar_de_ignorarse(self):
        for changed in (
            {"Fuente": ""}, {"Fuente": "http://example.org/"},
            {"Verificado": ""}, {"Verificado": "ayer"},
            {"Fecha": ""}, {"Provincia": ""}, {"Localidad": ""},
            {"Modalidad": "BICICLETA"}, {"Nombre": ""},
        ):
            with self.subTest(changed=changed):
                with self.assertRaisesRegex(ValueError, "veto editorial inválido"):
                    vetoes(editorial(**changed))
        self.assertEqual(vetoes(editorial(Estado="Confirmada")), [])

    def test_filtra_vivo_catalogo_y_publicacion_anterior_antes_de_restaurar(self):
        v = vetoes(editorial())
        sources, rejected = exclude_vetoed([candidate(), candidate(nombre="Trail Río Verde")], v)
        self.assertEqual(rejected, 1)
        self.assertEqual(len(sources), 1)
        previous = [item(nombre="Carrera Pueblo"), item(
            nombre="XI Carrera Monte Azul", fecha="2027-01-10",
            localidad="Moguer", provincia="Huelva", modalidad="RUNNING",
        )]
        retained, excluded = exclude_vetoed(previous, v)
        self.assertEqual(excluded, 1)
        restored = []
        restore_missing(restored, retained, report(), build.slugify, build.km_parse, TODAY)
        self.assertFalse(any(r["nombre"] == "XI Carrera Monte Azul" for r in restored))

    def test_contradiccion_con_aprobacion_bloquea_build(self):
        approved = editorial(Estado="Confirmada", Publicar="si")
        with patch.dict(os.environ, {"CORRERADAR_FETCH": "0", "SHEET_CSV_URL": ""}), \
             patch("build.load_csv", return_value=[approved, editorial()]), \
             patch("captacion.collect") as collect:
            with self.assertRaisesRegex(ValueError, "contradice un veto editorial"):
                build.main()
            collect.assert_not_called()

    def test_build_offline_no_reintroduce_una_carrera_vetada_por_fuente(self):
        synthetic = candidate()
        report_offline = {"modo": "Prueba local sin conexión", "fuentes": {}}
        with TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {"CORRERADAR_FETCH": "0", "SHEET_CSV_URL": ""}), \
             patch("build.OUT", Path(tmp) / "_site"), \
             patch("build.load_csv", return_value=[editorial()]), \
             patch("captacion.collect", return_value=([synthetic], report_offline)):
            build.main()
            doc = json.loads((Path(tmp) / "_site/data/carreras.json").read_text())
            audit = json.loads((Path(tmp) / "_site/data/auditoria_duplicados.json").read_text())
        self.assertFalse(any(r.get("nombre") == synthetic["nombre"]
                             and r.get("fecha") == synthetic["fecha"]
                             and r.get("localidad") == synthetic["localidad"]
                             for r in doc["carreras"]))
        self.assertEqual(audit["vetos_editoriales"]["decisiones_verificadas"], 1)
        self.assertEqual(audit["vetos_editoriales"]["vivas_descartadas"], 1)


if __name__ == "__main__":
    unittest.main()
