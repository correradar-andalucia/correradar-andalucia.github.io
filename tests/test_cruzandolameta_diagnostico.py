"""Regresiones del lector de Cruzando la Meta con HTML mínimo y sin red.

Los fragmentos son esquemáticos; no copian la descripción ni la web completa.
"""
from datetime import date
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from captacion import collect, cruzando_links, parse_cruzando_detail, SOURCES

TODAY = date(2026, 11, 20)
BASE = "https://www.cruzandolameta.es"
URL = BASE + "/pruebas/san-silvestre-vegas-del-genil-2026/"


def ficha(nombre="SAN SILVESTRE VEGAS DEL GENIL 2026",
          encabezado="Miércoles, 30 de diciembre de 2026 Salida a las 17:30 Vegas del Genil (Granada)",
          donde="Vegas del Genil (Granada)", extra=""):
    return (f'<main><h1>{nombre}</h1><p>{encabezado}</p>'
            f'<h2>Distancias</h2><p>Marcha senderista 7 km</p>'
            f'<h2>Dónde</h2><p>{donde}</p>'
            f'{extra}</main>')


class DiagnosticoCruzandoTests(unittest.TestCase):
    def test_ficha_con_hora_y_donde_separado_recupera_municipio(self):
        result = {}
        row = parse_cruzando_detail(ficha(), URL, TODAY, result)
        self.assertEqual(row["fecha"], "2026-12-30")
        self.assertEqual(row["localidad"], "Vegas del Genil")
        self.assertEqual(row["provincia"], "Granada")
        self.assertEqual(row["modalidad"], "RUNNING")
        self.assertEqual(row["distancia"], "")  # No apropiarse del senderismo.
        self.assertEqual(result, {})

    def test_municipio_explicitado_entre_parentesis(self):
        url = BASE + "/pruebas/relevos-por-equipos-la-alqueria-2027/"
        html = ficha(
            nombre="RELEVOS POR EQUIPOS LA ALQUERÍA 2027",
            encabezado="Domingo, 10 de enero de 2027 Salida a las 08:30 La Alquería (Adra) (Almería)",
            donde="La Alquería (Adra) (Almería)")
        row = parse_cruzando_detail(html, url, TODAY)
        self.assertEqual((row["localidad"], row["provincia"], row["fecha"]),
                         ("Adra", "Almería", "2027-01-10"))

    def test_recinto_no_se_inventa_como_localidad(self):
        html = ficha(
            nombre="IV CxM EL VERGEL BÉRCHULES-ALCÚTAR 2026",
            encabezado="Sábado, 12 de diciembre de 2026 Salida a las 09:00 Plaza de la Iglesia de Alcútar (Granada)",
            donde="Plaza de la Iglesia de Alcútar (Granada)")
        diagnostic = {}
        self.assertIsNone(parse_cruzando_detail(html,URL,TODAY,diagnostic))
        self.assertEqual(diagnostic["motivo"],"recinto_sin_municipio_verificable")

    def test_palacio_de_deportes_de_vicar_no_es_localidad(self):
        # Regresión del caso publicado en la incidencia #68.
        html = ficha(
            nombre="II CXM LA CALZADA 2027",
            encabezado=("Domingo, 7 de febrero de 2027 "
                        "Salida a las 09:00 Palacio de Deportes de Vícar (Almería)"),
            donde="Palacio de Deportes de Vícar (Almería)")
        diagnostic = {}
        self.assertIsNone(parse_cruzando_detail(html, URL, TODAY, diagnostic))
        self.assertEqual(diagnostic["motivo"], "recinto_sin_municipio_verificable")

    def test_palacio_con_municipio_explicito_y_provincia_se_acepta(self):
        html = ficha(
            nombre="II CXM LA CALZADA 2027",
            encabezado="Domingo, 7 de febrero de 2027",
            donde="Palacio de Deportes de Vícar (Vícar) (Almería)")
        race = parse_cruzando_detail(html, URL, TODAY)
        self.assertEqual(race["localidad"], "Vícar")
        self.assertEqual(race["provincia"], "Almería")
        self.assertEqual(race["fecha"], "2027-02-07")

    def test_solo_plaza_sin_provincia_se_descarta(self):
        diagnostic={}
        html=ficha(nombre="VIII SAN SILVESTRE TORRENUEVA COSTA",
                   donde="Plaza de la Iglesia")
        self.assertIsNone(parse_cruzando_detail(html,URL,TODAY,diagnostic))
        self.assertEqual(diagnostic["motivo"],"ubicacion_sin_provincia_verificable")

    def test_no_reutiliza_localidad_de_carrera_recomendada(self):
        html=('<h1>SAN SILVESTRE VEGAS DEL GENIL 2026</h1>'
              '<p>30 de diciembre de 2026</p>'
              '<h2>También te puede interesar</h2>'
              '<p>Motril (Granada)</p>')
        diagnostic={}
        self.assertIsNone(parse_cruzando_detail(html,URL,TODAY,diagnostic))
        self.assertEqual(diagnostic["motivo"],"ubicacion_sin_provincia_verificable")

    def test_antigua_ficha_con_localidad_aislada_sigue_aceptada(self):
        html=('<h1>IV CARRERA SAN SILVESTRE ATARFE 2026</h1>'
              '<p>Domingo, 20 de diciembre de 2026</p>'
              '<p>Pabellón de Atarfe (Granada)</p><p>Running</p>')
        row=parse_cruzando_detail(html,URL,TODAY)
        self.assertEqual(row["localidad"],"Atarfe")
        self.assertEqual(row["fecha"],"2026-12-20")

    def test_cancelada_descartada_no_se_reinterpreta(self):
        html=ficha(extra='<p>Prueba cancelada</p>')
        diagnostic={}
        self.assertIsNone(parse_cruzando_detail(html,URL,TODAY,diagnostic))
        self.assertEqual(diagnostic["motivo"],"cancelada")

    def test_no_ciclismo_ni_fecha_pasada(self):
        diagnostic={}
        html=ficha(nombre="III RUTA BTT 2026")
        self.assertIsNone(parse_cruzando_detail(html,URL,TODAY,diagnostic))
        self.assertEqual(diagnostic["motivo"],"deporte_excluido")
        diagnostic={}
        html=ficha(encabezado="Domingo, 1 de noviembre de 2026",donde="Motril (Granada)")
        self.assertIsNone(parse_cruzando_detail(html,URL,TODAY,diagnostic))
        self.assertEqual(diagnostic["motivo"],"fecha_no_verificable")

    def test_diagnostico_agregado_sin_peticiones_extra(self):
        listing=('<a href="/pruebas/san-silvestre-vegas-del-genil-2026/">A</a>'
                 '<a href="/pruebas/san-silvestre-torrenueva-costa-2026/">B</a>')
        other=BASE+"/pruebas/san-silvestre-torrenueva-costa-2026/"
        resources={SOURCES["cruzandolameta"]:listing, URL:ficha(),
                   other:ficha(nombre="VIII SAN SILVESTRE TORRENUEVA COSTA",
                               donde="Plaza de la Iglesia")}
        def fake_fetch(uri):
            self.assertIn(uri,resources)
            return resources[uri]
        with patch("captacion.fuentes_habilitadas",return_value={"cruzandolameta"}), \
             patch("captacion.fetch_if_permitted",side_effect=fake_fetch) as fetch, \
             patch("captacion.time.sleep"), \
             patch("globaltempo_feed.authorized",return_value=False), \
             patch("globaltempo_feed.fetch_authorized_feed",
                   return_value=([],{"estado":"sin consulta automática"})), \
             patch.dict(os.environ,{"CORRERADAR_FETCH":"1"}):
            events, report=collect(TODAY)
        self.assertEqual(fetch.call_count,3)
        self.assertEqual(len(events),1)
        self.assertEqual(report["fuentes"]["cruzandolameta"]["candidatas"],1)
        info=report["fuentes"]["cruzandolameta_detalle"]
        self.assertEqual(info["consultadas"],2)
        self.assertEqual(info["aceptadas"],1)
        self.assertEqual(info["descartadas"],1)
        self.assertEqual(info["errores"],0)
        self.assertEqual(info["motivos"],{"ubicacion_sin_provincia_verificable":1})
        self.assertNotIn("https:",str(info))
        self.assertNotIn("Vegas del Genil",str(info))

    def test_links_sin_cambios_de_limites(self):
        html="".join(f'<a href="/pruebas/carrera-{i}/">Evento</a>'
                     for i in range(30))
        self.assertEqual(len(cruzando_links(html)),18)
        self.assertEqual(len(cruzando_links(html+html)),18)


if __name__=="__main__":
    unittest.main()
