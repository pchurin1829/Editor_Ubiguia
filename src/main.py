from ui_main import EditorUBIGUIA
from status_patch import apply_status_patch
from ui_chatgpt import apply_chatgpt_workflow

apply_status_patch(EditorUBIGUIA)
apply_chatgpt_workflow(EditorUBIGUIA)


def main():
    app = EditorUBIGUIA()
    app.mainloop()


if __name__ == "__main__":
    main()
