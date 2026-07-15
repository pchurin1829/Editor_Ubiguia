from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText

from config import load_config, save_config, project_root
from filesystem import list_dirs, open_folder, open_file
from poi_manager import list_pois, next_poi_number, create_poi, city_path, find_master_file
from validator import validate_text
from repair import repair_city
from zip_export import export_pois
from constants import APP_NAME, POI_MASTER_FILE

def poi_title_from_folder(folder_name: str) -> str:
    if "-" in folder_name:
        return folder_name.split("-", 1)[1].strip()
    return folder_name.strip()

def create_master_if_missing(poi_dir: Path) -> Path:
    master = poi_dir / POI_MASTER_FILE
    if master.exists():
        return master

    title = poi_title_from_folder(poi_dir.name)
    content = f"""# POI MASTER

# {title}

## 1. Identificación

Nombre: {title}

## 2. Descripción General

## 3. Historia

## 4. Qué observar

## 5. Curiosidades

## 6. Información útil

## 7. Resumen para audio

## 8. POIs relacionados

## 9. Palabras clave

## 10. Fuentes
"""
    master.write_text(content, encoding="utf-8")
    return master

class EditorUBIGUIA(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.title(f"{APP_NAME} v2.6")
        self.geometry(f"{self.cfg.get('window_width', 1100)}x{self.cfg.get('window_height', 700)}")

        self.country_var = tk.StringVar(value=self.cfg.get("last_country", "ARGENTINA"))
        self.province_var = tk.StringVar(value=self.cfg.get("last_province", "BUENOS AIRES"))
        self.city_var = tk.StringVar(value=self.cfg.get("last_city", "LA PLATA"))

        self.build_ui()
        self.ensure_turismo_root()
        self.refresh_all()

    def build_ui(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        project_box = ttk.LabelFrame(main, text="Proyecto")
        project_box.pack(fill="x")
        self.root_label = ttk.Label(project_box, text="Carpeta TURISMO:")
        self.root_label.pack(side="left", padx=8, pady=8)
        ttk.Button(project_box, text="Cambiar", command=self.change_turismo_root).pack(side="right", padx=8)

        selectors = ttk.Frame(main)
        selectors.pack(fill="x", pady=10)

        ttk.Label(selectors, text="País").grid(row=0, column=0, sticky="w")
        self.country_cb = ttk.Combobox(selectors, textvariable=self.country_var, width=30, state="readonly")
        self.country_cb.grid(row=1, column=0, padx=(0, 10))
        self.country_cb.bind("<<ComboboxSelected>>", lambda e: self.on_country_change())

        ttk.Label(selectors, text="Provincia").grid(row=0, column=1, sticky="w")
        self.province_cb = ttk.Combobox(selectors, textvariable=self.province_var, width=30, state="readonly")
        self.province_cb.grid(row=1, column=1, padx=(0, 10))
        self.province_cb.bind("<<ComboboxSelected>>", lambda e: self.on_province_change())

        ttk.Label(selectors, text="Ciudad").grid(row=0, column=2, sticky="w")
        self.city_cb = ttk.Combobox(selectors, textvariable=self.city_var, width=30, state="readonly")
        self.city_cb.grid(row=1, column=2, padx=(0, 10))
        self.city_cb.bind("<<ComboboxSelected>>", lambda e: self.on_city_change())

        pois_box = ttk.LabelFrame(main, text="POIs")
        pois_box.pack(fill="both", expand=True)

        self.poi_list = tk.Listbox(pois_box, height=20, selectmode=tk.EXTENDED)
        self.poi_list.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.poi_list.bind("<Double-Button-1>", lambda e: self.edit_selected_poi())

        scroll = ttk.Scrollbar(pois_box, orient="vertical", command=self.poi_list.yview)
        scroll.pack(side="right", fill="y")
        self.poi_list.configure(yscrollcommand=scroll.set)

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=10)

        ttk.Button(buttons, text="Nuevo POI", command=self.new_poi).pack(side="left", padx=3)
        ttk.Button(buttons, text="Editar POI", command=self.edit_selected_poi).pack(side="left", padx=3)
        ttk.Button(buttons, text="Pegar Texto ES", command=lambda: self.edit_text_inline("ESPAÑOL")).pack(side="left", padx=3)
        ttk.Button(buttons, text="Texto ES", command=lambda: self.open_lang_file("ESPAÑOL", "texto.md")).pack(side="left", padx=3)
        ttk.Button(buttons, text="Imágenes ES", command=lambda: self.open_lang_folder("ESPAÑOL", "imagenes")).pack(side="left", padx=3)
        ttk.Button(buttons, text="Audio ES", command=lambda: self.open_lang_folder("ESPAÑOL", "audio")).pack(side="left", padx=3)
        ttk.Button(buttons, text="QR ES", command=lambda: self.open_lang_folder("ESPAÑOL", "qr")).pack(side="left", padx=3)
        ttk.Button(buttons, text="Abrir carpeta", command=self.open_selected_folder).pack(side="left", padx=3)
        ttk.Button(buttons, text="Validar POI", command=self.validate_selected).pack(side="left", padx=3)
        ttk.Button(buttons, text="Reparar ciudad", command=self.repair_current_city).pack(side="left", padx=3)
        ttk.Button(buttons, text="Generar ZIP", command=self.export_selected_pois).pack(side="left", padx=3)
        ttk.Button(buttons, text="Actualizar", command=self.refresh_all).pack(side="left", padx=3)
        ttk.Button(buttons, text="Salir", command=self.destroy).pack(side="right", padx=4)

    def ensure_turismo_root(self):
        root = self.cfg.get("turismo_root", "")
        if not root or not Path(root).exists():
            messagebox.showinfo("Configuración inicial", "Seleccione la carpeta TURISMO.")
            self.change_turismo_root()

    def change_turismo_root(self):
        selected = filedialog.askdirectory(title="Seleccione la carpeta TURISMO")
        if selected:
            self.cfg["turismo_root"] = selected
            save_config(self.cfg)
            self.refresh_all()

    def turismo_root(self):
        return self.cfg.get("turismo_root", "")

    def refresh_all(self):
        root = self.turismo_root()
        self.root_label.config(text=f"Carpeta TURISMO: {root}")
        root_path = Path(root) if root else None
        countries = list_dirs(root_path) if root_path else []
        self.country_cb["values"] = countries
        if self.country_var.get() not in countries and countries:
            self.country_var.set(countries[0])
        self.refresh_provinces()
        self.refresh_pois()

    def refresh_provinces(self):
        path = Path(self.turismo_root()) / self.country_var.get()
        provinces = list_dirs(path)
        self.province_cb["values"] = provinces
        if self.province_var.get() not in provinces and provinces:
            self.province_var.set(provinces[0])
        self.refresh_cities()

    def refresh_cities(self):
        path = Path(self.turismo_root()) / self.country_var.get() / self.province_var.get()
        cities = list_dirs(path)
        self.city_cb["values"] = cities
        if self.city_var.get() not in cities and cities:
            self.city_var.set(cities[0])

    def refresh_pois(self):
        self.poi_list.delete(0, tk.END)
        pois = list_pois(self.turismo_root(), self.country_var.get(), self.province_var.get(), self.city_var.get())
        for poi in pois:
            self.poi_list.insert(tk.END, poi)
        self.cfg["last_country"] = self.country_var.get()
        self.cfg["last_province"] = self.province_var.get()
        self.cfg["last_city"] = self.city_var.get()
        save_config(self.cfg)

    def on_country_change(self):
        self.refresh_provinces()
        self.refresh_pois()

    def on_province_change(self):
        self.refresh_cities()
        self.refresh_pois()

    def on_city_change(self):
        self.refresh_pois()

    def selected_poi_names(self):
        selection = self.poi_list.curselection()
        return [self.poi_list.get(i) for i in selection]

    def selected_poi_name(self):
        names = self.selected_poi_names()
        if not names:
            messagebox.showwarning("Atención", "Seleccione un POI.")
            return None
        return names[0]

    def selected_poi_path(self):
        poi_name = self.selected_poi_name()
        if not poi_name:
            return None
        return self.current_city_path() / poi_name

    def selected_poi_paths(self):
        return [self.current_city_path() / name for name in self.selected_poi_names()]

    def current_city_path(self):
        return city_path(self.turismo_root(), self.country_var.get(), self.province_var.get(), self.city_var.get())

    def new_poi(self):
        pois = list_pois(self.turismo_root(), self.country_var.get(), self.province_var.get(), self.city_var.get())
        suggested_number = next_poi_number(pois)
        name = simpledialog.askstring("Nuevo POI", f"Número sugerido: {suggested_number}\\n\\nNombre del POI:")
        if not name:
            return
        category = simpledialog.askstring("Nuevo POI", "Categoría (opcional):") or ""
        try:
            poi_dir = create_poi(project_root(), self.turismo_root(), self.country_var.get(), self.province_var.get(), self.city_var.get(), suggested_number, name.strip(), category.strip())
            self.refresh_pois()
            messagebox.showinfo("Listo", f"POI creado correctamente:\\n{poi_dir}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def open_selected_folder(self):
        path = self.selected_poi_path()
        if path:
            open_folder(path)

    def edit_selected_poi(self):
        path = self.selected_poi_path()
        if not path:
            return
        master = find_master_file(path)
        if not master:
            master = create_master_if_missing(path)
        open_file(master)

    def edit_text_inline(self, lang):
        path = self.selected_poi_path()
        if not path:
            return

        file_path = path / lang / "texto.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if not file_path.exists():
            file_path.write_text(f"# {poi_title_from_folder(path.name)}\\n\\n", encoding="utf-8")

        current = file_path.read_text(encoding="utf-8", errors="replace")

        win = tk.Toplevel(self)
        win.title(f"Pegar Texto {lang} - {path.name}")
        win.geometry("900x600")

        txt = ScrolledText(win, wrap="word", font=("Arial", 11))
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", current)

        def save():
            file_path.write_text(txt.get("1.0", "end-1c"), encoding="utf-8")
            messagebox.showinfo("Guardado", f"Texto guardado en:\\n{file_path}")
            win.destroy()

        bottom = ttk.Frame(win)
        bottom.pack(fill="x", padx=10, pady=8)
        ttk.Button(bottom, text="Guardar", command=save).pack(side="right", padx=5)
        ttk.Button(bottom, text="Cancelar", command=win.destroy).pack(side="right", padx=5)

    def open_lang_file(self, lang, filename):
        path = self.selected_poi_path()
        if not path:
            return
        file_path = path / lang / filename
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f"# {poi_title_from_folder(path.name)}\\n", encoding="utf-8")
        open_file(file_path)

    def open_lang_folder(self, lang, folder):
        path = self.selected_poi_path()
        if not path:
            return
        folder_path = path / lang / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        open_folder(folder_path)

    def validate_selected(self):
        path = self.selected_poi_path()
        if not path:
            return
        result = validate_text(path)
        messagebox.showinfo("Validación", result)

    def repair_current_city(self):
        city_dir = self.current_city_path()
        if not city_dir.exists():
            messagebox.showerror("Error", "No existe la carpeta de ciudad.")
            return
        if not messagebox.askyesno("Confirmar", f"Reparar estructura de:\\n{city_dir}\\n\\n¿Continuar?"):
            return
        report = repair_city(city_dir)
        self.refresh_pois()
        messagebox.showinfo("Reparación finalizada", "\\n".join(report[:80]))

    def export_selected_pois(self):
        poi_dirs = self.selected_poi_paths()
        if not poi_dirs:
            messagebox.showwarning("Atención", "Seleccione uno o más POIs para exportar.")
            return
        export_root = project_root() / "export"
        zip_path = export_pois(export_root, Path(self.turismo_root()), self.country_var.get(), self.province_var.get(), self.city_var.get(), poi_dirs)
        messagebox.showinfo("ZIP generado", f"Archivo creado:\\n{zip_path}")
        open_folder(export_root)
