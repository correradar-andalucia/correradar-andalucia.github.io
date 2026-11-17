"""Regresiones de Global Tempo sin hacer solicitudes reales al proveedor."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from globaltempo_feed import (
    authorized, event_url, feed_host, fetch_authorized_feed, parse_authorized_feed
)
from deduplicacion import combine
from build import slugify, km_parse
from control_calidad import inspect_calendar

TODAY = date(2026,11,17)
URL = "https://www.global-tempo.com/carreras.php?id=3325"


def event(**extra):
    data={
        "edicion_confirmada":True,
        "nombre":"VII San Silvestre de Alhendín 2026",
        "fecha":"2026-12-19",
        "localidad":"Alhendín",
        "provincia":"Granada",
        "modalidad":"RUNNING",
        "distancia":"5 km",
        "hora":"18:00",
        "url":URL,
    }
    data.update(extra)
    return data


def feed(events=None,updated="2026-11-17"):
    return {"version":1,"actualizado":updated,
            "eventos":[event()] if events is None else events}


class FakeResponse:
    status=200
    def __init__(self,data):
        self.data=data
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n=-1):return self.data[:n]


class FakeOpener:
    def __init__(self,data):self.data=data
    def open(self,req,timeout=None):
        assert req.full_url == "https://feeds.global-tempo.com/public.json"
        return FakeResponse(self.data)


class GlobalTempoAutorizado(unittest.TestCase):
    def test_desactivado_no_solicita_ninguna_pagina(self):
        with patch("globaltempo_feed.build_opener",
                   side_effect=AssertionError("NO debe acceder a la red")):
            rows,status=fetch_authorized_feed(TODAY,env={})
        self.assertEqual(rows,[])
        self.assertEqual(status["estado"],"sin consulta automática")
        self.assertFalse(authorized({"GLOBALTEMPO_AUTHORIZED":"true"}))
        self.assertTrue(authorized({"GLOBALTEMPO_AUTHORIZED":"yes"}))

    def test_solo_endpoint_https_acordado(self):
        self.assertEqual(feed_host("https://feeds.global-tempo.com/feed",
                                   "feeds.global-tempo.com"),
                         "feeds.global-tempo.com")
        for uri,host in [
            ("http://feeds.global-tempo.com/feed","feeds.global-tempo.com"),
            ("https://evil.example/feed","feeds.global-tempo.com"),
            ("https://user:pass@feeds.global-tempo.com/","feeds.global-tempo.com"),
            ("https://feeds.global-tempo.com:8080/","feeds.global-tempo.com"),
        ]:
            with self.subTest(uri=uri),self.assertRaises(ValueError):
                feed_host(uri,host)

    def test_solo_ficha_de_carrera_individual(self):
        self.assertTrue(event_url(URL))
        for url in ("https://www.global-tempo.com/",
                    "https://www.global-tempo.com/carreras.php",
                    "http://www.global-tempo.com/carreras.php?id=3325",
                    "https://evil.example/carreras.php?id=3325",
                    "https://www.global-tempo.com/carreras.php?id=3325&dni=1",
                    "https://www.global-tempo.com/carreras.php?id=bad",
                    "https://www.global-tempo.com/carreras.php?id=3325#comentarios"):
            with self.subTest(url=url):
                self.assertFalse(event_url(url))

    def test_importar_fecha_municipio_distancia_hora_y_fuente(self):
        rows,skipped=parse_authorized_feed(feed(),TODAY)
        self.assertEqual(len(rows),1)
        self.assertEqual(skipped,0)
        race=rows[0]
        self.assertEqual(race["fecha"],"2026-12-19")
        self.assertEqual(race["hora"],"18:00")
        self.assertEqual(race["origen"],"globaltempo")
        self.assertTrue(race["fuente_directa"])
        self.assertTrue(race["feed_autorizado"])
        self.assertEqual(race["distancia_fuente"],URL)
        self.assertEqual(race["enlace"],URL)

    def test_excluir_actividades_no_pertinentes(self):
        bad=[
            event(nombre="Duatlón Cross de Granada"),
            event(nombre="Ruta Senderismo Alhendín"),
            event(nombre="Pasacalles Andarines Alhendín"),
            event(nombre="X Travesía a Nado de Granada"),
            event(nombre="Carrera Popular en bici BTT"),
            event(nombre="Carrera sin confirmar",edicion_confirmada=False),
            event(provincia="Madrid"),
            event(fecha="2026-11-10"),
            event(fecha="2026-12-19",fecha_reglamento="2026-08-02"),
            event(url="https://www.global-tempo.com/"),
            event(distancia="200m de desnivel, sin kilómetros",hora="25:70"),
        ]
        races,discarded=parse_authorized_feed(feed(bad),TODAY)
        self.assertEqual(races,[])
        self.assertEqual(discarded,len(bad))

    def test_no_publicar_fechas_ambiguas_o_fuente_obsoleta(self):
        for document in [feed(updated="2026-10-01"),
                         feed(updated="2026-12-01"),
                         dict(feed(),version=2),
                         dict(feed(),eventos="texto")]:
            with self.subTest(document=document),self.assertRaises(ValueError):
                parse_authorized_feed(document,TODAY)

    def test_enlaces_y_eventos_repetidos_no_se_duplican(self):
        items=[event(),event(),event(url="https://www.global-tempo.com/carreras.php?id=3326",
                                    nombre="Otra carrera confirmada")]
        rows,skipped=parse_authorized_feed(feed(items),TODAY)
        self.assertEqual(len(rows),2)
        self.assertEqual(skipped,1)

    def test_descarga_autorizada_separada_de_robots_no_web_scraping(self):
        raw=json.dumps(feed()).encode("utf-8")
        env={"GLOBALTEMPO_AUTHORIZED":"yes",
             "GLOBALTEMPO_FEED_URL":"https://feeds.global-tempo.com/public.json",
             "GLOBALTEMPO_FEED_HOST":"feeds.global-tempo.com"}
        with patch("globaltempo_feed.build_opener",return_value=FakeOpener(raw)):
            rows,status=fetch_authorized_feed(TODAY,env)
        self.assertEqual(status["estado"],"leida")
        self.assertEqual(status["candidatas"],1)
        self.assertNotIn("public.json",status["url"])
        self.assertEqual(len(rows),1)

    def test_si_se_activa_y_feed_falla_no_se_despliega(self):
        row,skipped=parse_authorized_feed(feed(),TODAY)
        from deduplicacion import combine
        valid=combine([],row,slugify,km_parse)
        report={"globaltempo_autorizado":True,"fuentes":{
            "faa":{"estado":"leida"},"dorsalchip":{"estado":"leida"},
            "globaltempo":{"estado":"no disponible"}}}
        status=inspect_calendar(valid,report,TODAY)
        self.assertFalse(status["apto_para_desplegar"])
        self.assertTrue(any("Global Tempo" in msg for msg in status["bloqueos"]))
        report["fuentes"]["globaltempo"]={"estado":"leida"}
        status=inspect_calendar(valid,report,TODAY)
        self.assertTrue(status["apto_para_desplegar"],status["bloqueos"])

    def test_feed_autorizado_prevalece_sobre_semilla(self):
        latest,_=parse_authorized_feed(feed(),TODAY)
        old=dict(latest[0],feed_autorizado=False,fuente_directa=False,
                 distancia="",hora="",estado="Cotejada · fuente previa",
                 verificado="2026-11-15",origen="globaltempo")
        combined=combine([], [old,*latest],slugify,km_parse)
        self.assertEqual(len(combined),1)
        self.assertEqual(combined[0]["distancia"],"5 km")
        self.assertEqual(combined[0]["hora"],"18:00")
        self.assertFalse(combined[0]["confirmada"])


if __name__=="__main__":
    unittest.main()
