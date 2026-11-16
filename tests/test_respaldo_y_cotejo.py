"""Respaldo de eventos y cotejo de distancias por identidad de edición."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from multifuente import backup_runnink
from build import add_curated_distances
from captacion import enrich_distance_from_detail
from captacion_extra import gesconchip
from distancias import extract_races_section


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

    def test_nueva_localidad_gesconchip_rota_chipiona(self):
        html="""<a href="/app/prueba/informacion/xl-media-maraton-costa-de-la-luz">
            14 Mar 2027 XL MEDIA MARATÓN “COSTA DE LA LUZ” Rota-Chipiona - Cádiz
            </a>"""
        rows=gesconchip(html,date(2026,11,16))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["localidad"],"Rota-Chipiona")

    def test_pruebas_menu_no_interrumpe_carreras_reales(self):
        partes=["Gesconchip", "ÚLTIMA HORA", "INICIO", "PRUEBAS",
                "Próximas pruebas", "Resultados", "Circuitos", "SERVICIOS",
                "VII CROSS PINAR DEL REY", "FECHA", "22/11/2026",
                "LUGAR", "San Roque, Cádiz", "CARRERAS",
                "SUB 16 Y SUB 18 - 3.000 M - 10:30:00",
                "SUB 14 - 2.000 M. - 11:00:00",
                "SUB 12 - 1.000 M - 11:30:00",
                "SUB 10 - 500 M. - 11:50:00",
                "SUB 8 - 250 M. - 12:00:00",
                "SUB 20 A VETERANO M65 - 6.000 M - 13:15:00",
                "NORMATIVA", "Recorrido de otras carreras 21 km"]
        self.assertEqual(extract_races_section(partes),
                         "3 km · 2 km · 1 km · 500 m · 250 m · 6 km")

    def test_gesconchip_mtrs(self):
        text=["CARRERAS","7.770 M SUB 18 - 09:30:00",
              "2.590 MTRS SUB 16 - 10:00:00",
              "700 MTRS SUB 12","NORMATIVA","15 km de otro recorrido"]
        self.assertEqual(extract_races_section(text),"7,77 km · 2,59 km · 700 m")

    def test_genera_distancia_con_h1_generico_y_spans_separados(self):
        body=('<h1>Gesconchip</h1><h2>VII CROSS PINAR DEL REY</h2>'
              '<h3>CARRERAS</h3><span>6.000</span> <span>MTRS</span>'
              '<span>SUB 20</span><h3>NORMATIVA</h3>')
        row={"nombre":"VII CROSS PINAR DEL REY","distancia":"",
             "enlace":"https://gesconchip.es/prueba/informacion/vii-cross-pinar-del-rey"}
        self.assertTrue(enrich_distance_from_detail(row,body,"gesconchip"))
        self.assertEqual(row["distancia"],"6 km")

    def test_ficha_no_necesita_h1_si_h2_identifica_evento(self):
        html="<main><h2>VII CROSS PINAR DEL REY</h2><h3>CARRERAS</h3><p>6 KM - 13:15</p></main>"
        race={"nombre":"VII CROSS PINAR DEL REY","enlace":"https://gesconchip.es/prueba/informacion/vii-cross-pinar-del-rey","distancia":""}
        self.assertTrue(enrich_distance_from_detail(race,html,"gesconchip"))
        self.assertEqual(race["distancia"],"6 km")


if __name__=="__main__":
    unittest.main()
