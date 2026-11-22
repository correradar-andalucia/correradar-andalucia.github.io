"""Pruebas del detector RSS independiente; nunca toca internet ni secretos reales."""
import os
from datetime import date
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import quote
from xml.sax.saxutils import escape
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import alertas_nuevas_fuentes as rss
ROOT=Path(__file__).resolve().parents[1]
TODAY=date(2026,11,20)
URLS={
    "deportime":"https://deportime.es/events/carrera-ibero-navidena/",
    "croniussport":"https://inscripciones.croniussport.es/inscripcion/trail-sierra-de-aracena/",
    "cronofinisher":"https://www.cronofinisher.com/evento/carrera-torreperogil/",
    "patronato_jaen":"https://patronatodeportesjaen.es/presentacion-de-la-carrera-popular/",
}
def atom(url,title="Presentación de la carrera popular",stamp="2026-11-20T10:00:00Z"):
    return (f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>{escape(title)}</title>'
            f'<link href="{escape(url)}"/><updated>{stamp}</updated></entry></feed>').encode()

class AlertasNuevas(unittest.TestCase):
    def test_accept_each_domain_and_google_redirect(self):
        for source,url in URLS.items():
            with self.subTest(source=source):
                wrapped="https://www.google.com/url?url="+quote(url+"?utm_source=rss",safe="")
                self.assertEqual(rss.source_link(wrapped,source),url)
                rows=rss.parse_feed(atom(wrapped),source,TODAY)
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]["url"],url)
                self.assertEqual(rows[0]["fecha_aviso"],"2026-11-20")
    def test_patronato_events_can_generate_review_candidates(self):
        # El Patronato utiliza /events/<slug>/; no se abrían incidencias
        # con títulos del tipo «XLIII CARRERA...» sin verbo de noticia.
        url=("https://patronatodeportesjaen.es/events/"
             "xliii-carrera-urbana-internacional-noche-de-san-anton/")
        title="XLIII CARRERA URBANA INTERNACIONAL NOCHE DE SAN ANTÓN"
        self.assertEqual(rss.checked_url(url,"patronato_jaen"),url)
        rows=rss.parse_feed(atom(url,title),"patronato_jaen",TODAY)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["url"],url)
        # No reetiquetar un aviso antiguo como una edición nueva.
        self.assertEqual(rss.parse_feed(atom(url,title,"2026-09-01T10:00:00Z"),
                                        "patronato_jaen",TODAY),[])
        # Mantener dominios, rutas y parámetros restringidos.
        for forbidden in (
            "https://patronatodeportesjaen.es/events/",
            url+"inscritos/",
            "https://patronatodeportesjaen.es/events/resultados-carrera/",
            url+"?dni=123",
            url.replace("https://","http://"),
            url.replace(".es/",".es.evil.test/"),
        ):
            self.assertEqual(rss.checked_url(forbidden,"patronato_jaen"),"")
        # En páginas de noticias se conserva el filtro editorial anterior.
        news="https://patronatodeportesjaen.es/carrera-popular-sin-anuncio/"
        self.assertEqual(rss.parse_feed(atom(news,"Carrera popular habitual"),
                                        "patronato_jaen",TODAY),[])
        # Resultados no son convocatorias ni carreras nuevas.
        self.assertEqual(rss.parse_feed(atom(url,"Resultados Carrera San Antón"),
                                        "patronato_jaen",TODAY),[])

    def test_reject_private_subpages_and_parameters(self):
        base=URLS["cronofinisher"]
        for url in (base+"section%3Dinscritos/",base+"?dni=4",base+"?letter_range=A-F",
                    "http://www.cronofinisher.com/evento/carrera/",
                    "https://www.cronofinisher.com.evil.test/evento/carrera/",
                    "https://a:b@www.cronofinisher.com/evento/carrera/",
                    "https://www.cronofinisher.com/resultados/",URLS["deportime"]):
            self.assertEqual(rss.checked_url(url,"cronofinisher"),"")
    def test_no_results_or_old_alerts(self):
        url=URLS["deportime"]
        for title,stamp in [("Carrera MTB", "2026-11-20T00:00:00Z"),
              ("Resultados de la carrera popular","2026-11-20T00:00:00Z"),
              ("Carrera de prueba","2026-09-01T00:00:00Z"),
              ("Carrera de prueba","2026-11-21T00:00:00Z")]:
            self.assertEqual(rss.parse_feed(atom(url,title,stamp),"deportime",TODAY),[])
        self.assertEqual(rss.parse_feed(atom(URLS["patronato_jaen"],"Premios a la carrera popular"),"patronato_jaen",TODAY),[])
    def test_unsafe_xml_and_unknown_format(self):
        for xml in (b"<!DOCTYPE rss><rss/>",b"<html/>",b"<!ENTITY foo 'bar'><rss/>",
                    b"<!DOCTYPE rss><rss/>".decode().encode("utf-16")):
            with self.assertRaises((ValueError,UnicodeError)):
                rss.parse_feed(xml,"deportime",TODAY)
    def test_rss_alias_and_deduplication(self):
        a=URLS["cronofinisher"]
        b=a.replace("www.","").rstrip("/")+"?lang=es"
        xml=(f"<rss><channel><item><title>Carrera popular</title><link>{a}</link>"
             "<pubDate>Fri, 20 Nov 2026 09:00:00 GMT</pubDate></item>"
             f"<item><title>Carrera popular</title><link>{b}</link>"
             "<pubDate>Fri, 20 Nov 2026 09:00:00 GMT</pubDate></item></channel></rss>").encode()
        self.assertEqual(len(rss.parse_feed(xml,"cronofinisher",TODAY)),1)
    def test_history_includes_closed_issues_and_failure_stops(self):
        key="a"*24
        with patch.object(rss,"gh_request",return_value=[{"body":f"<!-- {rss.MARKER}:{key} -->","state":"closed"}]) as call:
            self.assertEqual(rss.existing_candidates(),{key})
            self.assertIn("state=all",call.call_args.args[1])
        with patch.object(rss,"gh_request",side_effect=ValueError("api")),patch.object(rss,"read_feed") as read:
            with self.assertRaises(ValueError):rss.detect()
            read.assert_not_called()
    def test_known_catalog_event_ignored(self):
        with patch.object(rss,"official_races",return_value=[{"fuente":URLS["deportime"]}]):
            self.assertIn(rss.candidate_id("deportime",URLS["deportime"]),rss.known_official("deportime"))
    def test_each_feed_independent_and_no_secrets_in_issue(self):
        env={v[1]:f"private-{key}" for key,v in rss.SOURCES.items()}
        candidates={key: rss.parse_feed(atom(url),key,TODAY) for key,url in URLS.items()}
        def read(value):
            if value=="private-deportime":raise ValueError("secret must not leak")
            return b"data"
        posted=[]
        with patch.dict(os.environ,env),patch.object(rss,"existing_candidates",return_value=set()), \
             patch.object(rss,"read_feed",side_effect=read),patch.object(rss,"known_official",return_value=set()), \
             patch.object(rss,"parse_feed",side_effect=lambda xml,key:candidates[key]), \
             patch.object(rss,"gh_request",side_effect=lambda m,p,d:posted.append(d)):
            self.assertEqual(rss.detect(),1)
        self.assertEqual(len(posted),3)
        for issue in posted:
            self.assertIn(rss.LABEL,issue["labels"])
            self.assertIn("NO es la fecha de la carrera",issue["body"])
            self.assertNotIn("private-",issue["body"])
            self.assertIn("no publica nada automáticamente",issue["body"])
    def test_limit_and_existing_candidate(self):
        env={v[1]:"rss" for v in rss.SOURCES.values()}
        posted=[]
        rows=[]
        for i in range(9):
            url=f"https://deportime.es/events/carrera-{i}/"
            rows.extend(rss.parse_feed(atom(url), "deportime", TODAY))
        with patch.dict(os.environ,env),patch.object(rss,"existing_candidates",return_value={rows[0]["id"]}), \
             patch.object(rss,"read_feed",return_value=b"data"),patch.object(rss,"known_official",return_value=set()), \
             patch.object(rss,"parse_feed",side_effect=lambda xml,key:rows if key=="deportime" else []), \
             patch.object(rss,"gh_request",side_effect=lambda m,p,d:posted.append(d)):
            self.assertEqual(rss.detect(),0)
        self.assertEqual(len(posted),rss.MAX_NEW)
        self.assertNotIn(rows[0]["id"],str(posted))
    def test_workflow_exact_secrets_no_access_to_writes(self):
        wf=(ROOT/".github/workflows/detectar-alertas-nuevas-fuentes.yml").read_text()
        for value in rss.SOURCES.values():
            self.assertIn("secrets."+value[1],wf)
        self.assertIn("contents: read",wf)
        self.assertIn("issues: write",wf)
        self.assertNotIn("contents: write",wf)
        self.assertIn("workflow_dispatch:",wf)

if __name__=="__main__":unittest.main()
