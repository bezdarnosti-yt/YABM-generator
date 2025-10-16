from PIL import Image
import math, numpy, sys

from PyQt6.QtGui import QImage, QPixmap

import palette

DEBUGMODE = False

def open_image(image_filename):
    return Image.open(image_filename).convert('RGB')


def pil2numpy(image):
    matrix = numpy.asarray(image, dtype=float)
    return matrix/255. 


def numpy2pil(matrix):
    image = Image.fromarray(numpy.uint8(matrix*255))
    return image


def clamp(val):
    return max(0.0, min(1.0, val))


def closest_palette_color(value, palette_name, bit_depth=1):
    if DEBUGMODE:
        print('\tvalue = {value}')

    # compute distance to colors in palette
    # TODO make this naive method more sophisticated
    min_dist = 10000.
    ci_use = -1
    for ci, color in enumerate(palette.palettes[palette_name]):
        pr, pg, pb = color
        vr, vg, vb = value
        dist = math.sqrt((vr-pr)*(vr-pr)+(vg-pg)*(vg-pg)+(vb-pb)*(vb-pb))

        if DEBUGMODE:
            print('\tcolor = {color}')
            print('\tdist = {dist}, min_dist = {min_dist}')

        if dist < min_dist:
            ci_use = ci
            min_dist = dist

    if ci == -1:
        return [0.0, 0.0, 0.0]
    else:
        return palette.palettes[palette_name][ci_use]


def pil_to_pixmap(pil_image):
    if pil_image.mode == '1':
        pil_image = pil_image.convert('L')

    if pil_image.mode == 'L':
        # Grayscale
        data = pil_image.tobytes('raw', 'L')
        q_image = QImage(data, pil_image.size[0], pil_image.size[1],
                         pil_image.size[0], QImage.Format.Format_Grayscale8)
    elif pil_image.mode == 'RGB':
        # RGB
        data = pil_image.tobytes('raw', 'RGB')
        q_image = QImage(data, pil_image.size[0], pil_image.size[1],
                         pil_image.size[0] * 3, QImage.Format.Format_RGB888)
    elif pil_image.mode == 'RGBA':
        # RGBA
        data = pil_image.tobytes('raw', 'RGBA')
        q_image = QImage(data, pil_image.size[0], pil_image.size[1],
                         pil_image.size[0] * 4, QImage.Format.Format_RGBA8888)
    else:
        pil_image = pil_image.convert('RGB')
        data = pil_image.tobytes('raw', 'RGB')
        q_image = QImage(data, pil_image.size[0], pil_image.size[1],
                         pil_image.size[0] * 3, QImage.Format.Format_RGB888)

    return QPixmap.fromImage(q_image)
