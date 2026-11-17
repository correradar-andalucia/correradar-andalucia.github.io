"""Seguridad editorial de prelanzamiento y protección del despliegue automático."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from control_calidad import (check_launch_ready, inspect_calendar, valid_source)


def carrera(**extra):
    record={
        "fecha":"2026-12-20","nombre":"Carrera Popular de prueba",
        "localidad":"Sevilla","provincia":"Sevilla","modalidad":"RUNNING",
        "distancia":"10 km","distancia_origen":"fuente",
        "hora":"","enlace":"https://organizador.example/carrera/2026",
        "fuente":"https://organizador.example/calendario",
        "fecha_origen":"fuente","consultado":"2026-11-17",
        "slug":"carrera-popular-de-prueba"
    }
    record.update(extra)
    return record


def fuentes():
    return {"fuentes":{
        "faa":{"estado":"leida","candidatas":2},
        "dorsalchip":{"estado":"leida","candidatas":3},
        "otra":{"estado":"error","motivo":"fuera de servicio"}
    }}


class ControlCalidad(unittest.TestCase):
    def test_calendario_valido_y_metricas(self):
        report=inspect_calendar([carrera()],fuentes(),date(2026,11,17))
        self.assertTrue(report["apto_para_desplegar"],report["bloqueos"])
        self.assertEqual(report["con_distancia"],1)
        self.assertEqual(report["fuentes_automaticas_leidas_total"],2)
        self.assertEqual(report["origen_fecha"]["fuente"],1)
        self.assertEqual(report["provincias"]["Sevilla"],1)

    def test_no_sobrescribir_si_caen_las_fuentes(self):
        report=inspect_calendar([carrera()],{"fuentes":{"faa":{"estado":"error"}}},
                                date(2026,11,17))
        self.assertFalse(report["apto_para_desplegar"])
        self.assertTrue(any("dos fuentes" in s for s in report["bloqueos"]))

    def test_permitir_pruebas_locales_sin_red(self):
        report=inspect_calendar([carrera()],{"modo":"Prueba local sin conexión","fuentes":{}},
                                date(2026,11,17))
        self.assertTrue(report["apto_para_desplegar"])

    def test_evitar_pagina_vacia(self):
        report=inspect_calendar([],fuentes(),date(2026,11,17))
        self.assertFalse(report["apto_para_desplegar"])

    def test_fecha_pasada_o_invalida_bloquea(self):
        for fecha in ("2026-11-15","2026-02-30","2032-01-01"):
            with self.subTest(fecha=fecha):
                report=inspect_calendar([carrera(fecha=fecha)],fuentes(),date(2026,11,17))
                self.assertFalse(report["apto_para_desplegar"])

    def test_consulta_antigua_no_se_muestra_como_reciente(self):
        record=carrera(consultado="2026-09-01",fecha_origen="fuente")
        report=inspect_calendar([record],fuentes(),date(2026,11,17))
        self.assertFalse(report["apto_para_desplegar"])
        record["fecha_origen"]="catalogo"
        report=inspect_calendar([record],fuentes(),date(2026,11,17))
        self.assertTrue(report["apto_para_desplegar"])

    def test_fecha_consulta_futura_bloquea(self):
        report=inspect_calendar([carrera(consultado="2026-11-30")],fuentes(),date(2026,11,17))
        self.assertFalse(report["apto_para_desplegar"])

    def test_proteccion_enlaces_entre_datos(self):
        self.assertTrue(valid_source("https://organizador.example/carrera/2026"))
        for uri in ("http://organizador.example/carrera", "javascript:alert(1)",
                    "https://u:clave@organizador.example/", "https://bad host.test/"):
            with self.subTest(uri=uri):
                self.assertFalse(valid_source(uri))
                report=inspect_calendar([carrera(enlace=uri)],fuentes(),date(2026,11,17))
                self.assertFalse(report["apto_para_desplegar"])

    def test_provincia_y_modalidad_requeridas(self):
        for record in (carrera(provincia="Madrid"),
                       carrera(modalidad="DESCONOCIDA"),
                       carrera(localidad="")):
            report=inspect_calendar([record],fuentes(),date(2026,11,17))
            self.assertFalse(report["apto_para_desplegar"])

    def test_lanzamiento_legal_requiere_aprobacion_expresa(self):
        check_launch_ready({"public_launch":False})
        with self.assertRaisesRegex(ValueError,"LANZAMIENTO BLOQUEADO"):
            check_launch_ready({"public_launch":True})
        with self.assertRaisesRegex(ValueError,"legal_review_complete"):
            check_launch_ready({"public_launch":True,
                                "contact_email":"ejemplo@correo.test",
                                "legal_name":"Persona responsable"})
        with self.assertRaisesRegex(ValueError,"source_rights_review_complete"):
            check_launch_ready({"public_launch":True,
                                "contact_email":"ejemplo@correo.test",
                                "legal_name":"Persona responsable",
                                "legal_review_complete":True})
        complete={"public_launch":True,
                  "contact_email":"ejemplo@correo.test",
                  "legal_name":"Persona responsable",
                  "legal_review_complete":True,
                  "source_rights_review_complete":True,
                  "hosting_privacy_review_complete":True,
                  "cookie_behavior_review_complete":True}
        for field in ("source_rights_review_complete",
                      "hosting_privacy_review_complete",
                      "cookie_behavior_review_complete"):
            broken=dict(complete,**{field:False})
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,field):
                check_launch_ready(broken)
        check_launch_ready(complete)


if __name__=="__main__":
    unittest.main()
