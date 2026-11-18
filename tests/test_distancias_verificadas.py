"""Regresiones de enriquecimiento prudente y respaldo de kilómetros."""
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from captacion import (SOURCES, dorsal_links, enrich_distance_from_detail, collect,
                       MAX_ENRIQUECIMIENTO_RUNNINK)
from build import preserve_previous_distances, add_granada_cross_notes

TODAY=date(2026,11,18)
URL="https://www.runnink.com/evento/montesierra-trail-la-teja/100"

def race(**kw):
    r={"fecha":"2026-12-06","nombre":"Montesierra Trail La Teja",
       "localidad":"Jerez de la Frontera","provincia":"Cádiz",
       "distancia":"","fuente":URL,"enlace":URL}
    r.update(kw)
    return r

class DistanciasVerificadas(unittest.TestCase):
    def test_dorsal_prioriza_fichas_futuras(self):
        page=''.join(f'<a href="/carrera/2026/10/{n}/pasada.aspx">pasada</a>'
                     for n in range(1,30))
        page+='<a href="/carrera/2026/12/06/futura.aspx">futura</a>'
        self.assertEqual(dorsal_links(page,TODAY),
                         ["https://dorsalchip.es/carrera/2026/12/06/futura.aspx"])

    def test_runnink_modalidades_de_la_edicion_correcta(self):
        html=('<h1>Montesierra Trail La Teja</h1><h3>06 de diciembre de 2026</h3>'
              '<p>Habrá tres modalidades: Trail Largo de 18 km, Trail Corto de 10 km.</p>'
              '<h3>¿Quieres participar?</h3><p>Te recomendamos otra carrera de 50 km.</p>')
        row=race()
        self.assertTrue(enrich_distance_from_detail(row,html,"runnink"))
        self.assertEqual(row["distancia"],"18 km · 10 km")
        self.assertFalse(enrich_distance_from_detail(race(fecha="2027-12-06"),html,"runnink"))
    
    def test_runnink_limitado_y_gesconchip_sin_ampliacion(self):
        rows=[race(nombre=f"Trail número {i}",enlace=f"https://www.runnink.com/evento/trail/{i}")
              for i in range(20)]
        with patch("captacion.fuentes_habilitadas",return_value={"runnink","gesconchip"}), \
             patch("captacion_extra.runnink",return_value=rows), \
             patch("captacion_extra.gesconchip",return_value=[race(enlace="https://gesconchip.es/prueba/informacion/trail")]), \
             patch("captacion.fetch_if_permitted",return_value="<html></html>") as fetch, \
             patch("captacion.time.sleep"), \
             patch.dict(os.environ,{"CORRERADAR_DISTANCE_ENRICHMENT":"yes","CORRERADAR_FETCH":"1","GLOBALTEMPO_AUTHORIZED":""}):
            _,rep=collect(TODAY)
        self.assertEqual(fetch.call_count,2+MAX_ENRIQUECIMIENTO_RUNNINK)
        self.assertTrue(all("/book/" not in call.args[0] for call in fetch.call_args_list))
        self.assertEqual(rep["fuentes"]["gesconchip_detalle"]["consultadas"],0)

    def test_respaldo_con_fecha_fuente_y_misma_edicion(self):
        checked=race(distancia="18 km · 10 km",distancia_fuente=URL,
                     distancia_origen="fuente",distancia_cotejada="2026-11-17")
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"previous.json"
            path.write_text(json.dumps({"carreras":[checked]}))
            same=race()
            changed=race(fecha="2027-12-06")
            new_value=race(distancia="20 km")
            approved=race(confirmada=True)
            result=preserve_previous_distances([same,changed,new_value,approved],path,TODAY)
            self.assertEqual(result["recuperadas"],1)
            self.assertEqual(same["distancia"],"18 km · 10 km")
            self.assertEqual(same["distancia_origen"],"catalogo")
            self.assertEqual(same["distancia_cotejada"],"2026-11-17")
            self.assertEqual(changed["distancia"],"")
            self.assertEqual(new_value["distancia"],"20 km")
            self.assertEqual(approved["distancia"],"")
            old=race()
            self.assertEqual(preserve_previous_distances([old],path,date(2026,12,25))["recuperadas"],0)

    def test_granada_estimaciones_no_son_distancias_del_filtro(self):
        item={"fecha":"2026-12-13","nombre":"XXX Circuito Provincial de Campo a Través — Lecrín",
              "localidad":"Lecrín","provincia":"Granada","distancia":""}
        self.assertEqual(add_granada_cross_notes([item]),1)
        self.assertIn("5,5–8 km",item["distancia_orientativa"])
        self.assertEqual(item["distancia"],"")
        self.assertIn("Normativa-Cross-2027.pdf",item["distancia_orientativa_fuente"])

if __name__=="__main__":unittest.main()
