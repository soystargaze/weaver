import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import weaver_core as core  # Importing the renamed core file

class PixelWeaverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixel-Weaver: AI Art Fixer")
        self.root.geometry("1100x760")
        self.root.configure(bg="#1e1e1e")

        # --- STYLES ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="#e0e0e0", font=("Consolas", 10))
        style.configure("Header.TLabel", font=("Consolas", 16, "bold"), foreground="#00ff99")
        style.configure("TButton", background="#333", foreground="#fff", borderwidth=1)
        style.map("TButton", background=[('active', '#444')])
        style.configure("TCheckbutton", background="#1e1e1e", foreground="#e0e0e0")
        style.map("TCheckbutton", background=[('active', '#1e1e1e')])

        # --- STATE ---
        self.img_path = None
        self.original_pil = None
        self.result_pil = None
        self.single_result = None
        self.zoom_level = 1.0
        self.display_image = None

        # --- UI LAYOUT ---
        
        # Header
        header = ttk.Frame(root)
        header.pack(fill="x", padx=20, pady=10)
        ttk.Label(header, text="👾 Pixel-Weaver", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="| AI Artifact Cleaner & Seam Fixer", style="TLabel").pack(side="left", padx=10)

        # Split Panes
        main_split = tk.PanedWindow(root, orient="horizontal", bg="#1e1e1e", sashwidth=4)
        main_split.pack(fill="both", expand=True, padx=10, pady=10)

        # === LEFT PANEL ===
        controls = ttk.Frame(main_split, width=320, padding=10)
        main_split.add(controls)

        # File Loader
        ttk.Button(controls, text="📂 Load Image", command=self.load_image).pack(fill="x", pady=10)

        # SECTION 1: CLEANUP
        labelframe_clean = ttk.Labelframe(controls, text="1. Grid & Colors", padding=10)
        labelframe_clean.pack(fill="x", pady=10)

        # Grid Resolution
        ttk.Label(labelframe_clean, text="Force Grid Size (Mixels Fix):").pack(anchor="w")
        self.var_grid = tk.IntVar(value=0) 
        ttk.Entry(labelframe_clean, textvariable=self.var_grid).pack(fill="x")
        ttk.Label(labelframe_clean, text="(e.g., 64 for 64x64). 0 = Off", font=("Consolas", 8), foreground="#888").pack(anchor="w")

        # Smart Sampling Checkbox
        self.var_smart_grid = tk.BooleanVar(value=False)
        chk_smart = ttk.Checkbutton(labelframe_clean, text="Enable Smart Sampling", variable=self.var_smart_grid, style="TCheckbutton")
        chk_smart.pack(anchor="w", pady=(8, 0))
        ttk.Label(labelframe_clean, text="* Use if input size is NOT a perfect multiple of Grid Size.", font=("Consolas", 8), foreground="#aaa", wraplength=250).pack(anchor="w", pady=(0, 10))

        # Palette
        ttk.Label(labelframe_clean, text="Max Colors (Denoise):").pack(anchor="w")
        self.var_colors = tk.IntVar(value=0)
        self.lbl_colors = ttk.Label(labelframe_clean, text="Full Colors")
        self.lbl_colors.pack(anchor="e")
        ttk.Scale(labelframe_clean, from_=0, to=128, variable=self.var_colors, command=lambda e: self.update_labels()).pack(fill="x")

        # SECTION 2: SEAMS
        labelframe_seam = ttk.Labelframe(controls, text="2. Seam Weaving", padding=10)
        labelframe_seam.pack(fill="x", pady=10)
        
        ttk.Label(labelframe_seam, text="Dither Overlap:").pack(anchor="w")
        self.var_strength = tk.DoubleVar(value=0.15)
        self.lbl_strength = ttk.Label(labelframe_seam, text="15%")
        self.lbl_strength.pack(anchor="e")
        ttk.Scale(labelframe_seam, from_=0.0, to=0.5, variable=self.var_strength, command=lambda e: self.update_labels()).pack(fill="x")

        # Buttons
        self.btn_process = ttk.Button(controls, text="✨ WEAVE & FIX ✨", command=self.process)
        self.btn_process.pack(fill="x", pady=20)
        ttk.Button(controls, text="💾 Save Result", command=self.save_img).pack(fill="x", pady=5)

        # === RIGHT PANEL ===
        preview_frame = ttk.Frame(main_split, padding=10)
        main_split.add(preview_frame)

        # Toolbar
        toolbar = ttk.Frame(preview_frame)
        toolbar.pack(fill="x", pady=(0, 5))
        ttk.Button(toolbar, text="Show Original", command=self.show_original).pack(side="left")
        ttk.Button(toolbar, text="Show Tiled (3x3)", command=self.show_result).pack(side="left", padx=5)
        
        ttk.Label(toolbar, text="|  Zoom:").pack(side="left", padx=10)
        ttk.Button(toolbar, text="-", width=3, command=lambda: self.change_zoom(-0.5)).pack(side="left")
        ttk.Button(toolbar, text="+", width=3, command=lambda: self.change_zoom(0.5)).pack(side="left")

        # Canvas
        self.canvas = tk.Canvas(preview_frame, bg="#101010", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Mouse Bindings
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)

    def update_labels(self):
        s = int(self.var_strength.get() * 100)
        self.lbl_strength.config(text=f"{s}%")
        c = int(self.var_colors.get())
        txt = f"{c} Colors" if c > 1 else "Full Colors (Off)"
        self.lbl_colors.config(text=txt)

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
        if not path: return
        self.img_path = path
        self.original_pil = Image.open(path).convert("RGBA")
        self.result_pil = None
        self.zoom_level = 1.0
        self.display_image = self.original_pil
        self.refresh_canvas()

    def process(self):
        if not self.original_pil: return
        try:
            # Inputs
            strength = self.var_strength.get()
            grid_res = int(self.var_grid.get())
            colors = int(self.var_colors.get())
            smart_mode = self.var_smart_grid.get()
            if colors < 2: colors = 0

            # Logic
            cleaned = core.process_pixel_art(
                self.original_pil, 
                strength=strength, 
                grid_res=grid_res, 
                max_colors=colors,
                smart_grid=smart_mode
            )
            
            # Create Tiled Preview
            self.result_pil = core.generate_tiled_preview(cleaned)
            self.single_result = cleaned # Store single tile for saving
            self.show_result()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))

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
        self.zoom_level = max(0.5, min(10.0, self.zoom_level + amount))
        self.refresh_canvas()

    def refresh_canvas(self):
        if not self.display_image: return
        
        # Nearest Neighbor for Zoom
        w, h = self.display_image.size
        nw, nh = int(w * self.zoom_level), int(h * self.zoom_level)
        
        resized = self.display_image.resize((nw, nh), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(resized) 
        
        self.canvas.delete("all")
        # Center image
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
        if not hasattr(self, 'single_result') or not self.single_result: 
            messagebox.showwarning("Warning", "Process image first!")
            return
        
        # Determine Filename
        base = os.path.splitext(self.img_path)[0]
        grid_res = int(self.var_grid.get())
        
        # If grid is active, append size (e.g., _64px). If not, just _fixed.
        suffix = f"_{grid_res}px" if grid_res > 0 else "_fixed"
        out_path = f"{base}{suffix}.png"
        
        self.single_result.save(out_path)
        messagebox.showinfo("Saved", f"Texture saved:\n{out_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PixelWeaverGUI(root)
    root.mainloop()
