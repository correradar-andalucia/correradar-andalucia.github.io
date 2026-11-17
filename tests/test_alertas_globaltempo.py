"""Pruebas de seguridad y aprobación del buzón editorial de Global Tempo."""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import alertas_globaltempo as gt

TODAY=date(2026,11,17)
URL="https://www.global-tempo.com/carreras.php?id=3375"
OTHER="https://www.global-tempo.com/carreras.php?id=3376"


def atom(title="XV Carrera Navideña de Prueba - Global Tempo",url=URL,
         updated="2026-11-17T12:00:00Z"):
    return (f'<feed xmlns="http://www.w3.org/2005/Atom">'
            f'<entry><title>{title}</title>'
            f'<link href="{url.replace("&","&amp;")}"/>'
            f'<updated>{updated}</updated></entry></feed>').encode("utf-8")


def issue(body=None,labels=None):
    record={"id":"3375","nombre":"XV Carrera Navideña de Prueba",
            "url":URL,"fecha_aviso":"2026-11-17"}
    if body is None:
        body=gt.issue_body(record).replace("- [ ]","- [x]")
    return {"state":"open","user":{"login":"github-actions[bot]"},
            "number":123,"body":body,"labels":[{"name":x} for x in (
                [gt.PENDING,gt.APPROVE] if labels is None else labels)]}


class AlertasGT(unittest.TestCase):
    def test_acepta_solo_link_profundo(self):
        self.assertEqual(gt.event_id(URL),"3375")
        for link in ("https://global-tempo.com/",
                     "https://global-tempo.com/carreras.php",
                     "http://www.global-tempo.com/carreras.php?id=3375",
                     "https://evil.example/carreras.php?id=3375",
                     "https://www.global-tempo.com/carreras.php?id=3375&dni=4",
                     "https://user:pwd@www.global-tempo.com/carreras.php?id=3375",
                     "https://www.global-tempo.com/carreras.php?id=00001",
                     "javascript:alert(1)"):
            with self.subTest(link=link):
                self.assertFalse(gt.event_id(link))

    def test_google_alerts_rss_y_enlaces_indexados(self):
        rows=gt.parse_feed(atom(),TODAY)
        self.assertEqual(rows,[{"id":"3375","nombre":"XV Carrera Navideña de Prueba",
                                "url":URL,"fecha_aviso":"2026-11-17"}])
        from urllib.parse import quote
        link="https://www.google.com/url?url="+quote(URL,safe="")
        self.assertEqual(gt.source_link(link),URL)
        self.assertEqual(gt.parse_feed(atom(url=link),TODAY)[0]["url"],URL)

    def test_rechaza_google_ajeno_y_redirect_a_otro_dominio(self):
        for link in ("https://www.google.com/search?q=globaltempo",
                     "https://google.example/url?url="+URL,
                     "https://www.google.com/url?url=https://evil.test/carreras.php?id=3375"):
            self.assertEqual(gt.source_link(link),"")

    def test_rechaza_entradas_antiguas_y_malformadas(self):
        self.assertEqual(gt.parse_feed(atom(updated="2026-07-01T12:00:00Z"),TODAY),[])
        self.assertEqual(gt.parse_feed(atom(updated="2026-11-19T12:00:00Z"),TODAY),[])
        self.assertEqual(gt.parse_feed(atom(title="Global Tempo",url=OTHER),TODAY),[])
        self.assertEqual(gt.parse_feed(atom(url="https://otro.test/carreras/123"),TODAY),[])
        with self.assertRaises(ValueError):
            gt.parse_feed(b"<!DOCTYPE feed><rss/>",TODAY)
        with self.assertRaises(ValueError):
            gt.parse_feed(b"<html></html>",TODAY)

    def test_rss_tradicional_y_duplicados(self):
        xml=(f'<rss version="2.0"><channel>'
             f'<item><title>III Carrera Nueva</title><link>{URL}</link>'
             '<pubDate>Tue, 17 Nov 2026 11:00:00 GMT</pubDate></item>'
             f'<item><title>Repetida</title><link>{URL}</link>'
             '<pubDate>Tue, 17 Nov 2026 12:00:00 GMT</pubDate></item>'
             '</channel></rss>').encode("utf-8")
        rows=gt.parse_feed(xml,TODAY)
        self.assertEqual(len(rows),1)

    def test_url_de_alerta_configurable_no_es_un_scraper(self):
        gt.alert_feed_url("https://www.google.com/alerts/feeds/123456")
        for link in ("https://www.global-tempo.com/carreras.php",
                     "https://www.google.com/search?q=x",
                     "http://www.google.com/alerts/feeds/123456",
                     "https://google.example/alerts/feeds/1234"):
            with self.subTest(link=link),self.assertRaises(ValueError):
                gt.alert_feed_url(link)

    def test_sin_alerta_no_hace_peticiones_ni_publica(self):
        with patch.dict("os.environ",{"GT_ALERT_RSS_URL":""}):
            with patch.object(gt,"read_feed",side_effect=AssertionError("no red")):
                gt.detect()

    def test_issue_pide_tres_comprobaciones(self):
        body=gt.issue_body({"id":"3375","nombre":"XV Carrera Navideña de Prueba",
                            "url":URL,"fecha_aviso":"2026-11-17"})
        self.assertEqual(body.count("- [ ]"),3)
        self.assertIn("NO es la fecha de la carrera",body)
        with self.assertRaisesRegex(ValueError,"tres comprobaciones"):
            gt.extract_issue(issue(body=body.replace("- [ ]","- [x]",2)))

    def test_aprobar_solo_issue_del_bot_y_con_etiqueta(self):
        record=gt.extract_issue(issue())
        self.assertEqual(record["url"],URL)
        self.assertEqual(record["nombre"],"XV Carrera Navideña de Prueba")
        self.assertEqual(record["issue"],123)
        false_issue=issue()
        false_issue["user"]["login"]="desconocido"
        with self.assertRaises(ValueError):
            gt.extract_issue(false_issue)
        with self.assertRaises(ValueError):
            gt.extract_issue(issue(labels=[gt.PENDING]))

    def test_no_permitir_cambiar_id_para_publicar_otro_enlace(self):
        original=gt.issue_body({"id":"3375","nombre":"XV Carrera Navideña de Prueba",
                                "url":URL,"fecha_aviso":"2026-11-17"})
        fake=original.replace(URL,OTHER)
        with self.assertRaisesRegex(ValueError,"ya no coincide"):
            gt.extract_issue(issue(body=fake))

    def test_catalogo_aprobado_solo_nombre_y_url(self):
        rows=gt.publication_candidates([{"nombre":"Carrera de prueba",
                                          "url":URL,"issue":123,
                                          "revision":"2026-11-17"}])
        self.assertEqual(rows,[{"nombre":"Carrera de prueba","url":URL}])
        with self.assertRaises(ValueError):
            gt.publication_candidates([{"nombre":"Carrera","url":URL},
                                       {"nombre":"Otra","url":URL}])
        with self.assertRaises(ValueError):
            gt.publication_candidates([{"nombre":"Carrera","url":"https://evil.test/"}])

    def test_aprobar_solo_guarda_tras_etiqueta_y_revisiones(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"aprobados.json"
            path.write_text('{"enlaces":[]}',encoding="utf-8")
            event=Path(folder)/"event.json"
            event.write_text(json.dumps({"action":"labeled",
                                         "label":{"name":gt.APPROVE},
                                         "issue":issue()}),encoding="utf-8")
            with patch.object(gt,"FILE",path),patch.dict("os.environ",
                                       {"GITHUB_EVENT_PATH":str(event)}):
                gt.approve()
                rows=gt.approved_items(path)
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]["url"],URL)
                gt.approve()
                self.assertEqual(len(gt.approved_items(path)),1)

    def test_aprobar_rechaza_otras_etiquetas(self):
        with tempfile.TemporaryDirectory() as folder:
            event=Path(folder)/"event.json"
            event.write_text(json.dumps({"action":"labeled",
                                         "label":{"name":"gt-pendiente"},
                                         "issue":issue()}))
            with patch.dict("os.environ",{"GITHUB_EVENT_PATH":str(event)}):
                with self.assertRaisesRegex(ValueError,"no es una aprobación"):
                    gt.approve()


if __name__=="__main__":
    unittest.main()
