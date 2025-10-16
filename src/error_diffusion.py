from collections import OrderedDict
import numpy

import utils

_diffusion_matrices = {
        'floyd_steinberg' : numpy.array([
            [7./16],
            [3./16,5./16,1./16]
        ], dtype=object),
        'jajuni' : numpy.array([
            [7./48,5./48],
            [1./16,5./48,7./48,5./48,1./16],
            [1./48,1./16,5./48,1./16,1./48]
        ], dtype=object),
        'fan' : numpy.array([
            [7./16],
            [1./16,3./16,5./16,0.,0.]
        ], dtype=object),
        'stucki' : numpy.array([
            [4./21,2./21],
            [1./21,2./21,4./21,2./21,1./21],
            [1./42,1./21,2./21,1./21,1./42]
        ], dtype=object),
        'burkes' : numpy.array([
            [.25,.125],
            [.0625,.125,.25,.125,.0625]
        ], dtype=object),
        'sierra' : numpy.array([
            [5./32,3./32],
            [1./16,1./8,5./32,1./8,1./16],
            [1./16,3./32,1./16]
        ], dtype=object),
        'two_row_sierra' : numpy.array([
            [1./4,3./16],
            [1./16,1./8,3./16,1./8,1./16]
        ], dtype=object),
        'sierra_lite' : numpy.array([
            [0.5],
            [0.25,0.25,0]
        ], dtype=object),
        'atkinson' : numpy.array([
            [0.125,0.125],
            [0.125,0.125,0.125],
            [0.125]
        ], dtype=object)
}

def _error_diffusion(image_matrix, palette_name, diffusion_matrix, threshold=0.5):
    new_matrix = numpy.copy(image_matrix)
    cols, rows, depth = image_matrix.shape
    for y in range(rows):
        for x in range(cols):
            # calculate the new pixel value
            old_pixel = numpy.array(new_matrix[x][y], dtype=float)
            if threshold != 0.5:
                threshold_value = threshold * 255
                adjusted_pixel = old_pixel * (threshold * 2)
            else:
                adjusted_pixel = old_pixel

            new_pixel = numpy.array(utils.closest_palette_color(adjusted_pixel, palette_name), dtype=float)
            # replace the old pixel with the new value, and quantify the error
            new_matrix[x][y] = new_pixel
            quant_error = old_pixel - new_pixel

            forward_diffusion = diffusion_matrix[0]
            for ci, coeff in enumerate(forward_diffusion):
                if x + ci + 1 < cols:
                    new_matrix[x + (ci + 1)][y] += quant_error * coeff
            for di, downward_diffusion in enumerate(diffusion_matrix[1:]):
                if y + di + 1 < rows:
                    offset = len(downward_diffusion) / 2
                    offset = int(offset)
                    for ci, coeff in enumerate(downward_diffusion):
                        if 0 <= x + ci - offset < cols:
                            new_matrix[x + ci - offset][y + di + 1] += quant_error * coeff
    return new_matrix

_method_names = [
        'floyd_steinberg', 'jajuni', 'fan', 'stucki', 'burkes',
        'sierra', 'two_row_sierra', 'sierra_lite', 'atkinson'
]

_available_methods = OrderedDict(
    [(mn, (lambda name: (lambda im, pal, threshold=0.5: _error_diffusion(im, pal, _diffusion_matrices[name], threshold)))(mn)) for mn in _method_names]
)
