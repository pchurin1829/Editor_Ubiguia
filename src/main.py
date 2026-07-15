from ui_main import EditorUBIGUIA
from status_patch import apply_status_patch

apply_status_patch(EditorUBIGUIA)

def main():
    app = EditorUBIGUIA()
    app.mainloop()

if __name__ == "__main__":
    main()
