# 👾 Pixel-Weaver
**The AI Pixel Art Fixer & Tiler**

AI generators (Midjourney, DALL-E) are notoriously bad at pixel art. They generate "mixels" (inconsistent pixel sizes), blurry edges, and non-tileable borders.

**Pixel-Weaver** is a Python tool that mathematically forces raw AI images into perfect, crisp pixel art assets ready for game development.

### ✨ Key Features

1.  **Mixel Fixer (Force Grid):**
    * Snaps blurry AI images to a strict grid (e.g., 64x64).
    * **Smart Sampling:** Handles irregular input sizes (e.g., 500px -> 64px) without distortion.
2.  **Stochastic Seam Weaving:**
    * Makes textures seamless using **dithering** instead of blur.
3.  **Palette Cleaner:**
    * Reduces JPEG noise to a clean, limited palette.
4.  **Smart Naming:**
    * Automatically saves files with their resolution (e.g., `fire_64px.png`).

### 📦 Installation

1.  Install Python 3.x.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### 🎮 How to Use

Run the interface:
```bash
python weaver_gui.py
