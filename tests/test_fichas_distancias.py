"""Fichas de fuentes originales: extraer distancias sin mezclar carreras ni desnivel."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from captacion import enrich_booking_distance,enrich_distance_from_detail
from distancias import (extract_races_section,extract_narrative_distance,
                        extract_booking_distance,extract_distance)


class DistanciasEnFichas(unittest.TestCase):
    def test_gesconchip_varias_categorias_y_metros_millares(self):
        body="""<main><h1>VII CROSS PINAR DEL REY</h1><div>FECHA</div>
        <div>22/11/2026</div><h3>CARRERAS</h3>
        <p>SUB 16 Y SUB 18 - 3.000 M - 10:30:00</p>
        <p>SUB 14 - 2.000 M. - 11:00:00</p>
        <p>SUB 10 - 500 M. - 11:50:00</p>
        <p>SUB 20 A VETERANO - 6.000 M - 13:15:00</p>
        <h3>NORMATIVA</h3><p>Avituallamiento en el km 5</p></main>"""
        race={"nombre":"VII CROSS PINAR DEL REY",
              "enlace":"https://gesconchip.es/app/prueba/informacion/vii-cross-pinar-del-rey",
              "distancia":""}
        self.assertTrue(enrich_distance_from_detail(race,body,"gesconchip"))
        self.assertEqual(race["distancia"],"3 km · 2 km · 500 m · 6 km")
        self.assertEqual(race["distancia_fuente"],race["enlace"])

    def test_gesconchip_dos_rutas(self):
        fragments=["XIV GRAN FONDO GUADIAMAR","FECHA","31/01/2027","CARRERAS",
                   "31 K - 09:15:00","15 K - 10:30:00",
                   "NORMATIVA","Recorrido 30 km aproximado"]
        self.assertEqual(extract_races_section(fragments),"31 km · 15 km")

    def test_runnink_descripcion_introduccion(self):
        body="""<main><h1>XXX Carrera Popular Puerto Menesteo</h1>
        <h2>XXX Carrera Popular Puerto Menesteo</h2>
        <p>El 22 de noviembre vuelve la clásica Carrera Popular Puerto Menesteo
        para celebrar su treinta edición. La prueba contará con carreras de menores
        y una carrera reina de 10 kilómetros con inicio y meta en la Ciudad Deportiva.</p>
        <h3>¿Quieres participar?</h3><div>Otras pruebas 21 km</div></main>"""
        race={"nombre":"XXX Carrera Popular Puerto Menesteo","distancia":"",
              "enlace":"https://www.runnink.com/evento/xxx-carrera-popular-puerto-menesteo/121"}
        self.assertTrue(enrich_distance_from_detail(race,body,"runnink"))
        self.assertEqual(race["distancia"],"10 km")

    def test_runnink_respaldo_pagina_modalidades(self):
        body="""<main><h1>XXX Carrera Popular Puerto Menesteo</h1>
        <p>Selecciona la modalidad:</p><h2>Carrera</h2>
        <p>domingo 22 de noviembre de 2026</p><p>10:00 h</p>
        <p>10 km</p><p>12 €</p><h2>Menores</h2>
        <p>Varias</p><p>3 €</p><p>Runnink © 2026</p></main>"""
        race={"nombre":"XXX Carrera Popular Puerto Menesteo","distancia":""}
        url="https://www.runnink.com/book/121"
        self.assertTrue(enrich_booking_distance(race,body,url))
        self.assertEqual(race["distancia"],"10 km")
        self.assertEqual(race["distancia_fuente"],url)

    def test_no_extraer_carrera_ajena(self):
        body="""<main><h1>Carrera Popular Pueblo A</h1>
        <h3>CARRERAS</h3><p>5 KM</p></main>"""
        race={"nombre":"Otra carrera del Pueblo B","distancia":""}
        self.assertFalse(enrich_distance_from_detail(race,body,"gesconchip"))
        self.assertEqual(race["distancia"],"")

    def test_enlaces_no_reemplazan_distancia_existente(self):
        body="""<main><h1>Trail de la Sierra</h1>
        <h3>CARRERAS</h3><p>15 KM</p></main>"""
        race={"nombre":"Trail de la Sierra","distancia":"12 km"}
        self.assertFalse(enrich_distance_from_detail(race,body,"gesconchip"))
        self.assertEqual(race["distancia"],"12 km")

    def test_no_arrastrar_kilometros_de_otras_recomendaciones(self):
        fragments=["Carrera 2026","El recorrido urbano tiene premios",
                   "¿Quieres participar?","Te recomendamos","Carrera de 21 kilómetros"]
        self.assertEqual(extract_narrative_distance(fragments),"")

    def test_metros_sin_punto(self):
        self.assertEqual(extract_distance("Cross","Distancia: 3000 m".split("|")),"3 km")

    def test_desnivel_positivo_descartado(self):
        self.assertEqual(extract_distance("Trail",
                         ["Distancia", "1000 m+ desnivel positivo"]),"")

    def test_titulo_trail_12k(self):
        self.assertEqual(extract_distance("Trail Corto 12K"),"12 km")


if __name__=="__main__":
    unittest.main()
