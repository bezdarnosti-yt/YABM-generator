from collections import OrderedDict
import numpy as np

import utils

_diffusion_matrices = {
    'bayer4x4': 1./17. * np.array([
        [ 1,  9,  3, 11],
        [13,  5, 15,  7],
        [ 4, 12,  2, 10],
        [16,  8, 14,  6]
    ]),
    'bayer8x8': 1./65. * np.array([
        [ 0, 48, 12, 60,  3, 51, 15, 63],
        [32, 16, 44, 28, 35, 19, 47, 31],
        [ 8, 56,  4, 52, 11, 59,  7, 55],
        [40, 24, 36, 20, 43, 27, 39, 23],
        [ 2, 50, 14, 62,  1, 49, 13, 61],
        [34, 18, 46, 30, 33, 17, 45, 29],
        [10, 58,  6, 54,  9, 57,  5, 53],
        [42, 26, 38, 22, 41, 25, 37, 21]
    ]),
    'cluster4x4': 1./15. * np.array([
        [12,  5,  6, 13],
        [ 4,  0,  1,  7],
        [11,  3,  2,  8],
        [15, 10,  9, 14]
    ]),
    'cluster8x8': 1./64. * np.array([
        [24, 10, 12, 26, 35, 47, 49, 37],
        [ 8,  0,  2, 14, 45, 59, 61, 51],
        [22,  6,  4, 16, 43, 57, 63, 53],
        [30, 20, 18, 28, 33, 41, 55, 39],
        [34, 46, 48, 36, 25, 11, 13, 27],
        [44, 58, 60, 50,  9,  1,  3, 15],
        [42, 56, 62, 52, 23,  7,  5, 17],
        [32, 40, 54, 38, 31, 21, 19, 29]
    ]),
}

def _ordered_dither(image_matrix, palette_name, map_to_use, threshold=0.5):
    rows, cols, depth = image_matrix.shape
    map_size = map_to_use.shape[0]

    # Creating noise matrix
    threshold_adjustment = (threshold - 0.5) * 2

    # Creating index matrix
    x_indices = np.arange(cols) % map_size
    y_indices = np.arange(rows) % map_size

    # Getting value of dither map for every pixel
    adjusted_map_values = map_to_use[y_indices[:, np.newaxis], x_indices[np.newaxis, :]]
    adjusted_map_values = adjusted_map_values + threshold_adjustment * 0.5

    # Expand for 3 color channels and apply noise
    adjusted_map_values_3d = adjusted_map_values[:, :, np.newaxis]
    noisy_image = image_matrix + image_matrix * adjusted_map_values_3d

    # Apply palette for image
    new_matrix = utils.closest_palette_color(noisy_image, palette_name)

    return new_matrix

_method_names = [
        'bayer4x4', 'bayer8x8',
        'cluster4x4', 'cluster8x8',
]

available_methods = OrderedDict(
    [(mn, (lambda name: (lambda im, pal, threshold=0.5: _ordered_dither(im, pal, _diffusion_matrices[name], threshold)))(mn)) for mn in _method_names]
)
