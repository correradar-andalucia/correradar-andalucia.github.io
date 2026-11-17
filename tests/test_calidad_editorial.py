"""Regresiones de calidad editorial: no se inventan datos ni se confunden fuentes con verificación."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from captacion import parse_cruzando_detail
from deduplicacion import combine, same_event, valid_locality
from build import detail_page, sitemap, slugify, km_parse

URL = "https://dorsalchip.es/carrera/2026/11/21/la-donaira.aspx"


def race(**kwargs):
    row = {
        "fecha": "2026-11-21", "nombre": "7 Ecomaratón La Donaira",
        "localidad": "El Gastor", "provincia": "Cádiz",
        "modalidad": "RUNNING", "distancia": "", "enlace": URL,
        "fuente": URL, "origen": "dorsalchip", "estado": "Por confirmar",
        "desnivel": "", "precio": "", "bolsa": "", "track": "",
        "slug": "ecomaraton-la-donaira", "verificado": ""
    }
    row.update(kwargs)
    return row


class CalidadEditorial(unittest.TestCase):
    def test_misma_ficha_identico_nombre_fecha_pero_modalidad_diferente(self):
        a = race(modalidad="RUNNING")
        b = race(modalidad="TRAIL", estado="Cotejada · confirmar en fuente", verificado="2026-11-15")
        self.assertTrue(same_event(a, b))
        rows, audit = combine([], [a, b], slugify, km_parse, with_audit=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(audit["duplicados_fusionados"], 1)
        self.assertTrue(rows[0]["modalidad_conflicto"])
        self.assertFalse(rows[0]["confirmada"])
        self.assertEqual(rows[0]["verificado"], "")

    def test_distancias_diferentes_no_se_fusionan_sin_confirmar(self):
        rows = combine([], [race(distancia="5 km"),
                            race(distancia="21 km")], slugify, km_parse)
        self.assertEqual(len(rows), 2)

    def test_no_publicar_localidades_con_hora(self):
        city = "a las 16:30 Pabellón Infanta Cristina Roquetas de Mar"
        self.assertFalse(valid_locality(city))
        rows, audit = combine([], [race(localidad=city)], slugify, km_parse, with_audit=True)
        self.assertEqual(rows, [])
        self.assertEqual(audit["descartadas_localidad"], 1)

    def test_aprobacion_editorial_no_se_infiere_de_scraping(self):
        confirmed = race(estado="Confirmado", verificado="2026-11-15")
        pending = race(nombre="Otra carrera", slug="otra-carrera", fecha="2026-11-22")
        results = combine([confirmed], [pending], slugify, km_parse)
        approved = next(r for r in results if r["nombre"] == confirmed["nombre"])
        other = next(r for r in results if r["nombre"] == pending["nombre"])
        self.assertTrue(approved["confirmada"])
        self.assertEqual(approved["verificado"], "2026-11-15")
        self.assertFalse(other["confirmada"])
        self.assertEqual(other["verificado"], "")
        self.assertTrue(other["consultado"])

    def test_captacion_descarta_hora_como_municipio(self):
        page = ('<main><h1>IX MEDIA MARATÓN CIUDAD DE ROQUETAS</h1>'
                '<p>Domingo, 22 de noviembre de 2026</p>'
                '<p>a las 16:30 Pabellón Infanta Cristina Roquetas de Mar (Almería)</p>'
                '</main>')
        self.assertIsNone(parse_cruzando_detail(
            page, "https://www.cruzandolameta.es/pruebas/media-maraton-roquetas/",
            date(2026, 11, 15)))

    def test_ficha_pendiente_sin_datos_ni_schema_de_evento_confirmado(self):
        pending = race(confirmada=False, distancia="12 km", consultado="2026-11-16")
        pending_page = detail_page(pending)
        self.assertIn('noindex,follow', pending_page)
        self.assertNotIn("Procedencia de fecha", pending_page)
        self.assertIn("Consulta anterior de la fuente", pending_page)
        self.assertNotIn("12 km", pending_page)
        self.assertNotIn('"SportsEvent"', pending_page)
        approved = race(confirmada=True, estado="Confirmado", verificado="2026-11-15")
        approved_page = detail_page(approved)
        self.assertNotIn('noindex,follow', approved_page)
        self.assertIn('"SportsEvent"', approved_page)


    def test_fecha_de_fuente_directa_esta_publicada_no_pendiente(self):
        result = combine([], [race()], slugify, km_parse)[0]
        self.assertEqual(result["fecha_origen"], "fuente")
        self.assertFalse(result["confirmada"])
        page = detail_page(result)
        self.assertIn("Fecha", page)
        self.assertIn("Fuente consultada", page)
        self.assertNotIn("Fecha publicada en la fuente consultada", page)
        self.assertNotIn("Pendiente de confirmación", page)

    def test_distancia_cotejada_visible_sin_aprobacion_manual(self):
        r = race(estado="Cotejada · confirmar en fuente", verificado="2026-11-15",
                 distancia="12 km")
        result = combine([], [r], slugify, km_parse)[0]
        self.assertEqual(result["fecha_origen"], "catalogo")
        self.assertEqual(result["distancia_origen"], "catalogo")
        page = detail_page(result)
        self.assertIn("12 km", page)
        self.assertIn("cotejada en el catálogo", page)

    def test_distancia_explicita_en_fuente_directa(self):
        r = race(distancia="10 km")
        result = combine([], [r], slugify, km_parse)[0]
        self.assertEqual(result["distancia_origen"], "fuente")
        self.assertIn("10 km", detail_page(result))

    def test_sitemap_solo_carreras_confirmadas(self):
        pending = race(confirmada=False, slug="pendiente")
        approved = race(confirmada=True, slug="aprobada")
        xml = sitemap([pending, approved])
        self.assertNotIn("/carreras/pendiente/", xml)
        self.assertIn("/carreras/aprobada/", xml)


if __name__ == "__main__":
    unittest.main()
