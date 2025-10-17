import os
import sys
import webbrowser
from collections import OrderedDict

from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGroupBox,
                             QFileDialog, QSlider, QComboBox)
from PyQt6.QtCore import Qt
import palette
import utils

import error_diffusion
import ordered_dithering
import randomized
import threshold

available_methods = OrderedDict()

available_methods.update(threshold.available_methods)
available_methods.update(randomized.available_methods)
available_methods.update(ordered_dithering.available_methods)
available_methods.update(error_diffusion.available_methods)

# noinspection PyAttributeOutsideInit
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YABM Generator")
        self.setGeometry(100, 100, 1280, 720)

        # Settings
        self.dither_method = 'bayer4x4'
        self.palette_method = '1bit_gray'
        self.index = 0

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal layout
        main_layout = QHBoxLayout(central_widget)

        # Left panel with buttons etc
        left_panel = self.create_left_panel()

        # Right panel with image/video
        right_panel = self.create_right_panel()

        # Adding panels in main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 3)

        self.load_image(True)

    def create_left_panel(self):
        # Creating group for left panel
        left_group = QGroupBox("Controls")
        layout = QVBoxLayout()

        # Greet text
        text_layout = QHBoxLayout()
        greet_label = QLabel("Yet Another Bitmap Generator")
        greet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_layout.addWidget(greet_label)
        layout.addLayout(text_layout)

        # 1 row
        row2_layout = QHBoxLayout()
        self.load_image_btn = QPushButton("Load Image")
        self.load_video_btn = QPushButton("Load Video")

        self.load_image_btn.clicked.connect(self.load_image)
        self.load_video_btn.clicked.connect(self.load_video)

        row2_layout.addWidget(self.load_image_btn)
        row2_layout.addWidget(self.load_video_btn)
        layout.addLayout(row2_layout)

        # 2 row
        size_layout = QVBoxLayout()
        size_label = QLabel("Size:")
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(10)
        self.size_slider.setMaximum(100)
        self.size_slider.setValue(50)
        self.size_slider.valueChanged.connect(self.on_size_changed)

        self.size_value_label = QLabel("50")
        self.size_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_value_label)
        layout.addLayout(size_layout)

        # 3 row
        threshold_layout = QVBoxLayout()
        threshold_label = QLabel("Threshold:")
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(50)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)

        self.threshold_value_label = QLabel("50")
        self.threshold_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value_label)
        layout.addLayout(threshold_layout)

        # 4 row
        dither_layout = QVBoxLayout()
        dither_label = QLabel("Dithering method:")
        self.dither_combo = QComboBox()
        self.dither_combo.addItems(available_methods)
        self.dither_combo.setCurrentText(self.dither_method)
        self.dither_combo.currentTextChanged.connect(self.on_dither_changed)

        dither_layout.addWidget(dither_label)
        dither_layout.addWidget(self.dither_combo)
        layout.addLayout(dither_layout)

        # 5 row
        palete_layout = QVBoxLayout()
        palete_label = QLabel("Palette:")
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(palette.available_palettes)
        self.palette_combo.setCurrentText(self.palette_method)
        self.palette_combo.currentTextChanged.connect(self.on_palette_changed)

        palete_layout.addWidget(palete_label)
        palete_layout.addWidget(self.palette_combo)
        layout.addLayout(palete_layout)

        # 6 row
        self.github_btn = QPushButton("GitHub Repository")
        self.github_btn.clicked.connect(self.open_github)
        layout.addWidget(self.github_btn)

        layout.addStretch()
        left_group.setLayout(layout)
        return left_group


    def create_right_panel(self):
        # Creating group for right panel
        right_group = QGroupBox("Preview")
        layout = QVBoxLayout()

        # Creating label for image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        self.image_label.setText("No Image/Video loaded")

        layout.addWidget(self.image_label)

        buttons_row = QHBoxLayout()
        self.export_one_btn = QPushButton("Export Current Image")
        self.next_btn = QPushButton("Next")
        self.next_save_btn = QPushButton("Next + Save")

        self.export_one_btn.clicked.connect(self.export_one)
        self.next_btn.clicked.connect(self.next)
        self.next_save_btn.clicked.connect(self.next_save)

        buttons_row.addWidget(self.export_one_btn)
        buttons_row.addWidget(self.next_btn)
        buttons_row.addWidget(self.next_save_btn)
        layout.addLayout(buttons_row)

        right_group.setLayout(layout)
        return right_group

    # Signals
    def load_image(self, test=False):
        if test:
            self.file_path = "test.jpg"
            self.file_name = self.file_path
        else:
            result = QFileDialog.getOpenFileName(
                self,
                "Select Image",
                "",
                "Image Files (*.jpg *.jpeg *.png *.bmp)",
                options=QFileDialog.Option.DontUseNativeDialog
            )
            self.file_path = result[0]
            self.file_name = self.file_path.fileName()
            self.index = 0

        if self.file_path and self.file_path != '':
            self.process_image()

    def load_video(self):
        pass

    def process_image(self):
        image = utils.open_image(self.file_path)

        scale_percent = self.size_slider.value()

        scale_factor = scale_percent / 100.0
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)
        image = image.resize((new_width, new_height), Image.Resampling.NEAREST)

        image_matrix = utils.pil2numpy(image)

        threshold_value = self.threshold_slider.value() / 100.0

        dither_matrix = available_methods[self.dither_method](image_matrix, self.palette_method, threshold_value)

        dither_image = utils.numpy2pil(dither_matrix)
        qt_pixmap = utils.pil_to_pixmap(dither_image)
        self.current_pixmap = qt_pixmap
        self.scale_image()

    def scale_image(self):
        if hasattr(self, 'current_pixmap') and self.current_pixmap:
            scaled_pixmap = self.current_pixmap.scaled(
                self.image_label.width() - 20,
                self.image_label.height() - 20,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def on_size_changed(self, value):
        self.size_value_label.setText(str(value))
        self.process_image()

    def on_threshold_changed(self, value):
        self.threshold_value_label.setText(str(value))
        self.process_image()

    def on_dither_changed(self, method):
        self.dither_method = method
        self.process_image()

    def on_palette_changed(self, value):
        self.palette_method = value
        self.process_image()

    def open_github(self):
        github_url = "https://github.com/bezdarnosti-yt/espRAT"
        webbrowser.open(github_url)

    def next(self):
        pass

    def export_one(self):
        if not hasattr(self, 'current_pixmap') or self.current_pixmap.isNull():
            return

        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        results_dir = f"{base_name}_results"
        os.makedirs(results_dir, exist_ok=True)

        filename = f"{results_dir}/result_{self.index:04d}.jpg"

        self.current_pixmap.save(filename)
        self.index += 1

    def next_save(self):
        pass


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())