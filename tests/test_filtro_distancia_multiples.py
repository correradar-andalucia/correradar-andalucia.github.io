"""Regresiones reales de JS: cada distancia declarada debe estar en su rango."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FiltrosDistanciasMultiples(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node necesario para probar el filtro real")
    def test_todas_las_distancias_y_unidades(self):
        source = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        start = source.index("const distanceNumbers =")
        end = source.index("let races = []", start)
        logic = source[start:end]
        cases = [
            ["25 km · 15 km", ["medium", "long"], ["short", "ultra"]],
            ["25 k y 15 k", ["medium", "long"], ["short", "ultra"]],
            ["25 kms / 15 kilómetros", ["medium", "long"], ["short"]],
            ["15 km", ["medium"], ["long", "ultra"]],
            ["1.500 m / 25 km", ["short", "long"], ["medium"]],
            ["5 km · 10 km · 25 km", ["short", "long"], ["medium", "ultra"]],
            ["50 km / 15 km", ["medium", "ultra"], ["long"]],
            ["sin distancias", ["unknown"], ["short", "medium", "long", "ultra"]],
        ]
        payload = json.dumps(cases, ensure_ascii=False)
        js = logic + f"""
const cases = {payload};
for (const [distance, yes, no] of cases) {{
 const item = {{distancia: distance}};
 for (const group of yes) if (!distanceMatches(item, group))
   throw new Error(distance + ': no se muestra en ' + group);
 for (const group of no) if (distanceMatches(item, group))
   throw new Error(distance + ': aparece indebidamente en ' + group);
}}
console.log('Filtros de varias distancias OK (' + cases.length + ' casos)');
"""
        result = subprocess.run(
            ["node", "-e", js], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
