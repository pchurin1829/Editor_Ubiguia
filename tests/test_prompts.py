"""Pruebas de la Etapa 6 del Motor de Investigación de UBIGUIA:
carga de prompts versionados desde Docs/prompts/.

Se prueba contra los archivos reales de Docs/prompts/ (son parte de la
entrega de esta etapa, no datos de prueba) y contra un nombre de
archivo inexistente. No requieren red ni credenciales: cargar_prompt()
solo lee archivos de texto.

Ejecutar con:  python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from motor_investigacion.prompts import PromptNoEncontradoError, cargar_prompt, listar_prompts  # noqa: E402

ARCHIVOS_PROMPTS_ESPERADOS = (
    "PROMPT_INVESTIGACION_v1.md",
    "PROMPT_TRADUCCION_ES_EN_v1.md",
    "PROMPT_TRADUCCION_ES_PT_v1.md",
    "PROMPT_AUDIO_v1.md",
)


class PruebasCargarPrompt(unittest.TestCase):
    def test_carga_correcta_del_prompt_de_investigacion(self):
        contenido = cargar_prompt("PROMPT_INVESTIGACION_v1.md")
        self.assertIsInstance(contenido, str)
        self.assertGreater(len(contenido), 0)
        self.assertIn("Objetivo", contenido)
        self.assertIn("Alcance", contenido)
        self.assertIn("Formato esperado", contenido)
        # Marcador indicando que será desarrollado posteriormente.
        self.assertIn("todavía no está desarrollado", contenido)

    def test_carga_correcta_de_los_prompts_reservados(self):
        for nombre in ("PROMPT_TRADUCCION_ES_EN_v1.md", "PROMPT_TRADUCCION_ES_PT_v1.md", "PROMPT_AUDIO_v1.md"):
            contenido = cargar_prompt(nombre)
            self.assertIn("Reservado para futuras etapas.", contenido)

    def test_archivo_inexistente_lanza_error_claro(self):
        with self.assertRaises(PromptNoEncontradoError):
            cargar_prompt("PROMPT_QUE_NO_EXISTE_v99.md")

    def test_archivo_inexistente_no_devuelve_texto_de_respaldo(self):
        # cargar_prompt() debe fallar, nunca inventar contenido ni
        # devolver un prompt interno alternativo.
        try:
            cargar_prompt("PROMPT_QUE_NO_EXISTE_v99.md")
            self.fail("Se esperaba PromptNoEncontradoError")
        except PromptNoEncontradoError as exc:
            self.assertIn("PROMPT_QUE_NO_EXISTE_v99.md", str(exc))

    def test_lectura_utf8_correcta(self):
        # El archivo real usa acentos y "ñ"; si se leyera con otra
        # codificación, estos caracteres llegarían corruptos.
        contenido = cargar_prompt("PROMPT_INVESTIGACION_v1.md")
        self.assertIn("Investigación", contenido)
        self.assertIn("versión", contenido.lower())

    def test_listar_prompts_incluye_los_cuatro_archivos_de_la_etapa(self):
        disponibles = listar_prompts()
        for nombre in ARCHIVOS_PROMPTS_ESPERADOS:
            self.assertIn(nombre, disponibles)

    def test_listar_prompts_devuelve_solo_nombres_de_archivo(self):
        for nombre in listar_prompts():
            self.assertNotIn("/", nombre)
            self.assertNotIn("\\", nombre)


if __name__ == "__main__":
    unittest.main()
