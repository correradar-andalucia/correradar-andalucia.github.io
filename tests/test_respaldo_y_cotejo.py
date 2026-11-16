"""Respaldo de eventos y cotejo de distancias por identidad de edición."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from multifuente import backup_runnink
from build import add_curated_distances
from captacion import enrich_distance_from_detail


class RespaldoYCuracion(unittest.TestCase):
    def test_runnink_guarda_13_carreras_anteriores(self):
        races=backup_runnink(date(2026,11,16))
        self.assertEqual(len(races),13)
        self.assertEqual(len({r["enlace"] for r in races}),13)
        self.assertTrue(all(r["verificado"]=="2026-11-16" for r in races))
        self.assertTrue(all("Cotejada" in r["estado"] for r in races))

    def test_runnink_no_muestra_carreras_pasadas(self):
        races=backup_runnink(date(2027,1,1))
        self.assertTrue(races)
        self.assertTrue(all(r["fecha"]>="2027-01-01" for r in races))
        self.assertTrue(all("RECONFIRMAR" in r["estado"] for r in races))

    def test_cotejar_solo_fecha_nombre_y_localidad(self):
        one={"fecha":"2026-11-22","nombre":"ALPINA SIERRA DE GADOR DALIAS",
             "localidad":"DALIAS","provincia":"Almería","distancia":""}
        another={"fecha":"2027-11-22","nombre":one["nombre"],
                 "localidad":"DALIAS","provincia":"Almería","distancia":""}
        result=add_curated_distances([one,another])
        self.assertEqual(result["aplicadas"],1)
        self.assertIn("21,6 km",one["distancia"])
        self.assertTrue(one["distancia_fuente"].startswith("https://"))
        self.assertEqual(another["distancia"],"")

    def test_no_sobrescribir_distancia_en_conflicto(self):
        one={"fecha":"2026-11-22","nombre":"VII CROSS PINAR DEL REY",
             "localidad":"San Roque","provincia":"Cádiz","distancia":"5 km"}
        result=add_curated_distances([one])
        self.assertEqual(result["aplicadas"],0)
        self.assertEqual(result["conflictos_no_sobrescritos"],1)
        self.assertEqual(one["distancia"],"5 km")

    def test_ficha_no_necesita_h1_si_h2_identifica_evento(self):
        html="<main><h2>VII CROSS PINAR DEL REY</h2><h3>CARRERAS</h3><p>6 KM - 13:15</p></main>"
        race={"nombre":"VII CROSS PINAR DEL REY","enlace":"https://gesconchip.es/prueba/informacion/vii-cross-pinar-del-rey","distancia":""}
        self.assertTrue(enrich_distance_from_detail(race,html,"gesconchip"))
        self.assertEqual(race["distancia"],"6 km")


if __name__=="__main__":
    unittest.main()
