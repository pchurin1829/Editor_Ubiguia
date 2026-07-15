import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from chatgpt_workflow import (
    build_prompt,
    extract_sections,
    save_sections,
    open_chatgpt,
)


def apply_chatgpt_workflow(EditorClass):
    if getattr(EditorClass, "_chatgpt_workflow_applied", False):
        return

    original_build_ui = EditorClass.build_ui

    def build_ui(self):
        original_build_ui(self)

        main = self.winfo_children()[0]
        box = ttk.LabelFrame(main, text="Trabajar con ChatGPT")
        box.pack(fill="x", pady=(8, 0))

        ttk.Button(
            box,
            text="1. Preparar prompt",
            command=self.prepare_chatgpt_prompt,
        ).pack(side="left", padx=5, pady=5)

        ttk.Button(
            box,
            text="2. Abrir ChatGPT",
            command=open_chatgpt,
        ).pack(side="left", padx=5, pady=5)

        ttk.Button(
            box,
            text="3. Importar respuesta",
            command=self.import_chatgpt_response,
        ).pack(side="left", padx=5, pady=5)

    def prepare_chatgpt_prompt(self):
        path = self.selected_path()
        if not path:
            return

        prompt = build_prompt(path)
        self.clipboard_clear()
        self.clipboard_append(prompt)
        self.update()

        messagebox.showinfo(
            "Prompt preparado",
            "El prompt completo quedó copiado al portapapeles.\n\n"
            "Pulse ‘Abrir ChatGPT’, péguelo y envíelo.",
        )

    def import_chatgpt_response(self):
        path = self.selected_path()
        if not path:
            return

        window = tk.Toplevel(self)
        window.title(f"Importar respuesta de ChatGPT - {path.name}")
        window.geometry("980x720")
        window.minsize(760, 520)

        ttk.Label(
            window,
            text=(
                "Pegue la respuesta completa de ChatGPT, "
                "incluyendo todos los marcadores <<<...>>>."
            ),
            padding=12,
        ).pack(fill="x")

        editor = ScrolledText(
            window,
            wrap="word",
            font=("Arial", 11),
            undo=True,
        )
        editor.pack(fill="both", expand=True, padx=12, pady=8)

        try:
            clipboard_text = self.clipboard_get()
            if "<<<TEXT_ES>>>" in clipboard_text:
                editor.insert("1.0", clipboard_text)
        except Exception:
            pass

        def import_now():
            response = editor.get("1.0", "end-1c").strip()

            try:
                sections = extract_sections(response)
            except Exception as exc:
                messagebox.showerror("Respuesta inválida", str(exc))
                return

            if not messagebox.askyesno(
                "Confirmar importación",
                "Se reemplazarán los textos ES, EN y PT.\n"
                "También se crearán los tres guiones de audio.\n\n"
                "¿Continuar?",
            ):
                return

            try:
                save_sections(path, sections)
            except Exception as exc:
                messagebox.showerror("Error al guardar", str(exc))
                return

            self.update_status()
            messagebox.showinfo(
                "Importación completa",
                "Se guardaron correctamente:\n\n"
                "• Texto ES\n"
                "• Texto EN\n"
                "• Texto PT\n"
                "• Guion de audio ES\n"
                "• Guion de audio EN\n"
                "• Guion de audio PT",
            )
            window.destroy()

        button_bar = ttk.Frame(window)
        button_bar.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Button(
            button_bar,
            text="Cancelar",
            command=window.destroy,
        ).pack(side="right", padx=4)

        ttk.Button(
            button_bar,
            text="Importar y guardar",
            command=import_now,
        ).pack(side="right", padx=4)

    EditorClass.build_ui = build_ui
    EditorClass.prepare_chatgpt_prompt = prepare_chatgpt_prompt
    EditorClass.import_chatgpt_response = import_chatgpt_response
    EditorClass._chatgpt_workflow_applied = True
