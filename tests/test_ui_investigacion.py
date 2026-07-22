"""Pruebas de las Etapas 2, 3 y 4 del Motor de Investigación de UBIGUIA
(UI mínima, ventana de revisión, y aprobación/promoción del POI_MASTER).

No instancian el Editor real (EditorUBIGUIA) para no depender de
config.local.json ni de la carpeta TURISMO real: usan un doble mínimo
(EditorFalso) que implementa solo el contrato que apply_investigacion_ui
necesita. Cada POI de prueba se crea en un directorio temporal fuera del
repositorio.

Ejecutar con:  python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constants import POI_JSON, POI_MASTER_FILE  # noqa: E402
import ui_investigacion  # noqa: E402
from motor_investigacion import estados  # noqa: E402
from motor_investigacion.entidades.poi import adaptador as adaptador_poi  # noqa: E402
from motor_investigacion.motor import ejecutar_investigacion, promover_a_master  # noqa: E402
from motor_investigacion.proveedor_simulado import ProveedorInvestigacionSimulado  # noqa: E402


def _crear_poi_de_prueba(base_dir: Path) -> Path:
    poi_dir = base_dir / "01-POI de Prueba UI"
    poi_dir.mkdir(parents=True, exist_ok=True)
    (poi_dir / POI_JSON).write_text(
        json.dumps(
            {
                "poi_id": "poi-ui-001",
                "poi_name": "POI de Prueba UI",
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
    (poi_dir / POI_MASTER_FILE).write_text("# POI MASTER\n\n# POI de Prueba UI\n", encoding="utf-8")
    return poi_dir


def _crear_poi_investigado(base_dir: Path) -> Path:
    """POI de prueba con una investigación ya completada (estado
    EN_REVISION, los 5 archivos de _research/ ya generados), ejecutada
    directamente contra el Motor sin pasar por la UI."""
    poi_dir = _crear_poi_de_prueba(base_dir)
    ejecutar_investigacion(poi_dir, ProveedorInvestigacionSimulado())
    return poi_dir


class EditorFalso(tk.Toplevel):
    """Doble mínimo de EditorUBIGUIA: implementa solo lo que
    apply_investigacion_ui necesita, sin depender de TURISMO real ni de
    config.local.json.

    Es un Toplevel (no un Tk) porque Tkinter no admite crear y destruir
    varias raíces Tk() independientes dentro del mismo proceso; las
    pruebas comparten una única raíz oculta (ver setUpClass)."""

    def __init__(self, master, poi_dir: Path):
        super().__init__(master)
        self.withdraw()
        self._poi_dir = poi_dir
        self.status_var = tk.StringVar(value="")
        self._seleccion: list[str] = []
        self.build_ui()

    def build_ui(self):
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack()

    def update_status(self):
        if not self._seleccion:
            self.status_var.set("Seleccione un POI para ver su estado.")
        else:
            self.status_var.set(f"{self._poi_dir.name}\n\nEstado base de prueba")

    def selected_names(self):
        return self._seleccion

    def selected_path(self):
        return self._poi_dir if self._seleccion else None

    def current_city_path(self):
        return self._poi_dir.parent

    def seleccionar_poi_de_prueba(self):
        self._seleccion = [self._poi_dir.name]

    def deseleccionar(self):
        self._seleccion = []


ui_investigacion.apply_investigacion_ui(EditorFalso)


class PruebasUIInvestigacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Una única raíz Tk compartida por todas las pruebas del módulo;
        # cada prueba usa un Toplevel propio (ver EditorFalso) que se
        # destruye al final sin tocar la raíz.
        cls._raiz = tk.Tk()
        cls._raiz.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls._raiz.destroy()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.poi_dir = _crear_poi_de_prueba(Path(self._tmp.name))
        self.editor = EditorFalso(self._raiz, self.poi_dir)
        self.addCleanup(self.editor.destroy)

    def _esperar_finalizacion(self, timeout=5.0):
        """Espera a que termine todo el ciclo asíncrono: hilo de
        investigación + callback verificar() + update_status() final.

        No alcanza con esperar a que aparezca "Investigación:" en el
        texto de estado: ese texto ya aparece antes de investigar (con
        valor "(sin investigar)"), porque el propio test llama a
        update_status() para habilitar el botón. La señal correcta es
        que el estado pase específicamente a EN_REVISION."""
        inicio = time.monotonic()
        while time.monotonic() - inicio < timeout:
            self.editor.update()
            if estados.EN_REVISION in self.editor.status_var.get():
                return
            time.sleep(0.02)
        raise AssertionError("La investigación no terminó dentro del tiempo esperado.")

    def _ejecutar_y_esperar(self):
        self.editor.seleccionar_poi_de_prueba()
        self.editor.update_status()
        with (
            mock.patch.object(ui_investigacion.messagebox, "showinfo") as mock_showinfo,
            mock.patch.object(ui_investigacion.messagebox, "showerror") as mock_showerror,
        ):
            self.editor.investigar_poi_seleccionado()
            self._esperar_finalizacion()
        return mock_showinfo, mock_showerror

    def test_boton_visible(self):
        self.assertTrue(hasattr(self.editor, "btn_investigar_poi"))
        self.assertIsInstance(self.editor.btn_investigar_poi, ttk.Button)

    def test_boton_deshabilitado_sin_poi_seleccionado(self):
        self.editor.deseleccionar()
        self.editor.update_status()
        self.assertEqual(str(self.editor.btn_investigar_poi["state"]), "disabled")

    def test_boton_habilitado_con_poi_seleccionado(self):
        self.editor.seleccionar_poi_de_prueba()
        self.editor.update_status()
        self.assertEqual(str(self.editor.btn_investigar_poi["state"]), "normal")

    def test_ejecucion_con_proveedor_simulado_crea_los_cinco_archivos(self):
        self._ejecutar_y_esperar()
        carpeta = adaptador_poi.ruta_research(self.poi_dir)
        for nombre in ui_investigacion.ARCHIVOS_RESEARCH:
            self.assertTrue((carpeta / nombre).exists(), f"falta {nombre}")

    def test_ui_sigue_usando_el_proveedor_simulado_sin_cambios_de_codigo(self):
        # La Etapa 5 solo reemplazó la instanciación directa por
        # crear_proveedor(); con USAR_PROVEEDOR_REAL en False (valor por
        # defecto) el comportamiento visible de la UI es exactamente el
        # mismo que en la Etapa 2, sin ningún otro cambio en ui_investigacion.py.
        self._ejecutar_y_esperar()
        datos = estados.leer_estado(adaptador_poi.ruta_research(self.poi_dir))
        self.assertEqual(datos["provider"], "simulado")

    def test_resumen_muestra_estado_anterior_y_actual_sin_error(self):
        mock_showinfo, mock_showerror = self._ejecutar_y_esperar()
        mock_showinfo.assert_called_once()
        mock_showerror.assert_not_called()
        texto = mock_showinfo.call_args[0][1]
        self.assertIn("(sin investigar)", texto)
        self.assertIn(estados.EN_REVISION, texto)
        self.assertIn("Tiempo de ejecución", texto)

    def test_refresco_automatico_de_ui_tras_investigar(self):
        self._ejecutar_y_esperar()
        texto_estado = self.editor.status_var.get()
        self.assertIn("Investigación:", texto_estado)
        self.assertIn(estados.EN_REVISION, texto_estado)

    def test_boton_no_bloqueado_al_terminar(self):
        self._ejecutar_y_esperar()
        self.assertEqual(str(self.editor.btn_investigar_poi["state"]), "normal")

    def test_funciona_sin_internet_ni_credenciales(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self._ejecutar_y_esperar()
        carpeta_research = adaptador_poi.ruta_research(self.poi_dir)
        datos = estados.leer_estado(carpeta_research)
        self.assertEqual(datos["state"], estados.EN_REVISION)
        self.assertEqual(datos["provider"], "simulado")


class PruebasVentanaRevision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._raiz = tk.Tk()
        cls._raiz.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls._raiz.destroy()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.poi_dir = _crear_poi_investigado(Path(self._tmp.name))
        self.editor = EditorFalso(self._raiz, self.poi_dir)
        self.addCleanup(self.editor.destroy)
        self.editor.seleccionar_poi_de_prueba()
        self.editor.update_status()

    def test_boton_deshabilitado_sin_investigacion(self):
        poi_sin_investigar = _crear_poi_de_prueba(Path(self._tmp.name) / "otro")
        editor = EditorFalso(self._raiz, poi_sin_investigar)
        self.addCleanup(editor.destroy)
        editor.seleccionar_poi_de_prueba()
        editor.update_status()
        self.assertEqual(str(editor.btn_revisar_investigacion["state"]), "disabled")

    def test_boton_habilitado_con_investigacion_existente(self):
        self.assertEqual(str(self.editor.btn_revisar_investigacion["state"]), "normal")

    def test_apertura_de_ventana_con_cuatro_pestanas(self):
        self.editor.revisar_investigacion_seleccionada()
        self.addCleanup(self.editor.ventana_revision.destroy)
        ventana = self.editor.ventana_revision
        self.assertEqual(ventana.title(), "Investigación del POI")
        textos_pestanas = [ventana.notebook.tab(pestana, "text") for pestana in ventana.notebook.tabs()]
        self.assertEqual(textos_pestanas, ["Resumen", "Borrador", "Fuentes", "Historial"])

    def test_ventana_no_es_modal(self):
        self.editor.revisar_investigacion_seleccionada()
        self.addCleanup(self.editor.ventana_revision.destroy)
        # Una ventana modal usa grab_set(); si no hay grab activo, "grab current"
        # devuelve "" para esa ventana — la interacción con el resto del Editor
        # sigue siendo posible.
        self.assertEqual(self.editor.ventana_revision.grab_current(), None)

    def test_pestana_resumen_carga_los_datos_correctos(self):
        self.editor.revisar_investigacion_seleccionada()
        self.addCleanup(self.editor.ventana_revision.destroy)
        datos = self.editor.ventana_revision.resumen_datos
        self.assertEqual(datos["state"], estados.EN_REVISION)
        self.assertEqual(datos["provider"], "simulado")
        self.assertEqual(datos["model"], "mock-1")
        self.assertEqual(len(datos["sources"]), 1)
        self.assertEqual(len(datos["contradictions_detected"]), 0)

    def test_pestana_borrador_carga_el_contenido_real(self):
        self.editor.revisar_investigacion_seleccionada()
        self.addCleanup(self.editor.ventana_revision.destroy)
        contenido_ventana = self.editor.ventana_revision.texto_borrador.get("1.0", "end-1c")
        contenido_archivo = adaptador_poi.ruta_borrador_master(self.poi_dir).read_text(encoding="utf-8")
        self.assertEqual(contenido_ventana.strip(), contenido_archivo.strip())
        self.assertEqual(str(self.editor.ventana_revision.texto_borrador["state"]), "disabled")

    def test_pestana_fuentes_carga_el_contenido_real(self):
        self.editor.revisar_investigacion_seleccionada()
        self.addCleanup(self.editor.ventana_revision.destroy)
        contenido_ventana = self.editor.ventana_revision.texto_fuentes.get("1.0", "end-1c")
        contenido_archivo = adaptador_poi.ruta_fuentes(self.poi_dir).read_text(encoding="utf-8")
        self.assertEqual(contenido_ventana.strip(), contenido_archivo.strip())

    def test_pestana_historial_formateada_sin_json_crudo(self):
        self.editor.revisar_investigacion_seleccionada()
        self.addCleanup(self.editor.ventana_revision.destroy)
        tabla = self.editor.ventana_revision.tabla_historial
        filas = tabla.get_children()
        self.assertEqual(len(filas), 2)

        primera = tabla.item(filas[0])["values"]
        segunda = tabla.item(filas[1])["values"]
        self.assertEqual(primera[1], "CREATED")
        self.assertEqual(segunda[1], "STATE_CHANGE")
        self.assertEqual(segunda[2], "agent")
        self.assertIn("BORRADOR", str(segunda[3]))
        self.assertIn(estados.EN_REVISION, str(segunda[3]))
        # Ninguna celda debe contener JSON crudo (llaves de objeto).
        for fila in (primera, segunda):
            for valor in fila:
                self.assertNotIn("{", str(valor))

    def test_comportamiento_cuando_falta_un_archivo(self):
        adaptador_poi.ruta_fuentes(self.poi_dir).unlink()
        self.editor.revisar_investigacion_seleccionada()
        self.addCleanup(self.editor.ventana_revision.destroy)
        contenido = self.editor.ventana_revision.texto_fuentes.get("1.0", "end-1c")
        self.assertIn("No se encontró", contenido)
        # El resto de la ventana se construyó igual, sin excepciones.
        self.assertEqual(
            [self.editor.ventana_revision.notebook.tab(p, "text") for p in self.editor.ventana_revision.notebook.tabs()],
            ["Resumen", "Borrador", "Fuentes", "Historial"],
        )

    def test_funciona_sin_internet_ni_credenciales(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.editor.revisar_investigacion_seleccionada()
        self.addCleanup(self.editor.ventana_revision.destroy)
        self.assertIsNotNone(self.editor.ventana_revision.resumen_datos)
        self.assertEqual(self.editor.ventana_revision.resumen_datos["state"], estados.EN_REVISION)


class PruebasAprobarInvestigacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._raiz = tk.Tk()
        cls._raiz.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls._raiz.destroy()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.poi_dir = _crear_poi_investigado(Path(self._tmp.name))
        self.editor = EditorFalso(self._raiz, self.poi_dir)
        self.addCleanup(self.editor.destroy)
        self.editor.seleccionar_poi_de_prueba()
        self.editor.update_status()

    def test_boton_habilitado_en_en_revision(self):
        self.assertEqual(str(self.editor.btn_aprobar_investigacion["state"]), "normal")

    def test_boton_deshabilitado_en_borrador(self):
        poi_borrador_dir = _crear_poi_de_prueba(Path(self._tmp.name) / "otro-borrador")
        estados.crear_estado_inicial(
            adaptador_poi.ruta_research(poi_borrador_dir), "POI", "poi-borrador", "simulado", "mock-1"
        )
        editor = EditorFalso(self._raiz, poi_borrador_dir)
        self.addCleanup(editor.destroy)
        editor.seleccionar_poi_de_prueba()
        editor.update_status()
        self.assertEqual(str(editor.btn_aprobar_investigacion["state"]), "disabled")

    def test_boton_deshabilitado_en_aprobado(self):
        promover_a_master(self.poi_dir, actor="editor")
        self.editor.update_status()
        self.assertEqual(str(self.editor.btn_aprobar_investigacion["state"]), "disabled")

    def test_si_responde_no_no_hace_ningun_cambio(self):
        carpeta_research = adaptador_poi.ruta_research(self.poi_dir)
        master_antes = adaptador_poi.ruta_master(self.poi_dir).read_text(encoding="utf-8")
        estado_antes = estados.leer_estado(carpeta_research)
        historial_antes = estados.leer_historial(carpeta_research)

        with mock.patch.object(ui_investigacion.messagebox, "askyesno", return_value=False) as mock_ask:
            self.editor.aprobar_investigacion_seleccionada()

        mock_ask.assert_called_once()
        master_despues = adaptador_poi.ruta_master(self.poi_dir).read_text(encoding="utf-8")
        estado_despues = estados.leer_estado(carpeta_research)
        historial_despues = estados.leer_historial(carpeta_research)
        self.assertEqual(master_antes, master_despues)
        self.assertEqual(estado_antes, estado_despues)
        self.assertEqual(historial_antes, historial_despues)

    def test_si_responde_si_promueve_y_muestra_resumen(self):
        with (
            mock.patch.object(ui_investigacion.messagebox, "askyesno", return_value=True),
            mock.patch.object(ui_investigacion.messagebox, "showinfo") as mock_showinfo,
        ):
            self.editor.aprobar_investigacion_seleccionada()

        mock_showinfo.assert_called_once()
        _titulo, texto = mock_showinfo.call_args[0]
        self.assertIn("aprobada correctamente", texto)
        self.assertIn("Backup generado", texto)
        self.assertIn("POI_MASTER actualizado", texto)

        datos = estados.leer_estado(adaptador_poi.ruta_research(self.poi_dir))
        self.assertEqual(datos["state"], estados.APROBADO)

    def test_refresco_automatico_muestra_aprobado(self):
        with (
            mock.patch.object(ui_investigacion.messagebox, "askyesno", return_value=True),
            mock.patch.object(ui_investigacion.messagebox, "showinfo"),
        ):
            self.editor.aprobar_investigacion_seleccionada()
        texto_estado = self.editor.status_var.get()
        self.assertIn("Investigación:", texto_estado)
        self.assertIn(estados.APROBADO, texto_estado)

    def test_funciona_sin_internet_ni_credenciales(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with (
                mock.patch.object(ui_investigacion.messagebox, "askyesno", return_value=True),
                mock.patch.object(ui_investigacion.messagebox, "showinfo"),
            ):
                self.editor.aprobar_investigacion_seleccionada()
        datos = estados.leer_estado(adaptador_poi.ruta_research(self.poi_dir))
        self.assertEqual(datos["state"], estados.APROBADO)


if __name__ == "__main__":
    unittest.main()
