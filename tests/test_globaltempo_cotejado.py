"""Global Tempo: solo fichas de inscripciones cotejadas; no importar calendario masivo."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from oficiales import official_races
from multifuente import seed_races
from deduplicacion import combine, verify_unique, same_event
from build import slugify, km_parse


class GlobalTempoControlado(unittest.TestCase):
    def test_11_fichas_primarias_con_fecha_y_enlace_profundo(self):
        items=official_races(date(2026,11,17))
        gt=[r for r in items if r["fuente_nombre"].startswith("Global Tempo")]
        self.assertEqual(len(gt),11)
        self.assertTrue(all(r["fuente"].startswith("https://www.global-tempo.com/carreras.php?id=")
                            for r in gt))
        self.assertTrue(all(r["tipo_fuente"]=="cronometraje" for r in gt))
        self.assertTrue(all(r["cotejada"]=="2026-11-17" for r in gt))
        names={r["nombre"] for r in gt}
        self.assertIn("VII Carrera San Silvestre Alhendín 2026",names)
        self.assertIn("XIII Subida a la Cruz de la Atalaya",names)
        self.assertIn("Carrera Solidaria de Navidad Villa de Otura",names)
        self.assertNotIn("Playa Cambriles Race",names)
        self.assertNotIn("Pasacalles Andarines Alhendín",names)

    def test_salida_de_trail_no_es_senderismo(self):
        items=official_races(date(2026,11,17))
        race=next(r for r in items if r["nombre"]=="CxM Albuñuelas")
        self.assertEqual(race["hora"],"10:30")
        self.assertEqual(race["distancia"],"20 km · 13,5 km")

    def test_padul_cotejado_en_reglamento(self):
        items=official_races(date(2026,11,17))
        race=next(r for r in items if r["nombre"]=="XIII Subida a la Cruz de la Atalaya")
        self.assertEqual(race["fecha"],"2027-01-31")
        self.assertEqual(race["distancia"],"8,72 km")
        self.assertEqual(race["hora"],"10:00")

    def test_otura_2026_fecha_hora_y_distancia_aproximada(self):
        gt=[r for r in official_races(date(2026,11,17))
            if r["nombre"]=="Carrera Solidaria de Navidad Villa de Otura"]
        self.assertEqual(len(gt),1)
        race=gt[0]
        self.assertEqual(race["fecha"],"2026-12-22")
        self.assertEqual(race["localidad"],"Otura")
        self.assertEqual(race["provincia"],"Granada")
        self.assertEqual(race["hora"],"18:00")
        self.assertIn("según categoría",race["distancia"])
        self.assertIn("aprox.",race["distancia"])
        self.assertEqual(race["enlace"],
                         "https://www.global-tempo.com/carreras.php?id=3327")
        self.assertFalse(race.get("confirmada",False))

    def test_una_portada_no_cuenta_como_confirmacion(self):
        sample=next(r for r in official_races(date(2026,11,17))
                    if r["nombre"]=="VII Carrera San Silvestre Alhendín 2026")
        fields=("fecha","nombre","localidad","provincia","modalidad","distancia",
                "hora","fuente","fuente_nombre","tipo_fuente")
        record={k:sample[k] for k in fields}
        record["fuente"]="https://www.global-tempo.com/index.php"
        with self.assertRaisesRegex(ValueError,"edición concreta"):
            official_races(date(2026,11,17),{"revision":"2026-11-17","carreras":[record]})

    def test_fecha_consultada_no_simula_actualidad_perpetua(self):
        gt=[r for r in official_races(date(2027,1,1))
            if r["fuente_nombre"].startswith("Global Tempo")]
        self.assertGreater(len(gt),0)
        self.assertTrue(all(not r["fuente_directa"] for r in gt))
        self.assertTrue(all("reconfirmar" in r["estado"].lower() for r in gt))

    def test_evitar_doble_albunol_por_localidad_compuesta(self):
        a={"fecha":"2026-11-22","nombre":"VI CxM Albuñol Trail La Contraviesa",
           "localidad":"Albuñol","provincia":"Granada","modalidad":"TRAIL",
           "distancia":"25 km · 12 km",
           "enlace":"https://www.global-tempo.com/carreras.php?id=3204"}
        b={"fecha":"2026-11-22","nombre":"VI CxM Albuñol Trail de la Contraviesa",
           "localidad":"Albuñol y Sorvilán","provincia":"Granada","modalidad":"TRAIL",
           "distancia":"","enlace":"https://fadmes.es/calendario-fam/"}
        self.assertTrue(same_event(a,b))
        unrelated=dict(b,nombre="Otra carrera de la provincia",modalidad="RUNNING")
        self.assertFalse(same_event(a,unrelated))

    def test_semilla_y_cotejo_conservan_solo_un_evento(self):
        gt=[r for r in official_races(date(2026,11,17))
            if r["fuente_nombre"].startswith("Global Tempo")]
        old=[r for r in seed_races(date(2026,11,17)) if r["origen"]=="globaltempo"]
        races=combine([],gt+old,slugify,km_parse)
        self.assertTrue(verify_unique(races))
        # Tres ediciones no estaban presentes en la semilla inicial.
        self.assertEqual(len(races),11)
        neptune=next(r for r in races if r["nombre"].startswith("Neptune Race"))
        self.assertEqual(neptune["distancia"],"6 km")
        self.assertEqual(neptune["hora"],"10:00")
        self.assertEqual(neptune["enlace"],
                         "https://www.global-tempo.com/carreras.php?id=3100")
        self.assertFalse(neptune["confirmada"])


if __name__=="__main__":
    unittest.main()
