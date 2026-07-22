"""Extensión de UI del Motor de Investigación de UBIGUIA.

Sigue exactamente el mismo patrón de extensión ya usado por
ui_chatgpt.py y status_patch.py: envuelve métodos de EditorUBIGUIA sin
modificar ui_main.py.

Etapa 5: el proveedor a usar lo decide crear_proveedor() (ver
motor_investigacion/proveedor_activo.py) — esta UI ya no instancia
ProveedorInvestigacionSimulado directamente. Sigue sin incluir
observaciones, edición del borrador, descubrimiento, exportación ni un
selector gráfico de proveedor.
"""
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from motor_investigacion import estados
from motor_investigacion.entidades.poi import adaptador as adaptador_poi
from motor_investigacion.motor import ejecutar_investigacion, promover_a_master
from motor_investigacion.proveedor_activo import crear_proveedor

ARCHIVOS_RESEARCH = (
    "research.json",
    "POI_MASTER_BORRADOR.md",
    "fuentes.md",
    "observaciones.md",
    "historial.json",
)


def apply_investigacion_ui(EditorClass):
    if getattr(EditorClass, "_investigacion_ui_applied", False):
        return

    original_build_ui = EditorClass.build_ui
    original_update_status = EditorClass.update_status

    def build_ui(self):
        original_build_ui(self)
        main = self.winfo_children()[0]
        box = ttk.LabelFrame(main, text="Motor de Investigación")
        box.pack(fill="x", pady=(8, 0))
        self.btn_investigar_poi = ttk.Button(
            box,
            text="Investigar POI",
            command=lambda: self.investigar_poi_seleccionado(),
            state="disabled",
        )
        self.btn_investigar_poi.pack(side="left", padx=5, pady=5)
        self.btn_revisar_investigacion = ttk.Button(
            box,
            text="Revisar investigación",
            command=lambda: self.revisar_investigacion_seleccionada(),
            state="disabled",
        )
        self.btn_revisar_investigacion.pack(side="left", padx=5, pady=5)
        self.btn_aprobar_investigacion = ttk.Button(
            box,
            text="Aprobar investigación",
            command=lambda: self.aprobar_investigacion_seleccionada(),
            state="disabled",
        )
        self.btn_aprobar_investigacion.pack(side="left", padx=5, pady=5)

    def update_status(self):
        original_update_status(self)
        nombres = self.selected_names()
        if not nombres:
            self.btn_investigar_poi.config(state="disabled")
            self.btn_revisar_investigacion.config(state="disabled")
            self.btn_aprobar_investigacion.config(state="disabled")
            return
        self.btn_investigar_poi.config(state="normal")
        poi_dir = self.current_city_path() / nombres[0]
        carpeta_research = adaptador_poi.ruta_research(poi_dir)
        datos = estados.leer_estado(carpeta_research)
        estado_texto = datos["state"] if datos else "(sin investigar)"
        self.status_var.set(self.status_var.get() + f"\n\nInvestigación:\n{estado_texto}")

        tiene_investigacion = (carpeta_research / estados.NOMBRE_ARCHIVO_ESTADO).exists()
        self.btn_revisar_investigacion.config(state="normal" if tiene_investigacion else "disabled")

        puede_aprobar = datos is not None and datos.get("state") == estados.EN_REVISION
        self.btn_aprobar_investigacion.config(state="normal" if puede_aprobar else "disabled")

    def investigar_poi_seleccionado(self):
        poi_dir = self.selected_path()
        if not poi_dir:
            return

        carpeta_research = adaptador_poi.ruta_research(poi_dir)
        estado_previo = estados.leer_estado(carpeta_research)
        estado_previo_texto = estado_previo["state"] if estado_previo else "(sin investigar)"

        if estado_previo is not None:
            messagebox.showerror(
                "Investigación ya existente",
                f"'{poi_dir.name}' ya tiene una investigación en estado {estado_previo_texto}.\n\n"
                "Esta etapa del Motor de Investigación solo admite la primera investigación de un POI.",
            )
            return

        self.btn_investigar_poi.config(state="disabled")
        ventana_progreso = _abrir_ventana_progreso(self)

        resultado = {}

        def trabajar():
            inicio = time.monotonic()
            try:
                resultado["datos"] = ejecutar_investigacion(poi_dir, crear_proveedor())
            except Exception as exc:  # noqa: BLE001 — se reporta al editor, no se silencia
                resultado["error"] = exc
            resultado["duracion"] = time.monotonic() - inicio

        hilo = threading.Thread(target=trabajar, daemon=True)
        hilo.start()

        def verificar():
            if hilo.is_alive():
                self.after(150, verificar)
                return

            ventana_progreso.destroy()
            self.btn_investigar_poi.config(state="normal")

            if "error" in resultado:
                messagebox.showerror("Error en la investigación", str(resultado["error"]))
                self.update_status()
                return

            datos = resultado["datos"]
            archivos_texto = "\n".join(f"- {nombre}" for nombre in ARCHIVOS_RESEARCH)
            messagebox.showinfo(
                "Investigación completa",
                f"Estado anterior: {estado_previo_texto}\n"
                f"Estado actual: {datos['state']}\n\n"
                f"Archivos creados:\n{archivos_texto}\n\n"
                f"Tiempo de ejecución: {resultado['duracion']:.1f} s",
            )
            self.update_status()

        self.after(150, verificar)

    def revisar_investigacion_seleccionada(self):
        poi_dir = self.selected_path()
        if not poi_dir:
            return

        carpeta_research = adaptador_poi.ruta_research(poi_dir)
        if not (carpeta_research / estados.NOMBRE_ARCHIVO_ESTADO).exists():
            messagebox.showwarning(
                "Sin investigación",
                f"'{poi_dir.name}' todavía no tiene ninguna investigación para revisar.",
            )
            return

        self.ventana_revision = _abrir_ventana_revision(self, poi_dir)

    def aprobar_investigacion_seleccionada(self):
        poi_dir = self.selected_path()
        if not poi_dir:
            return

        carpeta_research = adaptador_poi.ruta_research(poi_dir)
        datos = estados.leer_estado(carpeta_research)

        if datos is None:
            messagebox.showerror("Sin investigación", f"'{poi_dir.name}' no tiene research.json.")
            return
        if not adaptador_poi.ruta_borrador_master(poi_dir).exists():
            messagebox.showerror("Falta el borrador", f"'{poi_dir.name}' no tiene POI_MASTER_BORRADOR.md.")
            return
        if datos.get("state") != estados.EN_REVISION:
            messagebox.showerror(
                "Estado incorrecto",
                f"'{poi_dir.name}' está en estado {datos.get('state')}; solo se puede aprobar desde "
                f"{estados.EN_REVISION}.",
            )
            return

        continuar = messagebox.askyesno(
            "Confirmar aprobación",
            "Se reemplazará el contenido actual de POI_MASTER.md por el borrador aprobado.\n\n"
            "La versión anterior quedará respaldada.\n\n"
            "¿Desea continuar?",
        )
        if not continuar:
            return

        try:
            _datos_actualizados, nombre_backup = promover_a_master(poi_dir, actor="editor")
        except Exception as exc:  # noqa: BLE001 — se informa al editor, no se silencia
            messagebox.showerror("Error al aprobar", str(exc))
            self.update_status()
            return

        messagebox.showinfo(
            "Aprobación completa",
            "Investigación aprobada correctamente.\n\n"
            f"Backup generado:\n{nombre_backup}\n\n"
            "POI_MASTER actualizado.",
        )
        self.update_status()

    EditorClass.build_ui = build_ui
    EditorClass.update_status = update_status
    EditorClass.investigar_poi_seleccionado = investigar_poi_seleccionado
    EditorClass.revisar_investigacion_seleccionada = revisar_investigacion_seleccionada
    EditorClass.aprobar_investigacion_seleccionada = aprobar_investigacion_seleccionada
    EditorClass._investigacion_ui_applied = True


def _abrir_ventana_progreso(parent):
    ventana = tk.Toplevel(parent)
    ventana.title("Motor de Investigación")
    ventana.resizable(False, False)
    ventana.transient(parent)
    ttk.Label(ventana, text="Investigando...", padding=24).pack()
    ventana.protocol("WM_DELETE_WINDOW", lambda: None)
    ventana.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - ventana.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - ventana.winfo_height()) // 2
    ventana.geometry(f"+{x}+{y}")
    return ventana


def _abrir_ventana_revision(parent, poi_dir):
    """Ventana de solo lectura con el resultado completo de una
    investigación. No modal: no usa transient()+grab_set(), así que no
    bloquea la interacción con el resto del Editor mientras está
    abierta.

    Guarda los widgets clave y los datos de cada pestaña como atributos
    de la ventana (notebook, resumen_datos, texto_borrador,
    texto_fuentes, tabla_historial) para que puedan inspeccionarse
    directamente, tanto desde pruebas automatizadas como desde una
    futura extensión de esta misma ventana."""
    carpeta_research = adaptador_poi.ruta_research(poi_dir)

    ventana = tk.Toplevel(parent)
    ventana.title("Investigación del POI")
    ventana.geometry("760x560")

    notebook = ttk.Notebook(ventana)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)
    ventana.notebook = notebook

    ventana.resumen_datos = _agregar_pestana_resumen(notebook, carpeta_research)
    ventana.texto_borrador = _agregar_pestana_solo_lectura(
        notebook, "Borrador", adaptador_poi.ruta_borrador_master(poi_dir)
    )
    ventana.texto_fuentes = _agregar_pestana_solo_lectura(notebook, "Fuentes", adaptador_poi.ruta_fuentes(poi_dir))
    ventana.tabla_historial = _agregar_pestana_historial(notebook, carpeta_research)

    return ventana


def _agregar_pestana_resumen(notebook, carpeta_research):
    pestana = ttk.Frame(notebook, padding=16)
    notebook.add(pestana, text="Resumen")

    datos = estados.leer_estado(carpeta_research)
    if datos is None:
        ttk.Label(pestana, text=f"No se pudo leer {estados.NOMBRE_ARCHIVO_ESTADO}.").pack(anchor="w")
        return None

    filas = (
        ("Estado actual", datos.get("state", "")),
        ("Fecha de creación", datos.get("created_at", "")),
        ("Última actualización", datos.get("updated_at", "")),
        ("Proveedor utilizado", datos.get("provider", "")),
        ("Modelo", datos.get("model", "")),
        ("Cantidad de fuentes", str(len(datos.get("sources") or []))),
        ("Cantidad de contradicciones", str(len(datos.get("contradictions_detected") or []))),
    )
    for fila, (etiqueta, valor) in enumerate(filas):
        ttk.Label(pestana, text=f"{etiqueta}:", font=("Arial", 10, "bold")).grid(
            row=fila, column=0, sticky="w", padx=(0, 16), pady=4
        )
        ttk.Label(pestana, text=valor).grid(row=fila, column=1, sticky="w", pady=4)

    return datos


def _agregar_pestana_solo_lectura(notebook, titulo, ruta):
    pestana = ttk.Frame(notebook)
    notebook.add(pestana, text=titulo)

    texto = ScrolledText(pestana, wrap="word", font=("Arial", 10))
    texto.pack(fill="both", expand=True, padx=8, pady=8)

    if ruta.exists():
        contenido = ruta.read_text(encoding="utf-8")
    else:
        contenido = f"(No se encontró {ruta.name}.)"

    texto.insert("1.0", contenido)
    texto.config(state="disabled")
    return texto


def _agregar_pestana_historial(notebook, carpeta_research):
    pestana = ttk.Frame(notebook)
    notebook.add(pestana, text="Historial")

    columnas = ("fecha", "evento", "actor", "detalle")
    encabezados = {"fecha": "Fecha", "evento": "Evento", "actor": "Actor", "detalle": "Detalle"}
    anchos = {"fecha": 150, "evento": 120, "actor": 80, "detalle": 300}

    tabla = ttk.Treeview(pestana, columns=columnas, show="headings")
    for columna in columnas:
        tabla.heading(columna, text=encabezados[columna])
        tabla.column(columna, width=anchos[columna], anchor="w")

    for evento in estados.leer_historial(carpeta_research):
        tabla.insert(
            "",
            "end",
            values=(
                evento.get("timestamp", ""),
                evento.get("event", ""),
                evento.get("actor", ""),
                _describir_evento(evento),
            ),
        )

    scroll = ttk.Scrollbar(pestana, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=scroll.set)
    tabla.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
    scroll.pack(side="right", fill="y", pady=8)
    return tabla


def _describir_evento(evento: dict) -> str:
    """Arma una descripción legible de un evento de historial.json sin
    mostrar el JSON crudo, incluyendo cualquier campo extra que traiga
    (por ejemplo, un futuro evento EXPORTED con "zip")."""
    campos_ya_mostrados = {"timestamp", "event", "actor", "from", "to", "detail"}
    partes = []

    if evento.get("event") == "STATE_CHANGE":
        partes.append(f"{evento.get('from', '?')} → {evento.get('to', '?')}")
    if evento.get("detail"):
        partes.append(str(evento["detail"]))
    for clave, valor in evento.items():
        if clave in campos_ya_mostrados:
            continue
        partes.append(f"{clave}: {valor}")

    return " — ".join(partes)
