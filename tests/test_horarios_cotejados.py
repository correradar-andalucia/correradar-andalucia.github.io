"""Horarios cotejados: identidad completa, procedencia y prioridad de datos actuales."""
import unittest
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build import add_curated_times

TODAY=date(2026,11,18)

def row(**extra):
    return dict(fecha="2026-12-05",nombre="Carrera X",localidad="Guaro",
                provincia="Málaga",hora="",**extra)

def entry(**extra):
    d=row()
    d.update(hora="11:00",fuente="https://example.org/carrera",cotejada="2026-11-18",
             nota="Prueba principal 12:15")
    d.update(extra)
    return d

class HorariosTests(unittest.TestCase):
    def test_fill_exact_edition(self):
        r=row()
        s=add_curated_times([r],{"carreras":[entry()]},TODAY)
        self.assertEqual(s["aplicadas"],1)
        self.assertEqual(r["hora"],"11:00")
        self.assertEqual(r["hora_origen"],"fuente")
        self.assertEqual(r["hora_fuente"],"https://example.org/carrera")
        self.assertEqual(r["hora_cotejada"],"2026-11-18")
    def test_wrong_edition_and_editorial(self):
        r=row(confirmada=True)
        a=row();a["fecha"]="2027-12-05"
        self.assertEqual(add_curated_times([r,a],{"carreras":[entry()]},TODAY)["aplicadas"],0)
    def test_current_wins(self):
        r=row();r["hora"]="09:00"
        self.assertEqual(add_curated_times([r],{"carreras":[entry()]},TODAY)["conflictos_no_sobrescritos"],1)
        self.assertEqual(r["hora"],"09:00")
    def test_invalid_or_duplicate(self):
        for e in [[entry(hora="25:00")],[entry(fuente="http://example.org")],
                  [entry(cotejada="2026-11-19")],[entry(),entry()]]:
            with self.assertRaises(ValueError):
                add_curated_times([row()],{"carreras":e},TODAY)
    def test_ambiguous_identity(self):
        self.assertEqual(add_curated_times([row(),row()],{"carreras":[entry()]},TODAY)["aplicadas"],0)

if __name__=="__main__":unittest.main()
