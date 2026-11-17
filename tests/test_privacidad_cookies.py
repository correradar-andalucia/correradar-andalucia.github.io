"""Comprobar que privacidad y cookies describen lo que realmente hace el sitio."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build
from captacion import SOURCES
from control_calidad import check_launch_ready


class AuditoriaPrivacidad(unittest.TestCase):
    def setUp(self):
        self.pages = build.legal_pages()
        self.config=json.loads((ROOT/"config"/"site.json").read_text(encoding="utf-8"))

    def test_info_de_titular_no_inventada(self):
        legal=self.pages["aviso-legal"][1]
        self.assertIn("IDENTIDAD PENDIENTE DE COMPLETAR",legal)
        self.assertIn("NIF",legal)
        self.assertIn("revisión",legal)
        self.assertFalse(self.config["public_launch"])
        self.assertFalse(self.config["legal_review_complete"])

    def test_politica_privacidad_explicita_proveedor_e_ip(self):
        policy=self.pages["privacidad"][1]
        for term in ("GitHub Pages","direcciones IP","correo de contacto",
                     "AEPD","derecho","retirar","plazo"):
            with self.subTest(term=term):
                self.assertIn(term,policy)

    def test_cookie_policy_no_promete_lo_no_auditado(self):
        policy=self.pages["cookies"][1]
        self.assertIn("no crea cookies propias",policy)
        self.assertIn("GitHub Pages",policy)
        self.assertIn("No afirmamos",policy)
        self.assertIn("no mostramos un banner",policy)
        self.assertIn("aceptar y rechazar",policy)

    def test_codigo_no_incorpora_tracking_de_terceros(self):
        code=(ROOT/"assets"/"app.js").read_text(encoding="utf-8")
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        for forbidden in ("document.cookie","localStorage","sessionStorage",
                          "googletagmanager.com","google-analytics.com",
                          "connect.facebook.net","fbq("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden,code+html)
        self.assertIn('content="no-referrer"',html)
        self.assertNotIn("<iframe",html)
        self.assertNotIn('src="https://',html)

    def test_referrer_minimizado_en_todas_las_paginas_generadas(self):
        self.assertIn('name="referrer" content="no-referrer"',
                      build.legal_page("Privacidad","Prueba"))
        sample={
          "nombre":"Carrera de prueba",
          "fecha":"2026-12-20","localidad":"Sevilla",
          "provincia":"Sevilla","modalidad":"RUNNING",
          "distancia":"","hora":"","desnivel":"","precio":"",
          "bolsa":"","track":"","enlace":"https://organizador.example/carrera",
          "fuente":"https://organizador.example/carrera",
          "slug":"carrera-prueba"}
        self.assertIn('name="referrer" content="no-referrer"',
                      build.detail_page(sample))

    def test_diez_fuentes_y_registro_de_riesgos(self):
        audit=(ROOT/"docs"/"auditoria_fuentes_privacidad_2026-11-17.md").read_text(encoding="utf-8")
        self.assertEqual(len(SOURCES),10)
        for name in ("FADME/FADMES","Dorsalchip","Cruzando la Meta","FAA",
                     "GCC Sport Events","Runnink","Gesconchip",
                     "Diputación de Granada","Diputación de Huelva",
                     "Circuito Cordobés"):
            with self.subTest(name=name):
                self.assertIn(name,audit)
        self.assertIn("NO acreditada",audit)
        self.assertIn("reserva",audit.lower())

    def test_lanzamiento_bloqueado_sin_revisiones_independientes(self):
        config=dict(self.config,public_launch=True,legal_name="Titular",
                    legal_review_complete=True)
        with self.assertRaisesRegex(ValueError,"source_rights_review_complete"):
            check_launch_ready(config)
        complete=dict(config,source_rights_review_complete=True,
                      hosting_privacy_review_complete=True,
                      cookie_behavior_review_complete=True)
        check_launch_ready(complete)


if __name__=="__main__":
    unittest.main()
