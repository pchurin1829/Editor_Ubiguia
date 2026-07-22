"""Pruebas de las Etapas 1, 4 y 5 del Motor de Investigación de UBIGUIA
(base del motor, proveedor simulado, aprobación/promoción del
POI_MASTER, y confirmación de que el Motor acepta ProveedorInvestigacionAnthropic
sin modificaciones).

No tocan TURISMO ni ningún POI real: cada prueba crea un POI de prueba
en un directorio temporal fuera del repositorio. Ninguna prueba llama a
la API real de Anthropic.

Ejecutar con:  python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constants import POI_JSON, POI_MASTER_FILE  # noqa: E402
from motor_investigacion import estados  # noqa: E402
from motor_investigacion import motor  # noqa: E402
from motor_investigacion.entidades.poi import adaptador as adaptador_poi  # noqa: E402
from motor_investigacion.proveedor_anthropic import ProveedorInvestigacionAnthropic  # noqa: E402
from motor_investigacion.proveedor_simulado import ProveedorInvestigacionSimulado  # noqa: E402


def _crear_poi_de_prueba(base_dir: Path) -> Path:
    """Crea un POI de prueba mínimo, fuera de TURISMO, para las pruebas."""
    poi_dir = base_dir / "01-POI de Prueba"
    poi_dir.mkdir(parents=True, exist_ok=True)
    (poi_dir / POI_JSON).write_text(
        json.dumps(
            {
                "poi_id": "poi-prueba-001",
                "poi_order": "01",
                "poi_name": "POI de Prueba",
                "category": "Prueba",
                "country": "ARGENTINA",
                "province": "BUENOS AIRES",
                "city": "CIUDAD DE PRUEBA",
            },
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )
    (poi_dir / POI_MASTER_FILE).write_text(
        "# POI MASTER\n\n# POI de Prueba\n\n## 1. Identificación\n\nNombre: POI de Prueba\n",
        encoding="utf-8",
    )
    return poi_dir


class PruebasEstados(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.carpeta_research = Path(self._tmp.name) / "_research"

    def _crear_investigacion_en_revision(self):
        estados.crear_estado_inicial(self.carpeta_research, "POI", "poi-1", "simulado", "mock-1")
        return estados.cambiar_estado(self.carpeta_research, estados.EN_REVISION, actor="agent")

    def test_transicion_inicial_valida(self):
        self.assertTrue(estados.transicion_valida(None, estados.BORRADOR))

    def test_transicion_inicial_invalida(self):
        self.assertFalse(estados.transicion_valida(None, estados.EN_REVISION))

    def test_crear_estado_inicial_y_avanzar_a_en_revision(self):
        datos = self._crear_investigacion_en_revision()
        self.assertEqual(datos["state"], estados.EN_REVISION)

    def test_rechaza_transicion_invalida_borrador_a_aprobado(self):
        estados.crear_estado_inicial(self.carpeta_research, "POI", "poi-1", "simulado", "mock-1")
        with self.assertRaises(estados.TransicionInvalidaError):
            estados.cambiar_estado(self.carpeta_research, estados.APROBADO, actor="editor")

    def test_rechaza_transicion_invalida_desde_exportado(self):
        self._crear_investigacion_en_revision()
        estados.cambiar_estado(self.carpeta_research, estados.APROBADO, actor="editor")
        estados.cambiar_estado(self.carpeta_research, estados.EXPORTADO, actor="agent")
        with self.assertRaises(estados.TransicionInvalidaError):
            estados.cambiar_estado(self.carpeta_research, estados.BORRADOR, actor="agent")

    def test_cambiar_estado_falla_sin_research_json(self):
        with self.assertRaises(ValueError):
            estados.cambiar_estado(self.carpeta_research, estados.EN_REVISION, actor="agent")

    def test_escritura_atomica_no_deja_archivos_temporales(self):
        ruta = self.carpeta_research / "archivo.txt"
        estados.escribir_archivo_atomico(ruta, "contenido de prueba")
        self.assertEqual(ruta.read_text(encoding="utf-8"), "contenido de prueba")
        temporales = list(ruta.parent.glob(f".{ruta.name}.*"))
        self.assertEqual(temporales, [])

    def test_historial_es_append_only(self):
        self._crear_investigacion_en_revision()
        historial = estados.leer_historial(self.carpeta_research)
        self.assertEqual(len(historial), 2)
        self.assertEqual(historial[0]["event"], "CREATED")
        self.assertEqual(historial[1]["event"], "STATE_CHANGE")
        self.assertEqual(historial[1]["from"], estados.BORRADOR)
        self.assertEqual(historial[1]["to"], estados.EN_REVISION)


class PruebasMotorConProveedorSimulado(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.poi_dir = _crear_poi_de_prueba(Path(self._tmp.name))
        self.master_original = (self.poi_dir / POI_MASTER_FILE).read_text(encoding="utf-8")
        self.proveedor = ProveedorInvestigacionSimulado()

    def test_ejecutar_investigacion_crea_los_cinco_archivos(self):
        motor.ejecutar_investigacion(self.poi_dir, self.proveedor)
        carpeta = adaptador_poi.ruta_research(self.poi_dir)
        self.assertTrue((carpeta / "research.json").exists())
        self.assertTrue((carpeta / "POI_MASTER_BORRADOR.md").exists())
        self.assertTrue((carpeta / "fuentes.md").exists())
        self.assertTrue((carpeta / "observaciones.md").exists())
        self.assertTrue((carpeta / "historial.json").exists())

    def test_ejecutar_investigacion_deja_estado_en_revision_con_fuentes(self):
        datos = motor.ejecutar_investigacion(self.poi_dir, self.proveedor)
        self.assertEqual(datos["state"], estados.EN_REVISION)
        self.assertEqual(datos["entity_type"], "POI")
        self.assertEqual(datos["provider"], "simulado")
        self.assertGreaterEqual(len(datos["sources"]), 1)

    def test_no_modifica_poi_master(self):
        motor.ejecutar_investigacion(self.poi_dir, self.proveedor)
        master_actual = (self.poi_dir / POI_MASTER_FILE).read_text(encoding="utf-8")
        self.assertEqual(master_actual, self.master_original)

    def test_no_permite_reejecutar_sobre_investigacion_existente(self):
        motor.ejecutar_investigacion(self.poi_dir, self.proveedor)
        with self.assertRaises(ValueError):
            motor.ejecutar_investigacion(self.poi_dir, self.proveedor)

    def test_funciona_sin_red_ni_credenciales(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            datos = motor.ejecutar_investigacion(self.poi_dir, self.proveedor)
        self.assertEqual(datos["state"], estados.EN_REVISION)


class PruebasPromoverAMaster(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.poi_dir = _crear_poi_de_prueba(Path(self._tmp.name))
        self.master_original = (self.poi_dir / POI_MASTER_FILE).read_text(encoding="utf-8")
        self.carpeta_research = adaptador_poi.ruta_research(self.poi_dir)

    def _investigar(self):
        return motor.ejecutar_investigacion(self.poi_dir, ProveedorInvestigacionSimulado())

    def test_no_permite_aprobar_sin_research_json(self):
        with self.assertRaises(ValueError):
            motor.promover_a_master(self.poi_dir)

    def test_no_permite_aprobar_en_borrador(self):
        estados.crear_estado_inicial(self.carpeta_research, "POI", "poi-1", "simulado", "mock-1")
        # Se escribe un borrador de prueba para aislar específicamente la
        # validación del estado (sin este archivo, fallaría antes por otro motivo).
        adaptador_poi.ruta_borrador_master(self.poi_dir).write_text("borrador de prueba", encoding="utf-8")
        with self.assertRaises(estados.TransicionInvalidaError):
            motor.promover_a_master(self.poi_dir)

    def test_no_permite_aprobar_sin_borrador_master(self):
        # research.json llega a EN_REVISION sin pasar por escribir_borrador(),
        # para poder probar la validación de POI_MASTER_BORRADOR.md por separado.
        estados.crear_estado_inicial(self.carpeta_research, "POI", "poi-1", "simulado", "mock-1")
        estados.cambiar_estado(self.carpeta_research, estados.EN_REVISION, actor="agent")
        with self.assertRaises(ValueError):
            motor.promover_a_master(self.poi_dir)

    def test_no_permite_aprobar_ya_aprobado(self):
        self._investigar()
        motor.promover_a_master(self.poi_dir, actor="editor")
        with self.assertRaises(estados.TransicionInvalidaError):
            motor.promover_a_master(self.poi_dir, actor="editor")

    def test_crea_backup_con_el_contenido_anterior(self):
        self._investigar()
        _datos, nombre_backup = motor.promover_a_master(self.poi_dir, actor="editor")
        ruta_backup = self.poi_dir / nombre_backup
        self.assertTrue(ruta_backup.exists())
        self.assertEqual(ruta_backup.read_text(encoding="utf-8"), self.master_original)
        self.assertRegex(nombre_backup, r"^POI_MASTER\.md\.bak-\d{8}-\d{6}$")

    def test_reemplaza_master_con_el_contenido_del_borrador(self):
        self._investigar()
        contenido_borrador = adaptador_poi.ruta_borrador_master(self.poi_dir).read_text(encoding="utf-8")
        motor.promover_a_master(self.poi_dir, actor="editor")
        contenido_master = adaptador_poi.ruta_master(self.poi_dir).read_text(encoding="utf-8")
        self.assertEqual(contenido_master, contenido_borrador)
        self.assertNotEqual(contenido_master, self.master_original)

    def test_actualiza_research_json(self):
        self._investigar()
        datos, _nombre_backup = motor.promover_a_master(self.poi_dir, actor="editor")
        self.assertEqual(datos["state"], estados.APROBADO)
        self.assertIsNotNone(datos["approved_at"])
        self.assertIsNotNone(datos["updated_at"])

        datos_en_disco = estados.leer_estado(self.carpeta_research)
        self.assertEqual(datos_en_disco["state"], estados.APROBADO)
        self.assertEqual(datos_en_disco["approved_at"], datos["approved_at"])

    def test_actualiza_historial(self):
        self._investigar()
        _datos, nombre_backup = motor.promover_a_master(self.poi_dir, actor="editor")
        historial = estados.leer_historial(self.carpeta_research)
        eventos = [evento["event"] for evento in historial]
        self.assertIn("APPROVED", eventos)
        self.assertIn("PROMOTED", eventos)

        evento_approved = next(e for e in historial if e["event"] == "APPROVED")
        self.assertEqual(evento_approved["actor"], "editor")

        evento_promoted = next(e for e in historial if e["event"] == "PROMOTED")
        self.assertEqual(evento_promoted["actor"], "editor")
        self.assertEqual(evento_promoted["master_backup"], nombre_backup)

    def test_operacion_atomica_sin_archivos_temporales(self):
        self._investigar()
        motor.promover_a_master(self.poi_dir, actor="editor")
        temporales_master = list(self.poi_dir.glob(f".{POI_MASTER_FILE}.*"))
        temporales_research = list(self.carpeta_research.glob(".research.json.*"))
        self.assertEqual(temporales_master, [])
        self.assertEqual(temporales_research, [])

    def test_recuperacion_ante_error_restaura_poi_master(self):
        self._investigar()
        with mock.patch.object(estados, "escribir_estado_atomico", side_effect=RuntimeError("fallo simulado")):
            with self.assertRaises(RuntimeError):
                motor.promover_a_master(self.poi_dir, actor="editor")

        # POI_MASTER.md quedó restaurado a su contenido previo a la promoción,
        # no vacío ni con el borrador a medio aplicar.
        contenido_master = adaptador_poi.ruta_master(self.poi_dir).read_text(encoding="utf-8")
        self.assertEqual(contenido_master, self.master_original)

        # research.json nunca llegó a escribirse como APROBADO.
        datos = estados.leer_estado(self.carpeta_research)
        self.assertEqual(datos["state"], estados.EN_REVISION)

        # El backup generado antes del fallo se conserva, y el error queda registrado.
        backups = list(self.poi_dir.glob(f"{POI_MASTER_FILE}.bak-*"))
        self.assertEqual(len(backups), 1)
        historial = estados.leer_historial(self.carpeta_research)
        self.assertTrue(any(evento["event"] == "ERROR" for evento in historial))

    def test_funciona_sin_red_ni_credenciales(self):
        self._investigar()
        with mock.patch.dict(os.environ, {}, clear=True):
            datos, nombre_backup = motor.promover_a_master(self.poi_dir, actor="editor")
        self.assertEqual(datos["state"], estados.APROBADO)
        self.assertTrue((self.poi_dir / nombre_backup).exists())


class PruebasMotorAceptaProveedorAnthropicSinCambios(unittest.TestCase):
    """El Motor (motor.py) no se modificó en la Etapa 5: estas pruebas
    corren ejecutar_investigacion() con ProveedorInvestigacionAnthropic
    (con su llamada HTTP mockeada) para demostrar que el Motor solo
    depende del contrato ProveedorInvestigacion, nunca de una
    implementación concreta."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.poi_dir = _crear_poi_de_prueba(Path(self._tmp.name))
        self._entorno_previo = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._entorno_previo)))
        os.environ["ANTHROPIC_API_KEY"] = "clave-de-prueba"

    def test_ejecutar_investigacion_funciona_con_proveedor_anthropic_mockeado(self):
        respuesta_falsa = SimpleNamespace(content=[SimpleNamespace(type="text", text="Respuesta de prueba.")])
        with mock.patch("motor_investigacion.proveedor_anthropic.anthropic.Anthropic") as ClienteFalso:
            ClienteFalso.return_value.messages.create.return_value = respuesta_falsa
            datos = motor.ejecutar_investigacion(self.poi_dir, ProveedorInvestigacionAnthropic())

        self.assertEqual(datos["state"], estados.EN_REVISION)
        self.assertEqual(datos["provider"], "anthropic")
        self.assertEqual(len(datos["sources"]), 1)

        carpeta = adaptador_poi.ruta_research(self.poi_dir)
        self.assertTrue((carpeta / "research.json").exists())
        self.assertTrue((carpeta / "POI_MASTER_BORRADOR.md").exists())
        self.assertTrue((carpeta / "fuentes.md").exists())


if __name__ == "__main__":
    unittest.main()
