from constants import POI_MASTER_FILE, SHARED_IMAGES_FOLDER, AUDIO_FOLDER
from content_status import has_real_text, count_media

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".jfif",
    ".jif",
    ".gif",
}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}

def apply_status_patch(EditorClass):
    def update_status(self):
        names = self.selected_names()
        if not names:
            self.status_var.set("Seleccione un POI para ver su estado.")
            return

        path = self.current_city_path() / names[0]

        master_ok = has_real_text(path / POI_MASTER_FILE, 100)
        es_ok = has_real_text(path / "ESPAÑOL" / "texto.md", 100)
        en_ok = has_real_text(path / "INGLES" / "texto.md", 100)
        pt_ok = has_real_text(path / "PORTUGUES" / "texto.md", 100)

        images = count_media(path / SHARED_IMAGES_FOLDER, IMAGE_EXTENSIONS)
        audio_es = count_media(path / "ESPAÑOL" / AUDIO_FOLDER, AUDIO_EXTENSIONS)
        audio_en = count_media(path / "INGLES" / AUDIO_FOLDER, AUDIO_EXTENSIONS)
        audio_pt = count_media(path / "PORTUGUES" / AUDIO_FOLDER, AUDIO_EXTENSIONS)

        mark = lambda ok: "✓" if ok else "✗"

        self.status_var.set(
            f"{path.name}\n\n"
            f"{mark(master_ok)} Ficha del POI\n"
            f"{mark(es_ok)} Texto ES\n"
            f"{mark(en_ok)} Texto EN\n"
            f"{mark(pt_ok)} Texto PT\n\n"
            f"{mark(images > 0)} Imágenes ({images})\n"
            f"{mark(audio_es > 0)} Audio ES ({audio_es})\n"
            f"{mark(audio_en > 0)} Audio EN ({audio_en})\n"
            f"{mark(audio_pt > 0)} Audio PT ({audio_pt})"
        )

    EditorClass.update_status = update_status
