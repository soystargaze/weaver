import numpy as np
from PIL import Image

def enforce_pixel_grid(img, target_res, smart_mode=False):
    """
    Downscales and Upscales to force a perfect pixel grid.
    """
    if target_res <= 0: return img
    
    # Assume square tiles for simplicity
    target_size = (target_res, target_res)
    
    if not smart_mode:
        # Standard Method: Fast and crisp for integer scaling (e.g., 512 -> 64)
        small = img.resize(target_size, Image.NEAREST)
    else:
        # Smart Method: High-quality average for non-integers (e.g., 500 -> 64)
        # 1. Soft downscale to average pixels (Lanczos)
        small_blurry = img.resize(target_size, Image.LANCZOS)
        
        # 2. Hard Snap: Quantize immediately to remove blur but keep geometry
        # We use a generous palette (256) to snap shapes without destroying colors yet
        small = small_blurry.quantize(colors=256, method=2, dither=Image.NONE).convert("RGBA")

    # 3. Upscale back to original size using Nearest Neighbor (Hard Edges)
    clean = small.resize(img.size, Image.NEAREST)
    return clean

def clean_palette(img, max_colors=64):
    """
    Quantizes the image to a specific palette size to remove 
    AI compression noise.
    """
    if max_colors < 2: return img
    quantized = img.quantize(colors=max_colors, method=2, dither=Image.NONE)
    return quantized.convert("RGBA")

def weave_dithered(array, axis, strength):
    """
    Weaves edges using Stochastic Dithering (No Blur).
    """
    height, width, channels = array.shape
    target_dim = width if axis == 1 else height
    overlap = int(target_dim * strength)
    
    if overlap == 0: return array

    # Probability gradient
    linspace = np.linspace(0, 1, overlap)
    # Random noise
    noise = np.random.rand(overlap)
    
    # Binary Mask (True/False)
    mask_binary = (noise > linspace).astype(np.float32)

    if axis == 1: # Horizontal
        mask = mask_binary.reshape(1, overlap, 1)
        start_slice = array[:, :overlap, :] 
        end_slice = array[:, -overlap:, :]  
        
        woven = (start_slice * mask) + (end_slice * (1.0 - mask))
        array[:, :overlap, :] = woven
        return array[:, :-overlap, :]
        
    else: # Vertical
        mask = mask_binary.reshape(overlap, 1, 1)
        start_slice = array[:overlap, :, :]
        end_slice = array[-overlap:, :, :]
        
        woven = (start_slice * mask) + (end_slice * (1.0 - mask))
        array[:overlap, :, :] = woven
        return array[:-overlap, :, :]

def process_pixel_art(img, strength=0.15, grid_res=0, max_colors=0, smart_grid=False):
    """
    Main pipeline: Grid Fix -> Color Clean -> Seam Weaving
    """
    processed = img.copy()

    # 1. Enforce Pixel Grid (Mixel Fixer)
    if grid_res > 0:
        processed = enforce_pixel_grid(processed, grid_res, smart_mode=smart_grid)

    # 2. Clean Palette (Remove JPEG noise)
    if max_colors > 0:
        processed = clean_palette(processed, max_colors)

    # 3. Weave Seams (Dithering)
    if strength > 0:
        img_arr = np.array(processed).astype(np.float32)
        img_arr = weave_dithered(img_arr, 1, strength) # X axis
        img_arr = weave_dithered(img_arr, 0, strength) # Y axis
        img_arr = np.clip(img_arr, 0, 255).astype(np.uint8)
        return Image.fromarray(img_arr)
    
    return processed

def generate_tiled_preview(img):
    """Generates a 3x3 grid for preview."""
    w, h = img.size
    tiled = Image.new("RGBA", (w * 3, h * 3))
    for i in range(3):
        for j in range(3):
            tiled.paste(img, (i * w, j * h))
    return tiled
