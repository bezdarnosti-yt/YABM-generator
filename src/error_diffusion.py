from collections import OrderedDict
import numpy as np

_diffusion_matrices_fast = {
    'floyd_steinberg': np.array([
        [0, 0, 7, 0, 0],
        [3, 5, 1, 0, 0],
        [0, 0, 0, 0, 0]
    ], dtype=np.float32) / 16.0,

    'atkinson': np.array([
        [0, 0, 1, 1, 0],
        [1, 1, 1, 0, 0],
        [0, 1, 0, 0, 0]
    ], dtype=np.float32) / 8.0,

    'burkes': np.array([
        [0, 0, 8, 4, 0],
        [2, 4, 8, 4, 2],
        [0, 0, 0, 0, 0]
    ], dtype=np.float32) / 32.0,

    'sierra_lite': np.array([
        [0, 0, 2, 0, 0],
        [1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0]
    ], dtype=np.float32) / 4.0,
}

class ErrorDiffusionOptimizer:
    def __init__(self):
        self.palette_cache = {}

    def get_palette_array(self, palette_name):
        if palette_name not in self.palette_cache:
            import palette
            self.palette_cache[palette_name] = np.array(palette.palettes[palette_name], dtype=np.float32)
        return self.palette_cache[palette_name]


_diffusion_optimizer = ErrorDiffusionOptimizer()

def closest_color_fast(pixel, palette_array):
    distances = np.sum((palette_array - pixel) ** 2, axis=1)
    return palette_array[np.argmin(distances)]

def _error_diffusion(image_matrix, palette_name, diffusion_matrix, threshold=0.5):
    new_matrix = np.copy(image_matrix)
    rows, cols, _ = image_matrix.shape

    # Precompute
    palette_array = _diffusion_optimizer.get_palette_array(palette_name)

    center_x = diffusion_matrix.shape[1] // 2

    for y in range(rows):
        for x in range(cols):
            old_pixel = new_matrix[y, x]

            # Apply threshold as bias
            adjusted_pixel = old_pixel + (threshold - 0.5) * 0.5
            adjusted_pixel = np.clip(adjusted_pixel, 0.0, 1.0)

            new_pixel = closest_color_fast(adjusted_pixel, palette_array)

            # Updating pixel
            new_matrix[y, x] = new_pixel
            quant_error = old_pixel - new_pixel

            for dy in range(diffusion_matrix.shape[0]):
                for dx in range(diffusion_matrix.shape[1]):
                    coeff = diffusion_matrix[dy, dx]
                    if coeff != 0:
                        ny = y + dy
                        nx = x + dx - center_x
                        if 0 <= ny < rows and 0 <= nx < cols:
                            new_matrix[ny, nx] += quant_error * coeff

    return new_matrix

_method_names_fast = ['floyd_steinberg', 'atkinson', 'burkes', 'sierra_lite']

def _create_method(matrix_name):
    """Create error diffusion method for given matrix name."""
    def method(image_matrix, palette_name, threshold=0.5):
        return _error_diffusion(image_matrix, palette_name, _diffusion_matrices_fast[matrix_name], threshold)
    return method

available_methods = OrderedDict(
    (name, _create_method(name)) for name in _method_names_fast
)
