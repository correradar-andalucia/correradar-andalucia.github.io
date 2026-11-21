"""Pruebas de seguridad y aprobación del buzón editorial de Global Tempo."""
import json
import io
from contextlib import redirect_stdout
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

    def test_sin_alerta_crea_etiquetas_pero_no_lee_fuentes(self):
        created=[]
        with patch.dict("os.environ",{"GT_ALERT_RSS_URL":""}):
            with patch.object(gt,"read_feed",side_effect=AssertionError("no leer RSS")):
                with patch.object(gt,"gh_request",side_effect=AssertionError("no crear incidencias")):
                    with patch.object(gt,"ensure_label",side_effect=lambda name,*args:created.append(name)):
                        gt.detect()
        self.assertEqual(created,[gt.PENDING,gt.APPROVE,gt.PUBLISHED])

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

    def test_siguientes_lotes_tambien_generan_incidencias(self):
        candidates=[{"id":str(4000+i),
                     "nombre":f"Carrera de prueba {i}",
                     "url":f"https://www.global-tempo.com/carreras.php?id={4000+i}",
                     "fecha_aviso":"2026-11-17"} for i in range(35)]
        posted=[]
        with patch.dict("os.environ",{"GT_ALERT_RSS_URL":"rss-configurado"}):
            with patch.object(gt,"read_feed",return_value=b"feed"):
                with patch.object(gt,"parse_feed",return_value=candidates):
                    with patch.object(gt,"existing_candidates",
                                      return_value={c["id"] for c in candidates[:20]}):
                        with patch.object(gt,"ensure_label"):
                            with patch.object(gt,"gh_request",
                                              side_effect=lambda method,path,data:
                                              posted.append((method,path,data))):
                                gt.detect()
        self.assertEqual(len(posted),15)
        self.assertTrue(all(item[0]=="POST" for item in posted))
        self.assertIn("Carrera de prueba 34",posted[-1][2]["title"])

    def test_diagnostico_atom_clasifica_todos_los_descartes(self):
        def entry(title, link, updated):
            return (f'<entry><title>{title}</title><link href="{link}"/>'
                    f'<updated>{updated}</updated></entry>')
        xml=('<feed xmlns="http://www.w3.org/2005/Atom">'
             +entry('I Carrera válida',URL,'2026-11-17T12:00:00Z')
             +entry('I Carrera repetida',URL,'2026-11-17T12:00:00Z')
             +entry('Global Tempo',OTHER,'2026-11-17T12:00:00Z')
             +entry('I Carrera con enlace extraño','https://evil.test/','2026-11-17T12:00:00Z')
             +entry('I Carrera sin fecha',OTHER,'fecha-desconocida')
             +entry('I Carrera futura',OTHER,'2026-11-19T12:00:00Z')
             +entry('I Carrera antigua',OTHER,'2026-09-01T12:00:00Z')
             +entry('I Carrera adicional',OTHER,'2026-11-17T12:00:00Z')
             +'</feed>').encode('utf-8')
        metrics={}
        rows=gt.parse_feed(xml,TODAY,metrics=metrics)
        self.assertEqual([r['id'] for r in rows],['3375','3376'])
        self.assertEqual(metrics,{
            'entradas_rss':8,'titulo_invalido':1,'enlace_no_admitido':1,
            'fecha_no_valida':1,'fecha_futura':1,'fecha_antigua':1,
            'duplicado_en_rss':1,'candidatos_validos':2,
        })
        self.assertEqual(metrics['entradas_rss'],
                         sum(v for k,v in metrics.items() if k!='entradas_rss'))

    def test_diagnostico_rss_tradicional_sin_datos_de_carrera(self):
        xml=(f'<rss><channel><item><title>Una carrera nueva</title>'
             f'<link>{URL}</link><pubDate>Tue, 17 Nov 2026 11:00:00 GMT</pubDate>'
             f'</item><item><title>Duplicada</title><link>{URL}</link>'
             f'<pubDate>Tue, 17 Nov 2026 12:00:00 GMT</pubDate>'
             f'</item></channel></rss>').encode('utf-8')
        metrics={}
        self.assertEqual(len(gt.parse_feed(xml,TODAY,metrics=metrics)),1)
        self.assertEqual(metrics['entradas_rss'],2)
        self.assertEqual(metrics['duplicado_en_rss'],1)
        self.assertEqual(metrics['candidatos_validos'],1)

    def test_diagnostico_logs_sin_rss_privado_titulos_ni_urls(self):
        private_url="https://www.google.com/alerts/feeds/TOKEN_ULTRASECRETO"
        title="I Carrera DATOS_PRIVADOS_EN_TITULO"
        xml=atom(title=title)
        output=io.StringIO()
        with patch.dict("os.environ",{"GT_ALERT_RSS_URL":private_url}):
            with patch.object(gt,"ensure_label"):
                with patch.object(gt,"read_feed",return_value=xml) as reader:
                    with patch.object(gt,"existing_candidates",return_value={"3375"}):
                        with patch.object(gt,"approved_items",return_value=[]):
                            with patch.object(gt,"gh_request",side_effect=AssertionError("no crear nuevas incidencias")):
                                with redirect_stdout(output):
                                    gt.detect()
        self.assertEqual(reader.call_count,1)
        logged=output.getvalue()
        self.assertIn('Global Tempo: diagnóstico RSS ',logged)
        self.assertIn('"entradas_rss": 1',logged)
        self.assertIn('"candidatos_validos": 1',logged)
        self.assertIn('"ya_conocidos": 1',logged)
        self.assertIn('"incidencias_nuevas": 0',logged)
        for secret in (private_url,'TOKEN_ULTRASECRETO',title,URL,'3375'):
            self.assertNotIn(secret,logged)

    def test_diagnostico_distingue_limitados_de_duplicados_historicos(self):
        candidates=[{"id":str(8000+i),
                     "nombre":f"Carrera de prueba {i}",
                     "url":f"https://www.global-tempo.com/carreras.php?id={8000+i}",
                     "fecha_aviso":"2026-11-17"} for i in range(23)]
        posted=[]
        output=io.StringIO()
        with patch.dict("os.environ",{"GT_ALERT_RSS_URL":"rss-de-prueba"}):
            with patch.object(gt,"read_feed",return_value=b"xml-de-prueba"):
                with patch.object(gt,"parse_feed",return_value=candidates):
                    with patch.object(gt,"existing_candidates",return_value={"8000"}):
                        with patch.object(gt,"approved_items",return_value=[]):
                            with patch.object(gt,"ensure_label"):
                                with patch.object(gt,"gh_request",side_effect=lambda method,path,data:
                                                  posted.append((method,path,data))):
                                    with redirect_stdout(output):
                                        gt.detect()
        self.assertEqual(len(posted),20)
        logged=output.getvalue()
        self.assertIn('"ya_conocidos": 1',logged)
        self.assertIn('"aplazados_por_limite": 2',logged)
        self.assertIn('"incidencias_nuevas": 20',logged)
        self.assertNotIn(candidates[0]['url'],logged)

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
