"""Respaldo temporal de carreras: no equivale a una nueva verificación."""
import sys
import unittest
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from tempfile import TemporaryDirectory
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))

from persistencia import restore_missing, distance_backlog, read_previous
from captacion import is_transient_failure
from build import slugify, km_parse

TODAY=date(2026,11,18)
R="https://www.runnink.com/evento/carrera-pueblo/123"

def item(**kw):
    row=dict(fecha="2026-12-01",nombre="Carrera Pueblo",localidad="Jerez de la Frontera",
             provincia="Cádiz",modalidad="RUNNING",origen="runnink",confirmada=False,
             fuente=R,enlace=R,slug="carrera-pueblo",consultado="2026-11-17",
             distancia="10 km",distancia_fuente=R,distancia_cotejada="2026-11-17")
    row.update(kw)
    return row

def report(**kw):
    sources=dict(estado="no disponible",fallo_temporal=True)
    sources.update(kw)
    return {"nombres_fuentes_habilitadas":["runnink"],
            "fuentes":{"runnink":sources}}

class PersistenciaTests(unittest.TestCase):
    def restore(self,previous,races=None,rep=None,today=TODAY):
        rows=[] if races is None else races
        result=restore_missing(rows,previous,rep or report(),slugify,km_parse,today)
        return rows,result

    def test_source_outage_preserves_actual_dates(self):
        rows,summary=self.restore([item()])
        self.assertEqual(summary["recuperadas"],1)
        self.assertTrue(rows[0]["respaldo_temporal"])
        self.assertEqual(rows[0]["consultado"],"2026-11-17")
        self.assertEqual(rows[0]["fecha_origen"],"catalogo")
        self.assertEqual(rows[0]["distancia"],"10 km")
        self.assertEqual(rows[0]["distancia_cotejada"],"2026-11-17")

    def test_no_restore_successful_empty_listing(self):
        rows,_=self.restore([item()],rep=report(estado="leida"))
        self.assertEqual(rows,[])

    def test_no_restore_access_denial(self):
        rows,_=self.restore([item()],rep=report(fallo_temporal=False))
        self.assertEqual(rows,[])

    def test_no_restore_paused_source(self):
        r=report()
        r["nombres_fuentes_habilitadas"]=[]
        rows,_=self.restore([item()],rep=r)
        self.assertEqual(rows,[])

    def test_no_restore_old_or_expired(self):
        rows,_=self.restore([item(consultado="2026-11-01"),item(fecha="2026-11-16")])
        self.assertEqual(rows,[])

    def test_no_duplicate_or_date_conflict(self):
        current=[item(fecha="2026-12-02")]
        rows,summary=self.restore([item()],races=current)
        self.assertEqual(summary["recuperadas"],0)
        self.assertEqual(len(rows),1)

    def test_no_foreign_host(self):
        rows,_=self.restore([item(fuente="https://example.org/carrera")])
        self.assertFalse(rows)

    def test_http_failure_types(self):
        self.assertTrue(is_transient_failure(URLError(TimeoutError())))
        self.assertTrue(is_transient_failure(HTTPError(R,503,"Unavailable",{},None)))
        self.assertFalse(is_transient_failure(HTTPError(R,403,"Forbidden",{},None)))
        self.assertFalse(is_transient_failure(RuntimeError("robots.txt prohíbe la consulta")))

    def test_backlog_inventories_estimates_and_future(self):
        rows=[item(distancia=""),item(nombre="orientativa",distancia="",distancia_orientativa="5–8 km"),
              item(nombre="known"),item(fecha="2026-11-17",distancia="")]
        b=distance_backlog(rows,TODAY)
        self.assertEqual(b["total"],2)
        self.assertEqual(b["orientativas"],1)
        self.assertEqual(b["pendientes"][0]["prioridad"],"alta")

    def test_previous_invalid(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"prev.json"
            p.write_text("[]")
            self.assertEqual(read_previous(p),[])
            p.write_text(json.dumps({"carreras":[{},None]}))
            self.assertEqual(read_previous(p),[{}])

if __name__=="__main__":unittest.main()
