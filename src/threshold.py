from collections import OrderedDict
import numpy as np

import utils

def threshold(image_matrix, palette_name, threshold_val=0.5):
    # Calculate brightness for all pixels
    if image_matrix.shape[2] == 3:  # RGB
        brightness = (0.299 * image_matrix[:, :, 0] +
                      0.587 * image_matrix[:, :, 1] +
                      0.114 * image_matrix[:, :, 2])
    else:  # Grayscale etc
        brightness = np.mean(image_matrix, axis=2)

    # Creating binary image
    binary_mask = brightness > threshold_val

    # Creating bw image
    white_black_image = np.zeros_like(image_matrix)
    white_black_image[binary_mask] = [1.0, 1.0, 1.0]  # White
    white_black_image[~binary_mask] = [0.0, 0.0, 0.0]  # Black

    # Apply palette to image
    new_matrix = utils.closest_palette_color(white_black_image, palette_name)

    return new_matrix

available_methods = OrderedDict([
    ('threshold', lambda im, pal, threshold_val=0.5: threshold(im, pal, threshold_val)),
])
