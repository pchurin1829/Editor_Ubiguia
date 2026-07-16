import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

root = tk.Tk()
root.title("UBIGUIA - Crear Nuevo POI")
root.geometry("520x330")

def row(lbl,r):
    tk.Label(root,text=lbl).grid(row=r,column=0,sticky="w",padx=10,pady=6)

row("Carpeta base:",0)
base=tk.StringVar(value=r"I:\MIS PROYECTOS\PROYECTO\Puntos de Interes y MAPA\crear estructura\TURISMO")
e0=tk.Entry(root,textvariable=base,width=55)
e0.grid(row=0,column=1,padx=5)

row("País:",1)
pais=tk.StringVar(value="ARGENTINA")
tk.Entry(root,textvariable=pais,width=35).grid(row=1,column=1,sticky="w")

row("Provincia:",2)
prov=tk.StringVar(value="BUENOS AIRES")
tk.Entry(root,textvariable=prov,width=35).grid(row=2,column=1,sticky="w")

row("Ciudad:",3)
ciudad=tk.StringVar(value="LA PLATA")
tk.Entry(root,textvariable=ciudad,width=35).grid(row=3,column=1,sticky="w")

row("Número:",4)
num=tk.StringVar(value="01")
tk.Entry(root,textvariable=num,width=10).grid(row=4,column=1,sticky="w")

row("Nombre POI:",5)
nombre=tk.StringVar()
tk.Entry(root,textvariable=nombre,width=40).grid(row=5,column=1,sticky="w")

def crear():
    if not nombre.get().strip():
        messagebox.showerror("Error","Ingrese el nombre del POI")
        return
    poi_dir=os.path.join(base.get(),pais.get(),prov.get(),ciudad.get(),f"{num.get()}-{nombre.get()}")
    os.makedirs(poi_dir,exist_ok=True)
    for lang in ["ESPAÑOL","INGLES","PORTUGUES"]:
        ldir=os.path.join(poi_dir,lang)
        os.makedirs(os.path.join(ldir,"audio"),exist_ok=True)
        os.makedirs(os.path.join(ldir,"imagenes"),exist_ok=True)
        os.makedirs(os.path.join(ldir,"qr"),exist_ok=True)
        meta={
            "poi_id":"",
            "lang":lang,
            "title":nombre.get(),
            "summary":"",
            "content_markdown":"texto.md",
            "main_audio":"",
            "images":[],
            "qr":[],
            "tags":[],
            "version":1
        }
        with open(os.path.join(ldir,"meta.json"),"w",encoding="utf8") as f:
            json.dump(meta,f,ensure_ascii=False,indent=4)
        with open(os.path.join(ldir,"texto.md"),"w",encoding="utf8") as f:
            f.write(f"# {nombre.get()}\n\n## Resumen\n\n## Historia\n\n## Qué observar\n\n## Información útil\n")
    poi={
        "poi_order":num.get(),
        "poi_name":nombre.get(),
        "country":pais.get(),
        "province":prov.get(),
        "city":ciudad.get()
    }
    with open(os.path.join(poi_dir,"poi.json"),"w",encoding="utf8") as f:
        json.dump(poi,f,ensure_ascii=False,indent=4)
    with open(os.path.join(poi_dir,f"POI_MASTER-{nombre.get()}.md"),"w",encoding="utf8") as f:
        f.write(f"# POI MASTER\n\n# {nombre.get()}\n\n## 1. Identificación\n\n## 2. Descripción General\n\n## 3. Historia\n\n## 4. Qué observar\n\n## 5. Curiosidades\n\n## 6. Información útil\n\n## 7. Resumen para audio\n\n## 8. POIs relacionados\n\n## 9. Palabras clave\n\n## 10. Fuentes\n")
    messagebox.showinfo("Listo",f"POI creado en:\n{poi_dir}")

tk.Button(root,text="Crear POI",command=crear,height=2,width=20).grid(row=6,column=1,pady=20)
root.mainloop()
