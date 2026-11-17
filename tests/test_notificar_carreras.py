"""Comprobar notificaciones sin envío real de correo."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from notificar_carreras import (event_record, is_same_event, load_calendar,
                              load_state, make_message, plan, process)


def race(nombre="Carrera del Valle", fecha="2026-12-20", localidad="Granada",
         provincia="Granada", **extra):
    return {
        "nombre": nombre, "fecha": fecha, "localidad": localidad,
        "provincia": provincia, "enlace": "https://example.org/carrera",
        "distancia": "15 km · 25 km", "slug": "carrera-del-valle", **extra,
    }


class AlertasCorreoCarreras(unittest.TestCase):
    def test_primera_publicacion_no_envia_historicos(self):
        new, seen, initial = plan([event_record(race())], None)
        self.assertTrue(initial)
        self.assertEqual(new, [])
        self.assertEqual(len(seen), 1)

    def test_carrera_nueva_generara_un_solo_aviso(self):
        old = [event_record(race())]
        next_race = event_record(race(nombre="Carrera de Navidad",
                                      localidad="Málaga", provincia="Málaga"))
        new, seen, initial = plan([old[0], next_race], old)
        self.assertFalse(initial)
        self.assertEqual(new, [next_race])
        self.assertEqual(len(seen), 2)
        new_again, _, _ = plan([old[0], next_race], seen)
        self.assertEqual(new_again, [])

    def test_cambio_de_distancia_no_es_nueva_carrera(self):
        old = event_record(race(distancia="15 km"))
        updated = event_record(race(distancia="15 km · 25 km", slug="carrera-edicion"))
        new, _, _ = plan([updated], [old])
        self.assertEqual(new, [])

    def test_nombre_corregido_y_reaparicion_no_producen_avisos(self):
        known = event_record(race(nombre="XX Carrera del Valle",
                                   fecha="2026-12-20"))
        renamed = event_record(race(nombre="XX Carrera del Valle!",
                                     fecha="2026-12-20"))
        self.assertTrue(is_same_event(known, renamed))
        self.assertEqual(plan([renamed], [known])[0], [])
        self.assertEqual(plan([known], [known])[0], [])

    def test_misma_localidad_distinto_nombre_es_carrera_nueva(self):
        old = event_record(race(nombre="Cross del Valle"))
        other = event_record(race(nombre="Media Maratón de Sierra Nevada"))
        self.assertFalse(is_same_event(old, other))
        self.assertEqual(plan([other], [old])[0], [other])

    def test_email_contiene_nombre_fecha_y_enlace(self):
        msg = make_message([event_record(race())],
                           "destino@example.org", "remitente@example.org")
        self.assertIn("1 carrera nueva", str(msg["Subject"]))
        content = msg.get_content()
        self.assertIn("Carrera del Valle", content)
        self.assertIn("2026-12-20", content)
        self.assertIn("15 km · 25 km", content)
        self.assertIn("https://example.org/carrera", content)
        self.assertIn("/carreras/carrera-del-valle/", content)

    def test_fallo_smtp_no_avanza_estado(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            current = base / "carreras.json"
            previous = base / "previous.json"
            next_path = base / "next.json"
            previous.write_text(json.dumps({"version": 1, "eventos": [
                event_record(race())
            ]}), encoding="utf-8")
            current.write_text(json.dumps({"carreras": [race(), race(
                nombre="Carrera de Navidad", localidad="Málaga", provincia="Málaga"
            )]}), encoding="utf-8")
            with patch("notificar_carreras.send_email", side_effect=OSError("SMTP unavailable")):
                with self.assertRaisesRegex(OSError, "SMTP unavailable"):
                    process(current, previous, next_path,
                            sender="origen@example.org", password="dummy",
                            recipient="destino@example.org")
            self.assertFalse(next_path.exists())
            # También conservar pendientes si faltan credenciales.
            status = process(current, previous, next_path,
                             sender="", password="", recipient="destino@example.org")
            self.assertFalse(status["committed"])
            self.assertEqual(status["new"], 1)
            self.assertFalse(next_path.exists())

    def test_primera_ejecucion_crea_estado_sin_correo(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            current, prev, next_path = (base / name for name in
                                        ("carreras.json", "previous.json", "next.json"))
            current.write_text(json.dumps({"carreras": [race()]}), encoding="utf-8")
            with patch("notificar_carreras.send_email") as send:
                status = process(current, prev, next_path,
                                 sender="", password="", recipient="")
            send.assert_not_called()
            self.assertTrue(status["baseline"])
            self.assertEqual(len(load_state(next_path)), 1)

    def test_envio_valido_avanza_y_el_siguiente_no_repite(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            current, prev, next_path = (base / name for name in
                                        ("carreras.json", "previous.json", "next.json"))
            previous = {"version": 1, "eventos": [event_record(race())]}
            prev.write_text(json.dumps(previous), encoding="utf-8")
            current.write_text(json.dumps({"carreras": [race(), race(
                nombre="Navidad Popular", localidad="Sevilla", provincia="Sevilla"
            )]}), encoding="utf-8")
            with patch("notificar_carreras.send_email") as send:
                status = process(current, prev, next_path,
                                 sender="origen@example.org", password="dummy",
                                 recipient="destino@example.org")
            self.assertTrue(status["committed"])
            self.assertEqual(status["new"], 1)
            send.assert_called_once()
            with patch("notificar_carreras.send_email") as send2:
                same = process(current, next_path, base / "next2.json",
                               sender="origen@example.org", password="dummy",
                               recipient="destino@example.org")
            self.assertEqual(same["new"], 0)
            send2.assert_not_called()

    def test_datos_incompletos_rechazados(self):
        with self.assertRaises(ValueError):
            event_record({"nombre": "Evento sin fecha"})
        with self.assertRaises(ValueError):
            event_record(race(fecha="2026-13-40"))
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "empty.json"
            file.write_text('{"carreras":[]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "vacío"):
                load_calendar(file)


if __name__ == "__main__":
    unittest.main()
