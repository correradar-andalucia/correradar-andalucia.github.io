"""Anomalías de cobertura: desapariciones futuras, fallos parciales y límites."""
import sys
import unittest
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from persistencia import restore_missing,coverage_anomalies
from captacion import is_access_restriction
from build import slugify,km_parse
from control_calidad import inspect_calendar
from test_persistencia import item,report,TODAY

def batch():
    return [item(nombre="Carrera "+name,slug=slugify(name),
                 localidad=city,fecha="2026-12-01")
            for name,city in [("alfa","Jerez"),("beta","Rota"),("gamma","Cádiz"),
                              ("delta","Chipiona"),("epsilon","San Roque"),("zeta","Algeciras")]]

class ContinuidadTests(unittest.TestCase):
    def test_partial_read_preserves_previous_dates(self):
        previous=batch()
        rows=[previous[0].copy()]
        rep=report(estado="leida",fallo_temporal=False)
        summary=restore_missing(rows,previous,rep,slugify,km_parse,TODAY)
        self.assertEqual(summary["recuperadas"],5)
        self.assertEqual(summary["perdidas_residuales"],{})
        self.assertEqual(summary["fuentes_con_lectura_anomala"]["runnink"]["ausentes"],5)
        self.assertTrue(rep["fuentes"]["runnink"]["lectura_anomala"])
        self.assertEqual({r["consultado"] for r in rows},{"2026-11-17"})
    def test_expiration_and_pauses(self):
        prev=batch()
        rep=report(estado="leida",fallo_temporal=False)
        self.assertEqual(coverage_anomalies([],prev,rep,date(2026,11,25)),{})
        self.assertEqual(coverage_anomalies([],prev,rep,date(2026,12,2)),{})
        for changed in [dict(acceso_restringido=True),dict(detalle_restringido=True),dict(estado="sin consulta automática")]:
            info=report(estado="leida",fallo_temporal=False)
            info["fuentes"]["runnink"].update(changed)
            self.assertEqual(restore_missing([],prev,info,slugify,km_parse,TODAY)["recuperadas"],0)
    def test_date_correction_and_distance_update(self):
        prev=batch()
        rows=[dict(r,distancia="25 km") for r in prev]
        rows[0]["fecha"]="2026-12-02"
        self.assertEqual(coverage_anomalies(rows,prev,report(estado="leida"),TODAY),{})
    def test_unknown_outage_blocks_large_loss_without_restoring(self):
        prev=batch()
        rows=[]
        rep=report(fallo_temporal=False)
        summary=restore_missing(rows,prev,rep,slugify,km_parse,TODAY)
        self.assertEqual(summary["recuperadas"],0)
        self.assertEqual(summary["perdidas_residuales"]["runnink"]["ausentes"],6)
        rep["nombres_fuentes_habilitadas"]=["runnink","faa","dorsalchip"]
        rep["fuentes_con_consulta_habilitada"]=3
        rep["fuentes"].update(faa={"estado":"leida"},dorsalchip={"estado":"leida"})
        valid=item(fecha_origen="fuente",distancia_origen="fuente")
        result=inspect_calendar([valid],rep,TODAY,continuidad=summary)
        self.assertFalse(result["apto_para_desplegar"])
        self.assertTrue(any("Pérdida anómala" in x for x in result["bloqueos"]))
    def test_restriction_wrapped(self):
        try:
            try: raise HTTPError("https://example.org",403,"Forbidden",{},None)
            except HTTPError as exc: raise RuntimeError("robots.txt HTTP 403") from exc
        except RuntimeError as exc:
            self.assertTrue(is_access_restriction(exc))
        self.assertTrue(is_access_restriction(RuntimeError("robots.txt prohíbe la consulta")))
        self.assertFalse(is_access_restriction(TimeoutError()))

if __name__=="__main__":unittest.main()
