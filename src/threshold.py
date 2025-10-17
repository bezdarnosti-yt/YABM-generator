from collections import OrderedDict
import numpy

import utils

def threshold(image_matrix, palette_name, threshold_val=0.5):
    new_matrix = numpy.copy(image_matrix)
    cols, rows, depth = image_matrix.shape

    threshold_value = threshold_val / 2

    for y in range(rows):
        for x in range(cols):
            old_pixel = numpy.array(new_matrix[x][y], dtype=float)

            if len(old_pixel) == 3:
                brightness = 0.299 * old_pixel[0] + 0.587 * old_pixel[1] + 0.114 * old_pixel[2]
            else:
                brightness = old_pixel[0] if len(old_pixel) == 1 else numpy.mean(old_pixel)

            if brightness > threshold_value:
                new_color = [255.0, 255.0, 255.0]
            else:
                new_color = [0.0, 0.0, 0.0]

            new_pixel = numpy.array(utils.closest_palette_color(new_color, palette_name), dtype=float)
            new_matrix[x][y] = new_pixel

    return new_matrix

available_methods = OrderedDict([
    ('threshold', lambda im, pal, threshold_val=0.5: threshold(im, pal, threshold_val)),
])
