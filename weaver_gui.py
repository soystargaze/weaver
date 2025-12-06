import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import threading
import weaver_core as core

class PixelWeaverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixel-Weaver: Final Stable")
        self.root.geometry("1000x800")
        self.root.configure(bg="#1e1e1e")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="#e0e0e0", font=("Consolas", 10))
        style.configure("Header.TLabel", font=("Consolas", 16, "bold"), foreground="#00ff99")
        style.configure("TButton", background="#333", foreground="#fff", borderwidth=1)
        style.map("TButton", background=[('active', '#444')])
        style.configure("TCheckbutton", background="#1e1e1e", foreground="#e0e0e0")
        style.map("TCheckbutton", background=[('active', '#1e1e1e')])

        self.img_path = None
        self.original_pil = None
        self.result_pil = None    
        self.savable_pil = None   
        self.zoom_level = 1.0
        self.display_image = None
        self.is_processing = False

        header = ttk.Frame(root)
        header.pack(fill="x", padx=20, pady=10)
        ttk.Label(header, text="👾 Pixel-Weaver", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="| Manual Precision", style="TLabel").pack(side="left", padx=10)

        main_split = tk.PanedWindow(root, orient="horizontal", bg="#1e1e1e", sashwidth=4)
        main_split.pack(fill="both", expand=True, padx=10, pady=10)

        controls = ttk.Frame(main_split, width=300, padding=10)
        main_split.add(controls)

        ttk.Button(controls, text="📂 Cargar Imagen", command=self.load_image).pack(fill="x", pady=10)

        # 1. GRID
        labelframe_grid = ttk.Labelframe(controls, text="1. Rejilla (Grid)", padding=10)
        labelframe_grid.pack(fill="x", pady=10)

        ttk.Label(labelframe_grid, text="Resolución (ej. 100):").pack(anchor="w")
        self.var_grid = tk.IntVar(value=100) 
        ttk.Entry(labelframe_grid, textvariable=self.var_grid).pack(fill="x")
        
        # AUTO ALIGN (OFF BY DEFAULT)
        self.var_auto = tk.BooleanVar(value=False)
        chk_auto = ttk.Checkbutton(labelframe_grid, text="Auto-Detect Offset", variable=self.var_auto, style="TCheckbutton")
        chk_auto.pack(anchor="w", pady=(10,0))
        ttk.Label(labelframe_grid, text="* Activar solo si la imagen no está centrada.", font=("Consolas", 8), foreground="#aaa").pack(anchor="w")

        # 2. COLOR
        labelframe_opt = ttk.Labelframe(controls, text="2. Color Inteligente", padding=10)
        labelframe_opt.pack(fill="x", pady=10)
        
        ttk.Label(labelframe_opt, text="Número de Colores:").pack(anchor="w")
        self.var_colors = tk.IntVar(value=16)
        self.lbl_colors = ttk.Label(labelframe_opt, text="16 Colores")
        self.lbl_colors.pack(anchor="e")
        ttk.Scale(labelframe_opt, from_=2, to=64, variable=self.var_colors, command=lambda e: self.update_labels()).pack(fill="x")
        
        ttk.Label(labelframe_opt, text="* Recupera sombras usando promedios opacos.", font=("Consolas", 8), foreground="#aaa", wraplength=250).pack(anchor="w", pady=(5,0))

        # PROGRESO
        self.progress_bar = ttk.Progressbar(controls, orient="horizontal", length=100, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(20, 5))

        self.btn_process = ttk.Button(controls, text="✨ PROCESAR ✨", command=self.start_process_thread)
        self.btn_process.pack(fill="x", pady=10)
        
        ttk.Button(controls, text="💾 Guardar", command=self.save_img).pack(fill="x", pady=5)

        preview_frame = ttk.Frame(main_split, padding=10)
        main_split.add(preview_frame)
        
        toolbar = ttk.Frame(preview_frame)
        toolbar.pack(fill="x", pady=(0, 5))
        ttk.Button(toolbar, text="Original", command=self.show_original).pack(side="left")
        ttk.Button(toolbar, text="Resultado", command=self.show_result).pack(side="left", padx=5)
        ttk.Label(toolbar, text="| Zoom:").pack(side="left", padx=10)
        ttk.Button(toolbar, text="-", width=3, command=lambda: self.change_zoom(-0.5)).pack(side="left")
        ttk.Button(toolbar, text="+", width=3, command=lambda: self.change_zoom(0.5)).pack(side="left")

        self.canvas = tk.Canvas(preview_frame, bg="#101010", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)

    def update_labels(self):
        c = self.var_colors.get()
        self.lbl_colors.config(text=f"{c} Colores")

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
        if not path: return
        self.img_path = path
        self.original_pil = Image.open(path).convert("RGBA")
        self.result_pil = None
        self.savable_pil = None
        self.zoom_level = 1.0
        self.display_image = self.original_pil
        self.refresh_canvas()

    def start_process_thread(self):
        if not self.original_pil or self.is_processing: return
        self.is_processing = True
        self.btn_process.config(state="disabled")
        self.progress_bar["value"] = 0
        threading.Thread(target=self.process, daemon=True).start()

    def process(self):
        try:
            grid = int(self.var_grid.get())
            limit = int(self.var_colors.get())
            auto = self.var_auto.get()

            def update_prog(val):
                self.root.after(0, lambda: self.progress_bar.configure(value=val))

            processed_tiny = core.process_pixel_art(
                self.original_pil, 
                grid_res=grid, 
                max_colors=limit,
                auto_align=auto,
                progress_callback=update_prog
            )
            
            self.savable_pil = processed_tiny
            self.result_pil = core.generate_tiled_preview(processed_tiny)
            self.root.after(0, self.finish_processing)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.btn_process.config(state="normal"))
            self.is_processing = False

    def finish_processing(self):
        self.is_processing = False
        self.btn_process.config(state="normal")
        self.show_result()

    def show_original(self):
        if self.original_pil:
            self.display_image = self.original_pil
            self.refresh_canvas()

    def show_result(self):
        if self.result_pil:
            self.display_image = self.result_pil
            self.refresh_canvas()

    def change_zoom(self, amount):
        if not self.display_image: return
        self.zoom_level = max(0.5, min(32.0, self.zoom_level + amount))
        self.refresh_canvas()

    def refresh_canvas(self):
        if not self.display_image: return
        w, h = self.display_image.size
        nw, nh = int(w * self.zoom_level), int(h * self.zoom_level)
        resized = self.display_image.resize((nw, nh), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(resized) 
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x = max(0, (cw - nw) // 2)
        y = max(0, (ch - nh) // 2)
        self.canvas.create_image(x, y, image=self.tk_img, anchor="nw")
        self.canvas.config(scrollregion=(0, 0, nw, nh))

    def on_drag_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def on_drag_move(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def save_img(self):
        if not self.savable_pil: 
            messagebox.showwarning("Aviso", "Procesa la imagen primero")
            return
        base = os.path.splitext(self.img_path)[0]
        grid_res = int(self.var_grid.get())
        out_path = f"{base}_{grid_res}px.png"
        self.savable_pil.save(out_path)
        messagebox.showinfo("Guardado", f"Archivo: {out_path}\nTamaño: {self.savable_pil.size}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PixelWeaverGUI(root)
    root.mainloop()
