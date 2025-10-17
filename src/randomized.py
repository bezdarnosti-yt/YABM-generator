from collections import OrderedDict
import numpy as np
import random

import utils

def randomized(image_matrix, palette_name, threshold_val=0.5):
    new_matrix = np.copy(image_matrix)
    rows, cols, depth = image_matrix.shape

    threshold_adjustment = (threshold_val - 0.5) * 1

    for y in range(rows):
        for x in range(cols):
            old_pixel = new_matrix[y, x]
            opr, opg, opb = old_pixel

            opr = utils.clamp(opr + random.gauss(0.0, 1.0 / 6.0) + threshold_adjustment)
            opg = utils.clamp(opg + random.gauss(0.0, 1.0 / 6.0) + threshold_adjustment)
            opb = utils.clamp(opb + random.gauss(0.0, 1.0 / 6.0) + threshold_adjustment)

            new_pixel = np.array(utils.closest_palette_color([opr, opg, opb], palette_name), dtype=float)
            new_matrix[y, x] = new_pixel
    return new_matrix

def block_randomized(image_matrix, palette_name, threshold_val=0.5):
    new_matrix = np.copy(image_matrix)
    rows, cols, depth = image_matrix.shape

    # Block sizes
    block_width, block_height = max(1, cols // 50), max(1, rows // 50)

    threshold_adjustment = (threshold_val - 0.5) * 1

    for by in range(0, rows, block_height):
        for bx in range(0, cols, block_width):
            # Determ real block end
            end_x = min(bx + block_width, cols)
            end_y = min(by + block_height, rows)
            actual_block_width = end_x - bx
            actual_block_height = end_y - by

            if actual_block_width == 0 or actual_block_height == 0:
                continue

            # Calculate average block color
            block = new_matrix[by:end_y, bx:end_x, :]
            avg_color = np.mean(block, axis=(0, 1))

            # Generate one noise for all blocks
            ar = np.clip(avg_color[0] + random.gauss(0.0, 1.0 / 6.0) + threshold_adjustment, 0.0, 1.0)
            ag = np.clip(avg_color[1] + random.gauss(0.0, 1.0 / 6.0) + threshold_adjustment, 0.0, 1.0)
            ab = np.clip(avg_color[2] + random.gauss(0.0, 1.0 / 6.0) + threshold_adjustment, 0.0, 1.0)

            # Getting palette color for block
            block_color = utils.closest_palette_color([ar, ag, ab], palette_name)

            # Filling block with this color
            new_matrix[by:end_y, bx:end_x] = block_color

    return new_matrix

available_methods = OrderedDict([
    ('random', lambda im, pal, threshold=0.5: randomized(im, pal, threshold)),
    ('block_random', lambda im, pal, threshold=0.5: block_randomized(im, pal, threshold)),
])
