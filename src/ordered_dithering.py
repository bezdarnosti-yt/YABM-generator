from collections import OrderedDict
import numpy as np

import utils

_diffusion_matrices = {
    'bayer4x4': np.array([
        [ 0.05882353,  0.52941176,  0.17647059,  0.64705882],
        [ 0.76470588,  0.29411765,  0.88235294,  0.41176471],
        [ 0.23529412,  0.70588235,  0.11764706,  0.58823529],
        [ 0.94117647,  0.47058824,  0.82352941,  0.35294118]
    ], dtype=np.float32),
    'bayer8x8': np.array([
        [ 0.        ,  0.73846154,  0.18461538,  0.92307692,  0.04615385,  0.78461538,  0.23076923,  0.96923077],
        [ 0.49230769,  0.24615385,  0.67692308,  0.43076923,  0.53846154,  0.29230769,  0.72307692,  0.47692308],
        [ 0.12307692,  0.86153846,  0.06153846,  0.8       ,  0.16923077,  0.90769231,  0.10769231,  0.84615385],
        [ 0.61538462,  0.36923077,  0.55384615,  0.30769231,  0.66153846,  0.41538462,  0.6       ,  0.35384615],
        [ 0.03076923,  0.76923077,  0.21538462,  0.95384615,  0.01538462,  0.75384615,  0.2       ,  0.93846154],
        [ 0.52307692,  0.27692308,  0.70769231,  0.46153846,  0.50769231,  0.26153846,  0.69230769,  0.44615385],
        [ 0.15384615,  0.89230769,  0.09230769,  0.83076923,  0.13846154,  0.87692308,  0.07692308,  0.81538462],
        [ 0.64615385,  0.4       ,  0.58461538,  0.33846154,  0.63076923,  0.38461538,  0.56923077,  0.32307692]
    ], dtype=np.float32),
    'cluster4x4': np.array([
        [ 0.8       ,  0.33333333,  0.4       ,  0.86666667],
        [ 0.26666667,  0.        ,  0.06666667,  0.46666667],
        [ 0.73333333,  0.2       ,  0.13333333,  0.53333333],
        [ 1.        ,  0.66666667,  0.6       ,  0.93333333]
    ], dtype=np.float32),
    'cluster8x8': np.array([
        [ 0.375     ,  0.15625   ,  0.1875    ,  0.40625   ,  0.546875  ,  0.734375  ,  0.765625  ,  0.578125  ],
        [ 0.125     ,  0.        ,  0.03125   ,  0.21875   ,  0.703125  ,  0.921875  ,  0.953125  ,  0.796875  ],
        [ 0.34375   ,  0.09375   ,  0.0625    ,  0.25      ,  0.671875  ,  0.890625  ,  0.984375  ,  0.828125  ],
        [ 0.46875   ,  0.3125    ,  0.28125   ,  0.4375    ,  0.515625  ,  0.640625  ,  0.859375  ,  0.609375  ],
        [ 0.53125   ,  0.71875   ,  0.75      ,  0.5625    ,  0.390625  ,  0.171875  ,  0.203125  ,  0.421875  ],
        [ 0.6875    ,  0.90625   ,  0.9375    ,  0.78125   ,  0.140625  ,  0.015625  ,  0.046875  ,  0.234375  ],
        [ 0.65625   ,  0.875     ,  0.96875   ,  0.8125    ,  0.359375  ,  0.109375  ,  0.078125  ,  0.265625  ],
        [ 0.5       ,  0.625     ,  0.84375   ,  0.59375   ,  0.484375  ,  0.328125  ,  0.296875  ,  0.453125  ]
    ], dtype=np.float32),
}

def _ordered_dither(image_matrix, palette_name, map_to_use, threshold=0.5):
    rows, cols, depth = image_matrix.shape
    map_size = map_to_use.shape[0]

    # Creating noise matrix
    threshold_adjustment = (threshold - 0.5) * 0.5

    # Creating index matrix
    x_indices = np.arange(cols) % map_size
    y_indices = np.arange(rows) % map_size

    # Getting value of dither map for every pixel
    adjusted_map_values = map_to_use[y_indices[:, np.newaxis], x_indices[np.newaxis, :]]
    adjusted_map_values = adjusted_map_values + threshold_adjustment

    # Expand for 3 color channels and apply noise
    adjusted_map_values_3d = adjusted_map_values[:, :, np.newaxis]
    noisy_image = image_matrix + adjusted_map_values_3d

    # Apply palette for image
    new_matrix = utils.closest_palette_color(noisy_image, palette_name)

    return new_matrix

_method_names = [
        'bayer4x4', 'bayer8x8',
        'cluster4x4', 'cluster8x8',
]

def _create_method(matrix_name):
    """Create ordered dithering method for given matrix name."""
    def method(image_matrix, palette_name, threshold=0.5):
        return _ordered_dither(image_matrix, palette_name, _diffusion_matrices[matrix_name], threshold)
    return method

available_methods = OrderedDict(
    (name, _create_method(name)) for name in _method_names
)
