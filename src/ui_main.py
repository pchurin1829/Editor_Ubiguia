from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText

from config import load_config, save_config, project_root
from filesystem import list_dirs, open_folder
from poi_manager import list_pois, next_poi_number, create_poi, city_path, find_master_file, ensure_poi_structure
from validator import validate_text
from repair import repair_city
from zip_export import export_pois
from constants import APP_NAME, APP_VERSION, POI_MASTER_FILE, SHARED_IMAGES_FOLDER, SHARED_VIDEOS_FOLDER, AUDIO_FOLDER

def poi_title(folder_name: str) -> str:
    return folder_name.split("-", 1)[1].strip() if "-" in folder_name else folder_name

def count_files(folder: Path, extensions=None) -> int:
    if not folder.exists():
        return 0
    files = [p for p in folder.rglob("*") if p.is_file()]
    if extensions:
        extensions = {e.lower() for e in extensions}
        files = [p for p in files if p.suffix.lower() in extensions]
    return len(files)

def nonempty_text(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return False
    meaningful = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
    return any(len(line) > 10 for line in meaningful)

class EditorUBIGUIA(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry(f"{self.cfg.get('window_width',1180)}x{self.cfg.get('window_height',760)}")

        self.country_var = tk.StringVar(value=self.cfg.get("last_country", "ARGENTINA"))
        self.province_var = tk.StringVar(value=self.cfg.get("last_province", "BUENOS AIRES"))
        self.city_var = tk.StringVar(value=self.cfg.get("last_city", "LA PLATA"))
        self.status_var = tk.StringVar(value="Seleccione un POI para ver su estado.")

        self.build_ui()
        self.ensure_root()
        self.refresh_all()

    def build_ui(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        box = ttk.LabelFrame(main, text="Proyecto")
        box.pack(fill="x")
        self.root_label = ttk.Label(box, text="Carpeta TURISMO:")
        self.root_label.pack(side="left", padx=8, pady=8)
        ttk.Button(box, text="Cambiar", command=self.change_root).pack(side="right", padx=8)

        selectors = ttk.Frame(main)
        selectors.pack(fill="x", pady=10)

        ttk.Label(selectors, text="País").grid(row=0, column=0, sticky="w")
        self.country_cb = ttk.Combobox(selectors, textvariable=self.country_var, width=30, state="readonly")
        self.country_cb.grid(row=1, column=0, padx=(0,10))
        self.country_cb.bind("<<ComboboxSelected>>", lambda e: self.on_country())

        ttk.Label(selectors, text="Provincia").grid(row=0, column=1, sticky="w")
        self.province_cb = ttk.Combobox(selectors, textvariable=self.province_var, width=30, state="readonly")
        self.province_cb.grid(row=1, column=1, padx=(0,10))
        self.province_cb.bind("<<ComboboxSelected>>", lambda e: self.on_province())

        ttk.Label(selectors, text="Ciudad").grid(row=0, column=2, sticky="w")
        self.city_cb = ttk.Combobox(selectors, textvariable=self.city_var, width=30, state="readonly")
        self.city_cb.grid(row=1, column=2)
        self.city_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_pois())

        center = ttk.Frame(main)
        center.pack(fill="both", expand=True)

        pois_box = ttk.LabelFrame(center, text="POIs")
        pois_box.pack(side="left", fill="both", expand=True)

        self.poi_list = tk.Listbox(pois_box, selectmode=tk.EXTENDED)
        self.poi_list.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.poi_list.bind("<Double-Button-1>", lambda e: self.edit_master())
        self.poi_list.bind("<<ListboxSelect>>", lambda e: self.update_status())

        scroll = ttk.Scrollbar(pois_box, orient="vertical", command=self.poi_list.yview)
        scroll.pack(side="right", fill="y")
        self.poi_list.configure(yscrollcommand=scroll.set)

        status_box = ttk.LabelFrame(center, text="Estado del POI", width=290)
        status_box.pack(side="right", fill="y", padx=(10,0))
        status_box.pack_propagate(False)

        self.status_label = ttk.Label(
            status_box,
            textvariable=self.status_var,
            justify="left",
            anchor="nw",
            padding=10
        )
        self.status_label.pack(fill="both", expand=True)

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=(10,0))

        group_poi = ttk.LabelFrame(actions, text="POI")
        group_poi.pack(side="left", padx=(0,6))
        ttk.Button(group_poi, text="Nuevo", command=self.new_poi).pack(side="left", padx=3, pady=4)
        ttk.Button(group_poi, text="Editar MASTER", command=self.edit_master).pack(side="left", padx=3, pady=4)
        ttk.Button(group_poi, text="Validar", command=self.validate_selected).pack(side="left", padx=3, pady=4)

        group_content = ttk.LabelFrame(actions, text="Contenido")
        group_content.pack(side="left", padx=6)
        ttk.Button(group_content, text="Texto ES", command=lambda:self.edit_text("ESPAÑOL")).pack(side="left", padx=3, pady=4)
        ttk.Button(group_content, text="Texto EN", command=lambda:self.edit_text("INGLES")).pack(side="left", padx=3, pady=4)
        ttk.Button(group_content, text="Texto PT", command=lambda:self.edit_text("PORTUGUES")).pack(side="left", padx=3, pady=4)
        ttk.Button(group_content, text="Imágenes", command=self.open_images).pack(side="left", padx=3, pady=4)
        ttk.Button(group_content, text="Videos", command=self.open_videos).pack(side="left", padx=3, pady=4)
        ttk.Button(group_content, text="Audio ES", command=lambda:self.open_audio("ESPAÑOL")).pack(side="left", padx=3, pady=4)
        ttk.Button(group_content, text="Audio EN", command=lambda:self.open_audio("INGLES")).pack(side="left", padx=3, pady=4)
        ttk.Button(group_content, text="Audio PT", command=lambda:self.open_audio("PORTUGUES")).pack(side="left", padx=3, pady=4)

        group_export = ttk.LabelFrame(actions, text="Exportar")
        group_export.pack(side="left", padx=6)
        ttk.Button(group_export, text="Generar ZIP", command=self.export_selected).pack(side="left", padx=3, pady=4)
        ttk.Button(group_export, text="Abrir carpeta", command=self.open_selected_folder).pack(side="left", padx=3, pady=4)

        group_maint = ttk.LabelFrame(actions, text="Mantenimiento")
        group_maint.pack(side="right", padx=(6,0))
        ttk.Button(group_maint, text="Actualizar", command=self.refresh_all).pack(side="left", padx=3, pady=4)
        ttk.Button(group_maint, text="Reparar ciudad", command=self.repair_current_city).pack(side="left", padx=3, pady=4)
        ttk.Button(group_maint, text="Salir", command=self.destroy).pack(side="left", padx=3, pady=4)

    def turismo_root(self):
        return self.cfg.get("turismo_root", "")

    def ensure_root(self):
        if not self.turismo_root() or not Path(self.turismo_root()).exists():
            messagebox.showinfo("Configuración", "Seleccione la carpeta TURISMO.")
            self.change_root()

    def change_root(self):
        selected = filedialog.askdirectory(title="Seleccione la carpeta TURISMO")
        if selected:
            self.cfg["turismo_root"] = selected
            save_config(self.cfg)
            self.refresh_all()

    def refresh_all(self):
        root = self.turismo_root()
        self.root_label.config(text=f"Carpeta TURISMO: {root}")
        countries = list_dirs(Path(root)) if root else []
        self.country_cb["values"] = countries
        if countries and self.country_var.get() not in countries:
            self.country_var.set(countries[0])
        self.refresh_provinces()
        self.refresh_pois()

    def refresh_provinces(self):
        provinces = list_dirs(Path(self.turismo_root()) / self.country_var.get())
        self.province_cb["values"] = provinces
        if provinces and self.province_var.get() not in provinces:
            self.province_var.set(provinces[0])
        self.refresh_cities()

    def refresh_cities(self):
        cities = list_dirs(Path(self.turismo_root()) / self.country_var.get() / self.province_var.get())
        self.city_cb["values"] = cities
        if cities and self.city_var.get() not in cities:
            self.city_var.set(cities[0])

    def refresh_pois(self):
        self.poi_list.delete(0, tk.END)
        for name in list_pois(self.turismo_root(), self.country_var.get(), self.province_var.get(), self.city_var.get()):
            self.poi_list.insert(tk.END, name)

        self.cfg["last_country"] = self.country_var.get()
        self.cfg["last_province"] = self.province_var.get()
        self.cfg["last_city"] = self.city_var.get()
        save_config(self.cfg)
        self.status_var.set("Seleccione un POI para ver su estado.")

    def on_country(self):
        self.refresh_provinces()
        self.refresh_pois()

    def on_province(self):
        self.refresh_cities()
        self.refresh_pois()

    def current_city_path(self):
        return city_path(self.turismo_root(), self.country_var.get(), self.province_var.get(), self.city_var.get())

    def selected_names(self):
        return [self.poi_list.get(i) for i in self.poi_list.curselection()]

    def selected_path(self):
        names = self.selected_names()
        if not names:
            messagebox.showwarning("Atención", "Seleccione un POI.")
            return None
        path = self.current_city_path() / names[0]
        ensure_poi_structure(path)
        return path

    def selected_paths(self):
        paths = [self.current_city_path() / n for n in self.selected_names()]
        for path in paths:
            ensure_poi_structure(path)
        return paths

    def update_status(self):
        names = self.selected_names()
        if not names:
            self.status_var.set("Seleccione un POI para ver su estado.")
            return

        path = self.current_city_path() / names[0]
        ensure_poi_structure(path)

        master_ok = nonempty_text(path / POI_MASTER_FILE)
        es_ok = nonempty_text(path / "ESPAÑOL" / "texto.md")
        en_ok = nonempty_text(path / "INGLES" / "texto.md")
        pt_ok = nonempty_text(path / "PORTUGUES" / "texto.md")

        images = count_files(path / SHARED_IMAGES_FOLDER, {".jpg", ".jpeg", ".jtif", ".png", ".webp"})
        audio_es = count_files(path / "ESPAÑOL" / AUDIO_FOLDER, {".mp3", ".wav", ".m4a"})
        audio_en = count_files(path / "INGLES" / AUDIO_FOLDER, {".mp3", ".wav", ".m4a"})
        audio_pt = count_files(path / "PORTUGUES" / AUDIO_FOLDER, {".mp3", ".wav", ".m4a"})

        mark = lambda ok: "✓" if ok else "✗"

        self.status_var.set(
            f"{path.name}\n\n"
            f"{mark(master_ok)} POI MASTER\n"
            f"{mark(es_ok)} Texto ES\n"
            f"{mark(en_ok)} Texto EN\n"
            f"{mark(pt_ok)} Texto PT\n\n"
            f"Imágenes: {images}\n"
            f"{mark(audio_es > 0)} Audio ES\n"
            f"{mark(audio_en > 0)} Audio EN\n"
            f"{mark(audio_pt > 0)} Audio PT"
        )

    def ask_optional_text(self, title, prompt, initial=""):
        win = tk.Toplevel(self)
        win.title(title)
        win.resizable(False, False)
        win.transient(self)

        ttk.Label(win, text=prompt).pack(padx=12, pady=(12, 6))
        var = tk.StringVar(value=initial)
        entry = ttk.Entry(win, textvariable=var, width=40)
        entry.pack(padx=12, pady=(0, 6), fill="x")

        result = {"value": None}

        def on_ok(event=None):
            result["value"] = var.get()
            win.destroy()

        def on_cancel(event=None):
            result["value"] = None
            win.destroy()

        btns = ttk.Frame(win)
        btns.pack(pady=(0, 12))
        ttk.Button(btns, text="OK", command=on_ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancelar", command=on_cancel).pack(side="left", padx=4)

        win.bind("<Return>", on_ok)
        win.bind("<Escape>", on_cancel)
        win.protocol("WM_DELETE_WINDOW", on_cancel)

        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")

        win.grab_set()
        win.lift()
        win.focus_force()
        entry.focus_set()
        entry.select_range(0, tk.END)

        self.wait_window(win)
        return result["value"]

    def select_poi_in_list(self, name):
        items = self.poi_list.get(0, tk.END)
        if name not in items:
            return
        idx = items.index(name)
        self.poi_list.selection_clear(0, tk.END)
        self.poi_list.selection_set(idx)
        self.poi_list.activate(idx)
        self.poi_list.see(idx)

    def new_poi(self):
        number = next_poi_number(list_pois(self.turismo_root(), self.country_var.get(), self.province_var.get(), self.city_var.get()))
        name = simpledialog.askstring("Nuevo POI", f"Número sugerido: {number}\n\nNombre:", parent=self)
        if not name:
            return
        category = self.ask_optional_text("Nuevo POI", "Categoría (opcional):")
        if category is None:
            return
        try:
            created_name = f"{number}-{name.strip()}"
            create_poi(self.turismo_root(), self.country_var.get(), self.province_var.get(), self.city_var.get(), number, name, category)
            self.refresh_pois()
            self.select_poi_in_list(created_name)
            self.update_status()
            messagebox.showinfo("Listo", "POI creado correctamente.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def edit_file(self, file_path: Path, title: str):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            file_path.write_text("", encoding="utf-8")

        content = file_path.read_text(encoding="utf-8", errors="replace")
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("900x650")

        text = ScrolledText(win, wrap="word", font=("Arial", 11))
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", content)

        def save():
            file_path.write_text(text.get("1.0", "end-1c"), encoding="utf-8")
            self.update_status()
            messagebox.showinfo("Guardado", "Archivo guardado correctamente.")
            win.destroy()

        bar = ttk.Frame(win)
        bar.pack(fill="x", padx=10, pady=8)
        ttk.Button(bar, text="Guardar", command=save).pack(side="right", padx=4)
        ttk.Button(bar, text="Cancelar", command=win.destroy).pack(side="right", padx=4)

    def edit_master(self):
        path = self.selected_path()
        if not path:
            return
        master = find_master_file(path) or (path / POI_MASTER_FILE)
        if not master.exists():
            master.write_text(f"# POI MASTER\n\n# {poi_title(path.name)}\n", encoding="utf-8")
        self.edit_file(master, f"MASTER - {path.name}")

    def edit_text(self, lang):
        path = self.selected_path()
        if path:
            self.edit_file(path / lang / "texto.md", f"Texto {lang} - {path.name}")

    def open_images(self):
        path = self.selected_path()
        if path:
            folder = path / SHARED_IMAGES_FOLDER
            folder.mkdir(parents=True, exist_ok=True)
            open_folder(folder)

    def open_videos(self):
        path = self.selected_path()
        if path:
            folder = path / SHARED_VIDEOS_FOLDER
            folder.mkdir(parents=True, exist_ok=True)
            open_folder(folder)

    def open_audio(self, lang):
        path = self.selected_path()
        if path:
            folder = path / lang / AUDIO_FOLDER
            folder.mkdir(parents=True, exist_ok=True)
            open_folder(folder)

    def open_selected_folder(self):
        path = self.selected_path()
        if path:
            open_folder(path)

    def validate_selected(self):
        path = self.selected_path()
        if path:
            messagebox.showinfo("Validación", validate_text(path))

    def repair_current_city(self):
        city = self.current_city_path()
        if messagebox.askyesno("Confirmar", f"Reparar estructura de:\n{city}?"):
            report = repair_city(city)
            messagebox.showinfo("Reparación", "\n".join(report[:80]))
            self.refresh_all()

    def export_selected(self):
        paths = self.selected_paths()
        if not paths:
            messagebox.showwarning("Atención", "Seleccione uno o más POIs.")
            return

        zip_path = export_pois(
            project_root() / "export",
            Path(self.turismo_root()),
            self.country_var.get(),
            self.province_var.get(),
            self.city_var.get(),
            paths
        )

        images = sum(count_files(p / SHARED_IMAGES_FOLDER, {".jpg", ".jpeg", ".png",".jtif", ".webp"}) for p in paths)
        audios = sum(
            count_files(p / lang / AUDIO_FOLDER, {".mp3", ".wav", ".m4a"})
            for p in paths for lang in ["ESPAÑOL", "INGLES", "PORTUGUES"]
        )

        messagebox.showinfo(
            "Exportación correcta",
            f"{zip_path.name}\n\n"
            f"POIs: {len(paths)}\n"
            f"Imágenes: {images}\n"
            f"Audios: {audios}\n\n"
            f"Ubicación:\n{zip_path.parent}"
        )
        open_folder(project_root() / "export")
