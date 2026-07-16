import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from chatgpt_workflow import (
    build_spanish_prompt, build_translation_prompt, build_audio_prompt,
    extract_available_sections, save_sections, open_chatgpt,
)

def apply_chatgpt_workflow(EditorClass):
    if getattr(EditorClass, "_chatgpt_workflow_applied", False):
        return

    original_build_ui = EditorClass.build_ui

    def build_ui(self):
        original_build_ui(self)
        main = self.winfo_children()[0]
        box = ttk.LabelFrame(main, text="Generación de contenido con ChatGPT")
        box.pack(fill="x", pady=(8, 0))
        ttk.Button(box, text="1. Generar Texto ES", command=lambda: self.prepare_stage_prompt("ES")).pack(side="left", padx=5, pady=5)
        ttk.Button(box, text="2. Traducir EN + PT", command=lambda: self.prepare_stage_prompt("TRANSLATE")).pack(side="left", padx=5, pady=5)
        ttk.Button(box, text="3. Generar guiones", command=lambda: self.prepare_stage_prompt("AUDIO")).pack(side="left", padx=5, pady=5)
        ttk.Button(box, text="Abrir ChatGPT", command=open_chatgpt).pack(side="left", padx=5, pady=5)
        ttk.Button(box, text="Importar respuesta", command=self.import_chatgpt_response).pack(side="left", padx=5, pady=5)

    def prepare_stage_prompt(self, stage):
        path = self.selected_path()
        if not path:
            return
        try:
            if stage == "ES":
                prompt, description = build_spanish_prompt(path), "Texto español"
            elif stage == "TRANSLATE":
                prompt, description = build_translation_prompt(path), "traducciones EN y PT"
            elif stage == "AUDIO":
                prompt, description = build_audio_prompt(path), "tres guiones de audio"
            else:
                raise ValueError("Etapa desconocida.")
        except Exception as exc:
            messagebox.showerror("No se pudo preparar el prompt", str(exc))
            return
        self.clipboard_clear()
        self.clipboard_append(prompt)
        self.update()
        messagebox.showinfo("Prompt preparado", f"El prompt para {description} quedó copiado.\n\nAbra ChatGPT, pegue con Ctrl+V y envíelo.")

    def import_chatgpt_response(self):
        path = self.selected_path()
        if not path:
            return
        window = tk.Toplevel(self)
        window.title(f"Importar respuesta de ChatGPT - {path.name}")
        window.geometry("980x720")
        window.minsize(760, 520)
        ttk.Label(window, text="Pegue la respuesta completa de la etapa actual. El Editor detectará automáticamente los bloques presentes.", padding=12).pack(fill="x")
        editor = ScrolledText(window, wrap="word", font=("Arial", 11), undo=True)
        editor.pack(fill="both", expand=True, padx=12, pady=8)
        try:
            clipboard_text = self.clipboard_get()
            if "<<<" in clipboard_text and ">>>" in clipboard_text:
                editor.insert("1.0", clipboard_text)
        except Exception:
            pass

        def import_now():
            try:
                sections = extract_available_sections(editor.get("1.0", "end-1c").strip())
            except Exception as exc:
                messagebox.showerror("Respuesta inválida", str(exc))
                return
            block_names = {
                "TEXT_ES": "Texto ES", "TEXT_EN": "Texto EN", "TEXT_PT": "Texto PT",
                "AUDIO_ES": "Guion audio ES", "AUDIO_EN": "Guion audio EN", "AUDIO_PT": "Guion audio PT",
            }
            detected = "\n".join(f"• {block_names[key]}" for key in sections)
            if not messagebox.askyesno("Confirmar importación", "Se detectaron estos bloques:\n\n" + detected + "\n\nLos archivos correspondientes serán reemplazados.\n\n¿Continuar?"):
                return
            try:
                saved = save_sections(path, sections)
            except Exception as exc:
                messagebox.showerror("Error al guardar", str(exc))
                return
            self.update_status()
            messagebox.showinfo("Importación completa", "Se guardaron correctamente:\n\n" + "\n".join(f"• {item}" for item in saved))
            window.destroy()

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(buttons, text="Cancelar", command=window.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="Importar y guardar", command=import_now).pack(side="right", padx=4)

    EditorClass.build_ui = build_ui
    EditorClass.prepare_stage_prompt = prepare_stage_prompt
    EditorClass.import_chatgpt_response = import_chatgpt_response
    EditorClass._chatgpt_workflow_applied = True
