"""Pruebas sintéticas sin consultar sitios externos."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from captacion import parse_fadmes, parse_dorsalchip

class CaptacionTests(unittest.TestCase):
    def test_tabla_cxm(self):
        page="""<table>
          <tr><th>Inicio</th><th>Fin</th><th>Tipo</th><th>Nombre</th><th>Prueba</th><th>Localidad</th><th>Provincia</th></tr>
          <tr><td>21/11/2026</td><td>21/11/2026</td><td>CxM</td><td>Tiñosa Trail</td><td>Copa</td><td>Priego de Córdoba</td><td>Córdoba</td></tr>
          <tr><td>22/11/2026</td><td>22/11/2026</td><td>Senderismo</td><td>Ruta del Río</td><td>Copa</td><td>Granada</td><td>Granada</td></tr></table>"""
        data=parse_fadmes(page,date(2026,11,15))
        self.assertEqual(len(data),1)
        self.assertEqual(data[0]["provincia"],"Córdoba")
        self.assertEqual(data[0]["modalidad"],"TRAIL")

    def test_dorsal_aprobado_y_triatlon_excluido(self):
        page="""<a href="/carrera/2026/11/22/Run_UMA.aspx">
          <span>22/11/2026</span><span>We Run UMA</span><span>Málaga, Málaga</span>
          </a><a href="/carrera/2026/11/28/Triatlon.aspx">
          <span>28/11/2026</span><span>Triatlón Indoor</span><span>Torremolinos, Málaga</span></a>"""
        data=parse_dorsalchip(page,date(2026,11,15))
        self.assertEqual(len(data),1)
        self.assertEqual(data[0]["nombre"],"We Run UMA")
        self.assertEqual(data[0]["localidad"],"Málaga")

    def test_dorsal_enlace_con_datos_en_un_solo_nodo(self):
        page='<a href="/carrera/2026/11/21/7_Ecomaraton_La_Donaira.aspx">21/11/2026 7 Ecomaratón La Donaira El Gastor, Cádiz Prueba cronometrada por dorsalChip</a>'
        data=parse_dorsalchip(page,date(2026,11,15))
        self.assertEqual(len(data),1)
        self.assertEqual(data[0]["nombre"],"7 Ecomaratón La Donaira")
        self.assertEqual(data[0]["localidad"],"El Gastor")

    def test_dorsal_sin_localidad_se_descarta(self):
        data=parse_dorsalchip('<a href="/carrera/2026/12/02/trail.aspx">02/12/2026 Gran Trail</a>',date(2026,11,15))
        self.assertEqual(data,[])

    def test_datos_pasados_se_descartan(self):
        html='<table><tr><td>14/11/2026</td><td></td><td>CxM</td><td>Trail</td><td></td><td>Motril</td><td>GRANADA</td></tr></table>'
        self.assertEqual(parse_fadmes(html,date(2026,11,15)),[])

if __name__=="__main__":unittest.main()
