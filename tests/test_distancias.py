"""No ocultar distancias expresas ni inventar kilómetros de otros eventos."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from distancias import extract_distance, extract_modalities_distance
from captacion import parse_fadmes, dorsal_detail


class DistanciasExplicitas(unittest.TestCase):
    def test_bloque_modalidades(self):
        self.assertEqual(extract_modalities_distance(
            ["Modalidades", "Trail corto", "12 km", "Trail largo", "24 km",
             "Inscripciones", "Carrera 5 km recomendada"]), "12 km · 24 km")

    def test_no_traer_distancia_de_otras_carreras(self):
        self.assertEqual(extract_modalities_distance(
            ["Otras carreras", "Trail 10 km", "Recomendaciones"]), "")

    def test_dorsal_modalidades_en_ficha(self):
        page = ('<main><div>Carrera Popular del Puerto</div>'
                '<div>22/11/2026</div><div>El Puerto de Santa María</div>'
                '<div>Cádiz</div><h2>Modalidades</h2><div>5 km</div>'
                '<div>10 km</div><h2>Inscripciones</h2><div>21 km</div></main>')
        row = dorsal_detail(page, "https://dorsalchip.es/carrera/2026/11/22/puerto.aspx",
                            date(2026, 11, 15))
        self.assertEqual(row["distancia"], "5 km · 10 km")

    def test_10k_titulo(self):
        self.assertEqual(extract_distance("XX Carrera 10K de Prueba"), "10 km")

    def test_varias_distancias_en_campo(self):
        self.assertEqual(extract_distance("Trail de prueba",
                         ["Distancias:", "5 km / 10 km", "Inscripciones"]),
                         "5 km · 10 km")

    def test_distancia_no_se_infiere_de_media_maraton(self):
        self.assertEqual(extract_distance("Media Maratón Sierra", []), "")

    def test_no_recoger_distancias_de_pruebas_distintas(self):
        self.assertEqual(extract_distance("Trail de prueba",
                         ["Otras carreras", "Carrera 15 km", "Carrera 21 km"]), "")

    def test_contradiccion_se_oculta(self):
        self.assertEqual(extract_distance("Trail de Prueba 10 km",
                         ["Distancia:", "21 km"]), "")

    def test_desnivel_no_es_distancia(self):
        self.assertEqual(extract_distance("Trail de prueba",
                         ["Desnivel", "500 m", "Próximas carreras"]), "")

    def test_fadmes_distancia_en_nombre(self):
        page = ('<table><tr><td>22/11/2026</td><td>22/11/2026</td>'
                '<td>CxM</td><td>Trail Costa 12 km</td><td>Otros</td>'
                '<td>Almería</td><td>Almería</td></tr></table>')
        rows = parse_fadmes(page, date(2026, 11, 15))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["distancia"], "12 km")

    def test_dorsal_detail_field(self):
        page = ('<main><div>Carrera Popular del Puerto</div>'
                '<div>22/11/2026</div><div>El Puerto de Santa María</div>'
                '<div>Cádiz</div><div>Distancia</div><div>10 km</div></main>')
        row = dorsal_detail(page, "https://dorsalchip.es/carrera/2026/11/22/puerto.aspx",
                            date(2026, 11, 15))
        self.assertIsNotNone(row)
        self.assertEqual(row["distancia"], "10 km")


if __name__ == "__main__":
    unittest.main()
