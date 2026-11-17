"""Fuentes independientes: fichas del Circuito Cordobés y enlaces GT corroborados."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from circuito_cordoba import circuito_links, circuito_detail, event_city
from enlaces_inscripcion import match_registrations
from deduplicacion import combine, same_event
from build import slugify,km_parse,detail_page


TODAY=date(2026,11,17)
BASE="https://www.carreraspopularescordoba.com/"
CORDOBA=BASE+"index.php/calendario/eventodetalle/395/-/xxxvi-canada-real-soriana"
GT="https://www.global-tempo.com/carreras.php?id=3204"


def homepage():
    return """<html><body><h3>Próximas Carreras</h3>
      <span>22Nov - </span><a href="/index.php/calendario/eventodetalle/395/-/xxxvi-canada-real-soriana">XXXVI CAÑADA REAL SORIANA</a>
      <span>28Nov - </span><a href="/index.php/calendario/eventodetalle/390/-/xiv-carrera-del-kilo-de-benameji">XIV CARRERA DEL KILO DE BENAMEJÍ</a>
      <a href="/index.php/calendario/">Ver el Calendario Completo</a>
      <a href="https://www.global-tempo.com/carreras.php?id=123">Enlace externo</a>
    </body></html>"""


def detail(name,day):
    return (f"<main><h2>Calendario de eventos</h2><nav>Anual Mensual Semanal Hoy</nav>"
            f"<div><h1>{name}</h1><span>{day}</span></div>"
            f"<h3>Próximas Carreras</h3><div>22 Noviembre 2026</div></main>")


class CircuitoCordobes(unittest.TestCase):
    def test_enlaces_de_eventos_sin_otros_dominios(self):
        links=circuito_links(homepage())
        self.assertEqual(len(links),2)
        self.assertEqual(links[0],(CORDOBA,"XXXVI CAÑADA REAL SORIANA"))

    def test_fecha_con_ano_en_ficha_es_obligatoria(self):
        title="XXXVI CAÑADA REAL SORIANA"
        race=circuito_detail(detail(title,"Domingo, 22 Noviembre 2026"),
                             CORDOBA,title,TODAY)
        self.assertEqual(race["fecha"],"2026-11-22")
        self.assertEqual(race["localidad"],"Córdoba")
        self.assertEqual(race["provincia"],"Córdoba")
        self.assertEqual(race["enlace"],CORDOBA)
        self.assertEqual(race["origen"],"circuito_cordoba")
        self.assertEqual(race["distancia"],"")
        self.assertTrue(race["fuente_directa"])

    def test_carrera_nueva_benameji_municipio_explicito(self):
        url=BASE+"index.php/calendario/eventodetalle/390/-/xiv-carrera-del-kilo-de-benameji"
        title="XIV CARRERA DEL KILO DE BENAMEJÍ"
        result=circuito_detail(detail(title,"Sábado, 28 Noviembre 2026"),url,title,TODAY)
        self.assertEqual(result["localidad"],"Benamejí")
        self.assertEqual(result["fecha"],"2026-11-28")

    def test_no_inventar_ano_ni_municipio(self):
        title="XXXVI CAÑADA REAL SORIANA"
        self.assertIsNone(circuito_detail(detail(title,"Domingo, 22 Noviembre"),
                                          CORDOBA,title,TODAY))
        self.assertEqual(event_city("Prueba Popular Sin Lugar"),"")
        self.assertEqual(event_city("Carrera Córdoba-Almodóvar del Río"),"")

    def test_no_mezclar_fecha_de_otra_carrera(self):
        title="XXXVI CAÑADA REAL SORIANA"
        self.assertIsNone(circuito_detail(detail("Carrera totalmente distinta",
                                                  "Domingo, 22 Noviembre 2026"),
                                          CORDOBA,title,TODAY))
        self.assertIsNone(circuito_detail(detail(title,"Domingo, 22 Noviembre 2025"),
                                          CORDOBA,title,TODAY))
        self.assertIsNone(circuito_detail(detail(title,"Domingo, 32 Noviembre 2026"),
                                          CORDOBA,title,TODAY))

    def test_triatlon_no_incorporado(self):
        self.assertEqual(event_city("Triatlón de Benamejí"),"")
        self.assertEqual(event_city("Senderismo por Montoro"),"")

    def test_solo_la_modalidad_documentada(self):
        title="16º CROSS EL HECHO DE GUADALCÁZAR"
        url=BASE+"index.php/calendario/eventodetalle/393/-/cross-guadalcazar"
        row=circuito_detail(detail(title,"Sábado, 12 Diciembre 2026"),url,title,TODAY)
        self.assertEqual(row["modalidad"],"CROSS")

    def test_cotejo_con_otra_fuente_no_genera_doble_carrera(self):
        old={"fecha":"2026-11-22","nombre":"XXXV Carrera Popular Cañada Real Soriana",
             "localidad":"Córdoba","provincia":"Córdoba","modalidad":"RUNNING",
             "distancia":"11 km","enlace":BASE,"fuente":BASE}
        new=circuito_detail(detail("XXXVI CAÑADA REAL SORIANA",
                                    "Domingo, 22 Noviembre 2026"),
                            CORDOBA,"XXXVI CAÑADA REAL SORIANA",TODAY)
        self.assertTrue(same_event(old,new))
        merged=combine([], [new,old],slugify,km_parse)
        self.assertEqual(len(merged),1)


class EnlacesSinCopiarGlobalTempo(unittest.TestCase):
    def setUp(self):
        self.registration={
            "revision":"2026-11-17",
            "carreras":[{
                "fecha":"2026-11-22","nombre":"VI CxM Albuñol Trail La Contraviesa",
                "localidad":"Albuñol","provincia":"Granada","modalidad":"TRAIL",
                "distancia":"25 km","fuente":GT}]}
        self.independent={
            "fecha":"2026-11-22",
            "nombre":"VI CxM Albuñol Trail de la Contraviesa",
            "localidad":"Albuñol y Sorvilán",
            "provincia":"Granada","modalidad":"TRAIL",
            "distancia":"",
            "fuente":"https://fadmes.es/calendario-fam/",
            "enlace":"https://fadmes.es/calendario-fam/",
            "origen":"fadmes",
        }

    def test_solo_fuente_institucional_activa_enlace(self):
        race=dict(self.independent,confirmada=False,slug="trail-contraviesa",
                  estado="Por confirmar",fecha_origen="fuente",consultado="2026-11-17")
        stats=match_registrations([race],[self.independent],self.registration)
        self.assertEqual(stats["asociados_con_fuente_independiente"],1)
        self.assertEqual(race["enlace"],GT)
        self.assertEqual(race["fuente"],"https://fadmes.es/calendario-fam/")
        self.assertIn("Fuente de verificación", detail_page(race))
        self.assertEqual(race["inscripcion_enlace"],GT)

    def test_no_utilizar_globaltempo_como_unica_confirmacion(self):
        race=dict(self.independent,enlace=GT,fuente=GT)
        stats=match_registrations([race],[],self.registration)
        self.assertEqual(stats["asociados_con_fuente_independiente"],0)
        self.assertNotIn("inscripcion_enlace",race)
        self.assertEqual(len([race]),1)  # No crea registros

    def test_fecha_distinta_no_puede_vincularse(self):
        race=dict(self.independent,fecha="2026-11-29")
        stats=match_registrations([race],[self.independent],self.registration)
        self.assertEqual(stats["asociados_con_fuente_independiente"],0)
        self.assertNotIn("inscripcion_enlace",race)

    def test_ficha_con_inscripcion_ya_especifica_no_se_sustituye(self):
        official=dict(self.independent,
                      enlace="https://fadmes.es/competiciones/trail-contraviesa-2026/")
        race=dict(official,confirmada=False,slug="albu",estado="Por confirmar",
                  fecha_origen="fuente",consultado="2026-11-17")
        stats=match_registrations([race],[official],self.registration)
        self.assertEqual(stats["asociados_con_fuente_independiente"],1)
        self.assertEqual(race["enlace"],official["enlace"])
        self.assertIn('Inscripción en Global Tempo', detail_page(race))

    def test_no_enlazar_evento_diferente_en_mismo_municipio(self):
        fake=dict(self.independent,nombre="Otra carrera trail de Albuñol")
        races=[fake]
        stats=match_registrations(races,[fake],self.registration)
        self.assertEqual(stats["asociados_con_fuente_independiente"],0)


if __name__=="__main__":
    unittest.main()
