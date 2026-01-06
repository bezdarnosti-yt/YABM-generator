from collections import OrderedDict
import json, os

class PaletteManager:
    def __init__(self):
        self.palettes = OrderedDict()
        self.available_palettes = []
        self._initialize_palettes()
    
    def _initialize_palettes(self):
        cache_path = os.path.join(os.path.dirname(__file__), '..', 'palettes.cache')
        if os.access(cache_path, os.R_OK):
            # check its mtime
            me = os.path.realpath(__file__)
            my_mtime = os.stat(me).st_mtime
            cache_mtime = os.stat(cache_path).st_mtime
            
            if my_mtime > cache_mtime:
                # rebuild cache
                self._build_palettes()
            else:
                # read in the cache
                with open(cache_path, 'r') as pf:
                    self.palettes = json.load(pf, object_pairs_hook=OrderedDict)
                self.available_palettes = list(self.palettes.keys())
        else:
            self._build_palettes()
    
    def _build_palettes(self):
        print('building palettes')
        self._build_grayscale_palettes()
        self._build_cga_palettes()
        self._build_ega_palettes()
        self._build_websafe_palettes()
        self._build_c64_palettes()
        
        cache_path = os.path.join(os.path.dirname(__file__), '..', 'palettes.cache')
        with open(cache_path, 'w') as val:
            json.dump(self.palettes, val)
        
        self.available_palettes = list(self.palettes.keys())

    def _build_c64_palettes(self):
        print('building C64 palette')
        palette = [
                [  0.0,           0.0,           0.0        ],
                [254.999999878, 254.999999878, 254.999999878],
                [103.681836072,  55.445357742,  43.038096345],
                [111.932673473, 163.520631667, 177.928819803],
                [111.399725075,  60.720543693, 133.643433983],
                [ 88.102223525, 140.581101312,  67.050415368],
                [ 52.769271594,  40.296416104, 121.446211753],
                [183.892638117, 198.676829993, 110.585717385],
                [111.399725075,  79.245328562,  37.169652483],
                [ 66.932804788,  57.383702891,   0.0        ],
                [153.690586380, 102.553762644,  89.111118307],
                [ 67.999561813,  67.999561813,  67.999561813],
                [107.797780127, 107.797780127, 107.797780127],
                [154.244479632, 209.771445903, 131.584994128],
                [107.797780127,  94.106015515, 180.927622164],
                [149.480882981, 149.480882981, 149.480882981],
        ]
        self.palettes['c64'] = [[c/255. for c in color] for color in palette]

    def _build_websafe_palettes(self):
        print('building websafe palette')
        palette = []
        for r in range(6):
            for g in range(6):
                for b in range(6):
                    palette.append([r/5.0, g/5.0, b/5.0])
        self.palettes['websafe'] = palette

    def _build_grayscale_palettes(self):
        print('building grayscale palettes')
        for bit_depth in range(1, 8):
            levels = 2**bit_depth - 1
            pname = '{}bit_gray'.format(bit_depth)
            palette = [ [0.0, 0.0, 0.0] ]
            for l in range(levels):
                val = float(l+1) / levels
                palette.append([val, val, val])
            self.palettes[pname] = palette

    def _build_cga_palettes(self):
        print('building cga palettes')
        low = []
        off_on = (0.0, 2./3.)
        for r in off_on:
            for g in off_on:
                for b in off_on:
                    low.append([r, g, b])
        low[6][1] /= 2.

        high = []
        off_on = (1./3., 1.0)
        for r in off_on:
            for g in off_on:
                for b in off_on:
                    high.append([r, g, b])

        self.palettes['cga_mode4_1'] = [ low[0], low[3], low[5], low[7] ]
        self.palettes['cga_mode4_2'] = [ low[0], low[2], low[4], low[6] ]
        self.palettes['cga_mode4_1_high'] = [ low[0], high[3], high[5], high[7] ]
        self.palettes['cga_mode4_2_high'] = [ low[0], high[2], high[4], high[6] ]
        self.palettes['cga_mode5'] = [ low[0], low[3], low[4], low[7] ]
        self.palettes['cga_mode5_high'] = [ low[0], high[3], high[4], high[7] ]

    def _build_ega_palettes(self):
        print('building ega palettes')
        low = []
        off_on = (0.0, 2./3.)
        for r in off_on:
            for g in off_on:
                for b in off_on:
                    low.append([r, g, b])
        low[6][1] /= 2.

        high = []
        off_on = (1./3., 1.0)
        for r in off_on:
            for g in off_on:
                for b in off_on:
                    high.append([r, g, b])

        self.palettes['ega_default'] = low + high

# Create global instance for backward compatibility
_palette_manager = PaletteManager()
palettes = _palette_manager.palettes
available_palettes = _palette_manager.available_palettes
