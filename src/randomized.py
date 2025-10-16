from collections import OrderedDict
import numpy
import random

import utils


def randomized(image_matrix, palette_name, threshold_val=0.5):
    new_matrix = numpy.copy(image_matrix)
    cols, rows, depth = image_matrix.shape

    threshold_adjustment = (threshold_val - 0.5) * 1

    for y in range(rows):
        for x in range(cols):
            old_pixel = numpy.array(new_matrix[x][y], dtype=float)
            opr, opg, opb = old_pixel

            opr = utils.clamp(opr + random.gauss(0.0, 1. / 6.) + threshold_adjustment)
            opg = utils.clamp(opg + random.gauss(0.0, 1. / 6.) + threshold_adjustment)
            opb = utils.clamp(opb + random.gauss(0.0, 1. / 6.) + threshold_adjustment)

            new_pixel = numpy.array(utils.closest_palette_color([opr, opg, opb], palette_name), dtype=float)
            new_matrix[x][y] = new_pixel
    return new_matrix


def block_randomized(image_matrix, palette_name, threshold_val=0.5):
    new_matrix = numpy.copy(image_matrix)
    cols, rows, depth = image_matrix.shape

    block_width, block_height = (max(1, cols / 50), max(1, rows / 50))
    block_width = int(block_width)
    block_height = int(block_height)

    threshold_adjustment = (threshold_val - 0.5) * 1

    for by in range(0, rows, block_height):
        for bx in range(0, cols, block_width):
            block = new_matrix[bx:bx + block_width, by:by + block_height, :]
            avg_color = numpy.sum(block, axis=(0, 1)) / (block_width * block_height)

            for y in range(block_height):
                for x in range(block_width):
                    ar, ag, ab = avg_color
                    ar = utils.clamp(ar + random.gauss(0.0, 1. / 6.) + threshold_adjustment)
                    ag = utils.clamp(ag + random.gauss(0.0, 1. / 6.) + threshold_adjustment)
                    ab = utils.clamp(ab + random.gauss(0.0, 1. / 6.) + threshold_adjustment)

                    new_pixel = numpy.array(utils.closest_palette_color([ar, ag, ab], palette_name), dtype=float)
                    new_matrix[bx + x][by + y] = new_pixel
    return new_matrix

_available_methods = OrderedDict([
    ('random', lambda im, pal, threshold=0.5: randomized(im, pal, threshold)),
    ('block_random', lambda im, pal, threshold=0.5: block_randomized(im, pal, threshold)),
])
