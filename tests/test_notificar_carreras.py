"""Pruebas de avisos mediante GitHub Issues sin correo SMTP propio."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from notificar_carreras import (event_record, is_same_event, fingerprint, load_calendar,
                               load_state, make_issue, plan, process)


def race(nombre="Carrera del Valle", fecha="2026-12-20", localidad="Granada",
         provincia="Granada", **extra):
    return {
        "nombre": nombre, "fecha": fecha, "localidad": localidad,
        "provincia": provincia, "enlace": "https://example.org/carrera",
        "distancia": "15 km · 25 km", "slug": "carrera-del-valle", **extra,
    }


class AlertasGitHubCarreras(unittest.TestCase):
    def test_primera_publicacion_no_anuncia_historicos(self):
        new, seen, initial = plan([event_record(race())], None)
        self.assertTrue(initial)
        self.assertEqual(new, [])
        self.assertEqual(len(seen), 1)

    def test_carrera_nueva_se_anuncia_una_sola_vez(self):
        old = [event_record(race())]
        next_race = event_record(race(nombre="Carrera de Navidad",
                                      localidad="Málaga", provincia="Málaga"))
        new, seen, initial = plan([old[0], next_race], old)
        self.assertFalse(initial)
        self.assertEqual(new, [next_race])
        self.assertEqual(len(seen), 2)
        self.assertEqual(plan([old[0], next_race], seen)[0], [])

    def test_cambio_de_distancia_no_es_nueva_carrera(self):
        old = event_record(race(distancia="15 km"))
        updated = event_record(race(distancia="15 km · 25 km", slug="carrera-edicion"))
        self.assertEqual(plan([updated], [old])[0], [])

    def test_nombre_corregido_y_reaparicion_no_producen_avisos(self):
        known = event_record(race(nombre="XX Carrera del Valle"))
        renamed = event_record(race(nombre="XX Carrera del Valle!"))
        self.assertTrue(is_same_event(known, renamed))
        self.assertEqual(plan([renamed], [known])[0], [])
        self.assertEqual(plan([known], [known])[0], [])

    def test_misma_localidad_distinto_nombre_si_es_carrera_nueva(self):
        old = event_record(race(nombre="Cross del Valle"))
        other = event_record(race(nombre="Media Maratón de Sierra Nevada"))
        self.assertFalse(is_same_event(old, other))
        self.assertEqual(plan([other], [old])[0], [other])

    def test_incidencia_incluye_fuente_y_fecha(self):
        title, body, marker = make_issue([event_record(race())])
        self.assertEqual(title, "CorreRadar: 1 carrera nueva en el calendario")
        self.assertIn("Carrera del Valle", body)
        self.assertIn("2026-12-20", body)
        self.assertIn("15 km", body)
        self.assertIn("https://example.org/carrera", body)
        self.assertIn("/carreras/carrera-del-valle/", body)
        self.assertIn(marker, body)

    def test_el_identificador_se_mantiene_en_reintentos(self):
        a = event_record(race())
        b = event_record(race(nombre="Navidad Popular",
                              localidad="Sevilla", provincia="Sevilla"))
        self.assertEqual(fingerprint([a, b]), fingerprint([b, a]))
        self.assertNotEqual(fingerprint([a, b]), fingerprint([a]))

    def test_un_titulo_externo_no_puede_mencionar_usuarios(self):
        _, body, _ = make_issue([event_record(race(nombre="Trail @example [importante]"))])
        self.assertNotIn("@example", body)
        self.assertIn("＠example", body)

    def test_primera_ejecucion_guarda_referencia_sin_incidencia(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            current, prev, next_path, title, body = (base / name for name in (
                "carreras.json", "previous.json", "next.json", "title.txt", "body.md"))
            current.write_text(json.dumps({"carreras": [race()]}), encoding="utf-8")
            result = process(current, prev, next_path, title, body)
            self.assertTrue(result["baseline"])
            self.assertEqual(len(load_state(next_path)), 1)
            self.assertFalse(title.exists())
            self.assertFalse(body.exists())

    def test_preparar_novedades_y_no_repetir_las_anteriores(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            current, prev, next_path, title, body = (base / name for name in (
                "carreras.json", "previous.json", "next.json", "title.txt", "body.md"))
            prev.write_text(json.dumps({"version": 1, "eventos": [event_record(race())]}),
                            encoding="utf-8")
            current.write_text(json.dumps({"carreras": [
                race(), race(nombre="Navidad Popular",
                             localidad="Sevilla", provincia="Sevilla")
            ]}), encoding="utf-8")
            status = process(current, prev, next_path, title, body)
            self.assertEqual(status["new"], 1)
            self.assertTrue(title.is_file())
            self.assertTrue(body.is_file())
            same = process(current, next_path, base / "next2.json",
                           base / "title2.txt", base / "body2.md")
            self.assertEqual(same["new"], 0)
            self.assertFalse((base / "body2.md").exists())

    def test_no_email_ni_smtp_y_solo_despues_de_publicar(self):
        workflow = (ROOT / ".github" / "workflows" / "publicar.yml").read_text(encoding="utf-8")
        script = (ROOT / "scripts" / "notificar_carreras.py").read_text(encoding="utf-8")
        self.assertIn("needs: [build, deploy]", workflow)
        self.assertIn("issues: write", workflow)
        self.assertIn("gh issue create", workflow)
        self.assertIn("gh issue list", workflow)
        self.assertNotIn("SMTP_APP_PASSWORD", workflow)
        self.assertNotIn("smtplib", script)

    def test_datos_incompletos_rechazados(self):
        with self.assertRaises(ValueError):
            event_record({"nombre": "Evento sin fecha"})
        with self.assertRaises(ValueError):
            event_record(race(fecha="2026-13-40"))
        with self.assertRaises(ValueError):
            make_issue([])
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "empty.json"
            file.write_text('{"carreras":[]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "vacío"):
                load_calendar(file)


if __name__ == "__main__":
    unittest.main()
