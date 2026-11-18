"""Panel: recuentos reales, enlaces seguros y comparación no equivalente a correo."""
from datetime import datetime
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from panel import panel_page, comparison

NOW=datetime(2026,11,18,13,0,tzinfo=ZoneInfo("Europe/Madrid"))
def race(**extra):
    r={"fecha":"2026-12-01","nombre":"Carrera Pueblo","localidad":"Jerez de la Frontera",
       "provincia":"Cádiz","modalidad":"RUNNING","slug":"carrera-pueblo","distancia":"",
       "hora":"","fuente":"https://example.org/carrera","enlace":"https://example.org/carrera"}
    r.update(extra)
    return r

class PanelTests(unittest.TestCase):
    def test_metrics_and_source_health(self):
        capture={"nombres_fuentes_habilitadas":["runnink","diphuelva"],"fuentes":{
             "runnink":{"estado":"leida","candidatas":3},
             "diphuelva":{"estado":"no disponible","fallo_temporal":True,"motivo":"SECRET_SENTINEL"}}}
        page=panel_page([race(),race(nombre="Otra carrera",slug="otra",distancia="5 km")],
                        capture,{"respaldo_carreras":{"recuperadas":1}},
                        {"apto_para_desplegar":True},now=NOW,run_id="123")
        for text in ("1/2","50%","Fallo temporal","1 pendientes","/actions/runs/123",
                     "noindex,nofollow","Inscripción conocida","Google Alerts","carreras conservadas"):
            self.assertIn(text,page)
        self.assertNotIn("SECRET_SENTINEL",page)
        self.assertNotIn("<script",page)
    def test_compare_no_previous_and_date_correction(self):
        self.assertIsNone(comparison([race()],[]))
        self.assertEqual(comparison([race(fecha="2026-12-02")],[race()])["nuevas"],[])
        new=race(nombre="Otra carrera distinta",localidad="Rota",slug="otra")
        self.assertEqual(comparison([race(),new],[race()])["nuevas"],[new])
    def test_escape_and_no_false_novelty(self):
        page=panel_page([race(nombre="<script>alert(1)</script>",fuente="javascript:alert(1)")],
                        {},{},{"apto_para_desplegar":True},now=NOW,run_id="<script>")
        self.assertNotIn("<script>",page)
        self.assertNotIn("javascript:",page)
        self.assertIn("Sin una publicación anterior comparable",page)
        self.assertIn("público no indexado",page)
    def test_offline_is_not_live(self):
        page=panel_page([],{"modo":"Prueba local sin conexión"},{},{},now=NOW)
        self.assertIn("Sin consulta (prueba local)",page)
        self.assertIn("Sin red",page)

if __name__=="__main__":unittest.main()
