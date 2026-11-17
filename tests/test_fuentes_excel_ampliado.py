"""Ampliación aportada en Excel: nunca convertir agregadores en confirmación."""
import json
import sys
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build import add_curated_distances


class ExcelDeFuentes(unittest.TestCase):
    def test_catalogo_importado_y_separacion_agregadores(self):
        data=json.loads((ROOT/"config"/"fuentes_ampliadas_2026-11-17.json").read_text(encoding="utf-8"))
        self.assertEqual(data["total_fuentes"],45)
        self.assertEqual(len(data["fuentes"]),45)
        self.assertEqual(Counter(r["hoja"].split(".")[0] for r in data["fuentes"]),
                         {"1":4,"2":10,"3":9,"4":8,"5":8,"6":6})
        for record in data["fuentes"]:
            self.assertTrue(record["url"].startswith("https://"))
            self.assertFalse(record["ingesta_automatica_nueva"])
            if record["rol"]=="agregador":
                self.assertFalse(record["permite_confirmar"])
        self.assertEqual(sum(r["rol"]=="agregador" for r in data["fuentes"]),10)

    def test_distancias_completadas_en_carreras_ya_existentes(self):
        rows=[
            {"fecha":"2026-11-28","nombre":"Benamejí","localidad":"Benamejí","provincia":"Córdoba","distancia":"","km":0},
            {"fecha":"2026-12-07","nombre":"Rute","localidad":"Rute","provincia":"Córdoba","distancia":"","km":0},
            {"fecha":"2026-12-07","nombre":"Carrera de Rute","localidad":"Rute","provincia":"Córdoba","distancia":"","km":0},
            {"fecha":"2026-12-31","nombre":"42º San Silvestre Cordobesa","localidad":"Córdoba","provincia":"Córdoba","distancia":"","km":0}
        ]
        stat=add_curated_distances(rows)
        self.assertEqual(stat["aplicadas"],4)
        self.assertEqual([r["distancia"] for r in rows],
                         ["7 km","5,5 km","5,5 km","10 km"])
        self.assertTrue(all(r["distancia_origen"]=="fuente" for r in rows))
        self.assertTrue(all(r["distancia_cotejada"]=="2026-11-17" for r in rows))

    def test_no_sobrescribir_otra_distancia_publicada(self):
        rows=[{"fecha":"2026-11-28","nombre":"Benamejí","localidad":"Benamejí",
               "provincia":"Córdoba","distancia":"8 km","km":8}]
        stat=add_curated_distances(rows)
        self.assertEqual(stat["aplicadas"],0)
        self.assertEqual(stat["conflictos_no_sobrescritos"],1)
        self.assertEqual(rows[0]["distancia"],"8 km")


if __name__=="__main__":
    unittest.main()
