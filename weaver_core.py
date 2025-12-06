import numpy as np
from PIL import Image

def auto_detect_best_offset(img, target_res):
    """
    Algoritmo de detección simplificado. Devuelve enteros puros.
    """
    src_arr = np.array(img.convert("RGBA"))
    h, w, c = src_arr.shape
    
    block_w = w / target_res
    block_h = h / target_res
    
    # Búsqueda limitada al centro
    center_y, center_x = h // 2, w // 2
    sample_size = 128
    sy = center_y - 64
    sx = center_x - 64
    
    best_score = float('inf')
    best_off_x, best_off_y = 0, 0
    
    # Buscamos solo en un rango pequeño de píxeles enteros
    search_range = int(max(block_w, block_h)) + 1
    
    for oy in range(search_range):
        for ox in range(search_range):
            # Muestreamos unos pocos bloques
            score = 0
            count = 0
            for i in range(5):
                by = int((i * block_h) + oy + sy)
                bx = int((i * block_w) + ox + sx)
                if by+int(block_h) >= h or bx+int(block_w) >= w: continue
                
                block = src_arr[by:by+int(block_h), bx:bx+int(block_w)]
                if block.size == 0: continue
                
                pixels = block.reshape(-1, 4)
                # Desviación estándar: queremos bloques con colores uniformes (baja desviación)
                score += np.std(pixels, axis=0).mean()
                count += 1
            
            if count > 0:
                avg_score = score / count
                if avg_score < best_score:
                    best_score = avg_score
                    best_off_x, best_off_y = ox, oy
                    
    return best_off_x, best_off_y

def process_pixel_art(img, grid_res=100, max_colors=16, auto_align=False, progress_callback=None):
    """
    Pipeline v12: Manual/Auto Offset -> Hybrid Smart Color -> Palette
    """
    src_arr = np.array(img.convert("RGBA"))
    h, w, c = src_arr.shape
    
    # 1. ALINEACIÓN (Por defecto OFF para evitar borrones)
    off_x, off_y = 0, 0
    if auto_align:
        off_x, off_y = auto_detect_best_offset(img, grid_res)
    
    # 2. PROCESO DE BLOQUES
    block_w = w / grid_res
    block_h = h / grid_res
    
    dst_arr = np.zeros((grid_res, grid_res, 4), dtype=np.uint8)
    
    total_pixels = grid_res * grid_res
    processed_count = 0
    
    for y in range(grid_res):
        y_start = int((y * block_h) + off_y)
        y_end = int(((y + 1) * block_h) + off_y)
        y_start = max(0, min(y_start, h))
        y_end = max(0, min(y_end, h))
        
        if y_start >= y_end: 
            processed_count += grid_res
            continue

        for x in range(grid_res):
            x_start = int((x * block_w) + off_x)
            x_end = int(((x + 1) * block_w) + off_x)
            x_start = max(0, min(x_start, w))
            x_end = max(0, min(x_end, w))
            
            if x_start >= x_end:
                processed_count += 1
                continue

            # Bloque
            block = src_arr[y_start:y_end, x_start:x_end]
            pixels = block.reshape(-1, 4)
            
            if len(pixels) > 0:
                # A. FORMA (Votación Mayoritaria)
                dtype_void = np.dtype((np.void, pixels.dtype.itemsize * pixels.shape[1]))
                pixels_void = pixels.view(dtype_void)
                colors, counts = np.unique(pixels_void, return_counts=True)
                winner_idx = np.argmax(counts)
                
                winner_void_scalar = colors[winner_idx].reshape(1)
                shape_color = winner_void_scalar.view(pixels.dtype).reshape(-1)
                
                # B. COLOR (Promedio Inteligente)
                # Si usamos el promedio directo, mezclamos fondo y figura = sucio.
                # Solución: Promediamos solo los píxeles que NO son transparentes (si la forma es sólida)
                
                is_shape_transparent = shape_color[3] < 128
                
                if is_shape_transparent:
                    # Si la forma ganadora es transparente, dejamos transparente
                    dst_arr[y, x] = shape_color
                else:
                    # Si la forma ganadora es sólida, buscamos el "color medio real" del objeto
                    # Filtrar solo píxeles opacos del bloque para hacer el promedio
                    mask_opaque = pixels[:, 3] >= 128
                    opaque_pixels = pixels[mask_opaque]
                    
                    if len(opaque_pixels) > 0:
                        # Promedio de los opacos (recupera sombras y tonos medios)
                        avg_color = np.mean(opaque_pixels, axis=0).astype(np.uint8)
                        # Forzamos alfa 255 porque sabemos que es sólido
                        avg_color[3] = 255 
                        dst_arr[y, x] = avg_color
                    else:
                        # Fallback si algo raro pasa
                        dst_arr[y, x] = shape_color

            processed_count += 1
            
        if progress_callback:
            progress_callback( (processed_count / total_pixels) * 100 )

    tiny_img = Image.fromarray(dst_arr)
    
    # 3. PALETA FINAL (Aplicada sobre la imagen limpia)
    if max_colors > 1:
        # Extraemos paleta de la imagen limpia (tiny_img) para no coger ruido de la original
        # Pero a veces la tiny pierde matices. Probemos híbrido:
        # Generar paleta de la original suele ser mejor para captar fuego.
        palette_source = img.quantize(colors=max_colors, method=2, dither=Image.NONE)
        
        tiny_rgb = tiny_img.convert("RGB")
        final_tiny = tiny_rgb.quantize(palette=palette_source, dither=Image.NONE)
        return final_tiny.convert("RGBA")
        
    return tiny_img

def generate_tiled_preview(img):
    w, h = img.size
    preview_tile = img
    if w < 256:
        scale_factor = int(512 / w)
        preview_tile = img.resize((w*scale_factor, h*scale_factor), Image.NEAREST)
    w_p, h_p = preview_tile.size
    tiled = Image.new("RGBA", (w_p * 3, h_p * 3))
    for i in range(3):
        for j in range(3):
            tiled.paste(preview_tile, (i * w_p, j * h_p))
    return tiled
