import numpy as np
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap
import palette
import math

class PaletteCache:
    def __init__(self):
        self._arrays = {}

    def get_palette_array(self, palette_name):
        if palette_name not in self._arrays:
            # Convert palette to numpy array
            self._arrays[palette_name] = np.array(palette.palettes[palette_name], dtype=np.float32)
        return self._arrays[palette_name]

_palette_cache = PaletteCache()

def open_image(image_filename):
    return Image.open(image_filename).convert('RGB')

def pil2numpy(image):
    return np.array(image, dtype=np.float32) / 255.0

def numpy2pil(matrix):
    return Image.fromarray((matrix * 255).astype(np.uint8))

def clamp(val):
    return max(0.0, min(1.0, val))

def closest_palette_color(value, palette_name):
    palette_array = _palette_cache.get_palette_array(palette_name)

    # If value - list [r, g, b], converting to numpy array
    if isinstance(value, list):
        value = np.array(value, dtype=np.float32)

    # If value - one pixel [r, g, b]
    if value.ndim == 1:
        distances = np.sqrt(np.sum((palette_array - value) ** 2, axis=1))
        min_idx = np.argmin(distances)

        return palette_array[min_idx].tolist()

    # If value - image (H, W, 3)
    elif value.ndim == 3:
        # Reshape for vector operations
        h, w, c = value.shape
        value_flat = value.reshape(-1, 3)

        # Determ path to all palette colors for all pixels
        distances = np.sqrt(np.sum((value_flat[:, np.newaxis, :] - palette_array[np.newaxis, :, :]) ** 2, axis=2))

        # Finding indexes of close colors
        min_indices = np.argmin(distances, axis=1)

        # Change pixels with close colors from palette
        result_flat = palette_array[min_indices]
        return result_flat.reshape(h, w, c)

    else:
        # Fallback to original logic
        min_dist = 10000.
        ci_use = -1
        colors = palette.palettes[palette_name]

        for ci, color in enumerate(colors):
            pr, pg, pb = color
            vr, vg, vb = value
            dist = math.sqrt((vr-pr)*(vr-pr)+(vg-pg)*(vg-pg)+(vb-pb)*(vb-pb))

            if dist < min_dist:
                ci_use = ci
                min_dist = dist

        if ci_use == -1:
            return [0.0, 0.0, 0.0]
        else:
            return colors[ci_use]

def pil_to_pixmap(pil_image):
    if pil_image.mode == '1':
        pil_image = pil_image.convert('L')

    if pil_image.mode == 'L':
        # Grayscale
        data = pil_image.tobytes('raw', 'L')
        q_image = QImage(data, pil_image.width, pil_image.height,
                         pil_image.width, QImage.Format.Format_Grayscale8)
    elif pil_image.mode == 'RGB':
        # RGB
        data = pil_image.tobytes('raw', 'RGB')
        q_image = QImage(data, pil_image.width, pil_image.height,
                         pil_image.width * 3, QImage.Format.Format_RGB888)
    elif pil_image.mode == 'RGBA':
        # RGBA
        data = pil_image.tobytes('raw', 'RGBA')
        q_image = QImage(data, pil_image.width, pil_image.height,
                         pil_image.width * 4, QImage.Format.Format_RGBA8888)
    else:
        # Fallback
        pil_image = pil_image.convert('RGB')
        data = pil_image.tobytes('raw', 'RGB')
        q_image = QImage(data, pil_image.width, pil_image.height,
                         pil_image.width * 3, QImage.Format.Format_RGB888)

    return QPixmap.fromImage(q_image)