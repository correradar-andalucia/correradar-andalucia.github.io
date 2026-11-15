"""Regresiones para el catálogo multifuente de CorreRadar."""
import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from multifuente import seed_races
from deduplicacion import combine, verify_unique

class SemillaMultifuente(unittest.TestCase):
    def test_78_registros_de_ocho_fuentes(self):
        rows = seed_races(dt.date(2026, 11, 15))
        self.assertEqual(len(rows), 78)
        self.assertEqual(len({r["origen"] for r in rows}), 8)

    def test_76_eventos_unicos(self):
        rows = seed_races(dt.date(2026, 11, 15))
        result = combine([], rows, lambda x:x.lower().replace(" ","-"), lambda x:0)
        self.assertGreaterEqual(len(result), 69)
        self.assertLessEqual(len(result), 78)
        self.assertTrue(verify_unique(result))
        self.assertEqual(len({r["provincia"] for r in result}), 8)

    def test_revalidacion_datos_antiguos(self):
        rows = seed_races(dt.date(2026, 12, 16))
        self.assertGreater(len(rows), 0)
        self.assertTrue(all("RECONFIRMAR" in r["estado"] for r in rows))
        self.assertTrue(any(r["origen"]=="globaltempo" for r in rows))

    def test_global_tempo_siete_carreras(self):
        rows = seed_races(dt.date(2026, 11, 15))
        globaltempo=[r for r in rows if r["origen"]=="globaltempo"]
        self.assertEqual(len(globaltempo),7)
        self.assertTrue(all(r["fuente"].startswith("https://") for r in globaltempo))


    def test_prioridad_aprobadas(self):
        candidates = seed_races(dt.date(2026, 11, 15))
        one = candidates[0]
        approved = [dict(one, estado="Publicada", slug="original", distancia="42 km")]
        result = combine(approved, candidates, lambda x:x.lower().replace(" ","-"), lambda x:0)
        found = [r for r in result if r["fecha"] == one["fecha"] and r["nombre"] == one["nombre"]]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["distancia"], "42 km")

if __name__ == "__main__":
    unittest.main()
