"""Comprobar que la interfaz simplificada no pierde categorías ni enlaces."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.modes = []
        self.selects = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if "data-mode" in attributes:
            self.modes.append(attributes["data-mode"])
        if tag == "select":
            self.selects.append(attributes.get("id"))


class InterfazSimplificada(unittest.TestCase):
    def setUp(self):
        self.page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.script = (ROOT / "assets/app.js").read_text(encoding="utf-8")
        self.parser = Markup()
        self.parser.feed(self.page)

    def test_portada_movil_prioriza_calendario(self):
        css = (ROOT / "assets/styles.css").read_text(encoding="utf-8")
        self.assertIn("Prelanzamiento móvil: primero encontrar carreras", css)
        self.assertIn(".hero-metrics{display:none}", css)
        self.assertIn(".calendar-section{padding-top:35px}", css)
        self.assertIn(".hero-content{padding:32px 0 28px}", css)
        self.assertIn(".hero{min-height:0}", css)

    def test_solo_filtros_utiles(self):
        self.assertEqual(set(self.parser.selects), {"province", "month", "distance"})
        self.assertEqual(self.parser.modes,
                         ["TODAS", "RUNNING", "TRAIL", "CROSS", "OBSTACULOS", "OTRAS"])
        self.assertNotIn("confirmed-only", self.page)
        self.assertNotIn("id=\"source\"", self.page)

    def test_todos_los_controles_de_js_existen(self):
        direct_refs = set(re.findall(r"\$\('([^']+)'\)", self.script))
        self.assertEqual(direct_refs - self.parser.ids, set())
        self.assertNotIn("$('source')", self.script)
        self.assertNotIn("$('confirmed-only')", self.script)

    def test_no_promete_precios_ni_tracks_sin_datos(self):
        self.assertNotIn("Consulta precios, desnivel, track e inscripciones", self.page)
        self.assertNotIn("Accede a la inscripción oficial y al track", self.page)
        self.assertNotIn("50</strong><small>FUENTES", self.page)
        self.assertIn("Comprueba los detalles en su fuente", self.page)

    def test_fecha_visible_sin_etiquetas_tecnicas(self):
        self.assertNotIn("FECHA EN FUENTE", self.script)
        self.assertNotIn("FECHA COTEJADA", self.script)
        self.assertNotIn("dateLabel(", self.script)
        self.assertIn("date.append(", self.script)
        self.assertIn("Fuente consultada: ", self.script)
        self.assertIn("Consulta anterior: ", self.script)
        self.assertIn("sourceName(r)", self.script)
        self.assertIn("const sourceUrl = safeLink(", self.script)

    def test_solo_se_muestra_distancia_si_se_conoce(self):
        self.assertNotIn("Distancia no disponible", self.script)
        self.assertIn("if (r.distancia && r.distancia_origen)", self.script)

    def test_ano_completo_accesible_y_enlace_de_evento_prioritario(self):
        self.assertIn("el('time','race-date')", self.script)
        self.assertIn("date.dateTime = r.fecha", self.script)
        self.assertIn("el('span','race-year'", self.script)
        self.assertIn("d.toLocaleDateString('es-ES'", self.script)
        self.assertIn("safeLink(r.enlace) || safeLink(r.fuente)", self.script)
        self.assertIn('id="shown-count" aria-live="polite"', self.page)
        self.assertNotIn('class="cards" aria-live="polite"', self.page)

    def test_las_categorias_siguen_accesibles(self):
        self.assertIn("r.modalidad === 'TRAIL' || r.modalidad === 'ULTRA'", self.script)
        self.assertIn("r.modalidad === 'OCR' || r.modalidad === 'HIBRIDA'", self.script)
        self.assertIn("r.modalidad === 'RUNNING' || r.modalidad === 'CROSS'", self.script)
        self.assertIn("return 'OTRAS'", self.script)
        self.assertIn("currentMode !== 'TODAS' && modalityGroup(r) !== currentMode",
                      self.script)


if __name__ == "__main__":
    unittest.main()
