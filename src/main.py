import os
import sys
import hashlib

# Fix Qt plugin conflict with OpenCV
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''

import webbrowser
import time
import threading
import gc
from collections import OrderedDict, namedtuple
from queue import Queue

# Cache key structure for better readability
CacheKey = namedtuple('CacheKey', ['image_hash', 'scale_percent', 'threshold_value', 'dither_method', 'palette_method'])

from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGroupBox,
                             QFileDialog, QSlider, QComboBox, QProgressDialog)
from PyQt6.QtCore import Qt, QTimer
import palette
import utils

import error_diffusion
import ordered_dithering
import randomized
import threshold

import cv2

class VideoLoader:
    def __init__(self, cache_size=30):
        self.cache_size = cache_size
        self.frame_cache = OrderedDict()
        self.load_queue = Queue()
        self.loader_thread = None
        self.stop_loading = False
        self._lock = threading.Lock()

    def start_loading(self, video_path):
        self.stop_loading = True
        if self.loader_thread and self.loader_thread.is_alive():
            try:
                self.loader_thread.join(timeout=1.0)
            except Exception as e:
                print(f"Error stopping loader thread: {e}")

        self.stop_loading = False
        self.frame_cache.clear()
        try:
            self.loader_thread = threading.Thread(target=self._load_frames, args=(video_path,))
            self.loader_thread.daemon = True
            self.loader_thread.start()
        except Exception as e:
            print(f"Error starting loader thread: {e}")
            self.stop_loading = True

    def _load_frames(self, video_path):
        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"Error: Could not open video file: {video_path}")
                return
                
            frame_index = 0
            while not self.stop_loading and cap.isOpened():
                try:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    with self._lock:
                        if len(self.frame_cache) >= self.cache_size:
                            self.frame_cache.popitem(last=False)

                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        self.frame_cache[frame_index] = frame_rgb

                    frame_index += 1
                except Exception as e:
                    print(f"Error processing frame {frame_index}: {e}")
                    break
        except Exception as e:
            print(f"Error in video loading: {e}")
        finally:
            if cap:
                cap.release()

    def get_frame(self, frame_index):
        with self._lock:
            return self.frame_cache.get(frame_index, None)

    def cleanup(self):
        self.stop_loading = True
        with self._lock:
            self.frame_cache.clear()

class ImageProcessor:
    def __init__(self):
        self._cache = {}
        self._cache_keys = []
        self._max_cache_size = 20  # Cache limit
        self._lock = threading.Lock()

    @staticmethod
    def _get_cache_key(image_data, scale_percent, threshold_value, dither_method, palette_method):
        # Creating key for cache from args
        if hasattr(image_data, 'tobytes'):
            # For PIL Image - use SHA256 for secure hashing
            image_hash = hashlib.sha256(image_data.tobytes()).hexdigest()[:16]
        else:
            # etc
            image_hash = hashlib.sha256(str(image_data).encode()).hexdigest()[:16]

        return CacheKey(image_hash, scale_percent, threshold_value, dither_method, palette_method)

    def process_frame(self, image, scale_percent, threshold_value, dither_method, palette_method):
        try:
            cache_key = self._get_cache_key(image, scale_percent, threshold_value, dither_method, palette_method)

            with self._lock:
                if cache_key in self._cache:
                    # Updating order of use
                    self._cache_keys.remove(cache_key)
                    self._cache_keys.append(cache_key)
                    return self._cache[cache_key]

            # If not in cache
            scale_factor = scale_percent / 100.0
            new_width = int(image.width * scale_factor)
            new_height = int(image.height * scale_factor)
            resized_image = image.resize((new_width, new_height), Image.Resampling.NEAREST)

            image_matrix = utils.pil2numpy(resized_image)
            dither_matrix = available_methods[dither_method](image_matrix, palette_method, threshold_value)
            dither_image = utils.numpy2pil(dither_matrix)
            qt_pixmap = utils.pil_to_pixmap(dither_image)

            with self._lock:
                # Adding to cache
                self._cache[cache_key] = qt_pixmap
                self._cache_keys.append(cache_key)

                # Clear old if cache full
                while len(self._cache) > self._max_cache_size:
                    oldest_key = self._cache_keys.pop(0)
                    del self._cache[oldest_key]

            return qt_pixmap
        except Exception as e:
            print(f"Error processing frame: {e}")
            return None

    def clear_cache(self):
        with self._lock:
            self._cache.clear()
            self._cache_keys.clear()


# noinspection PyUnresolvedReferences
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_window()
        self._initialize_settings()
        self._setup_components()
        self._setup_timers()
        self._setup_ui()
    
    def _setup_window(self):
        """Configure main window properties."""
        self.setWindowTitle("YABM Generator")
        self.setGeometry(100, 100, 1280, 720)
    
    def _initialize_settings(self):
        """Initialize application settings and state variables."""
        # Settings
        self.dither_method = 'bayer4x4'
        self.palette_method = '1bit_gray'
        self.index = 0

        # Video settings
        self.video_capture = None
        self.video_frames = []
        self.current_frame_index = 0
        self.total_frames = 0
        self.is_video_loaded = False
        self.fps = 0
    
    def _setup_components(self):
        """Initialize core components."""
        self.video_loader = VideoLoader()
        self.image_processor = ImageProcessor()
    
    def _setup_timers(self):
        """Configure application timers."""
        # Timer for delay
        self._processing_timer = QTimer()
        self._processing_timer.setSingleShot(True)
        self._processing_timer.timeout.connect(self._delayed_process_image)
        self._last_process_time = 0

        # Timer for memory clear
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_memory)
        self._cleanup_timer.start(30000)  # Every 30 seconds
    
    def _setup_ui(self):
        """Setup the user interface layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 3)

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
        palette_layout = QVBoxLayout()
        palette_label = QLabel("Palette:")
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(palette.available_palettes)
        self.palette_combo.setCurrentText(self.palette_method)
        self.palette_combo.currentTextChanged.connect(self.on_palette_changed)

        palette_layout.addWidget(palette_label)
        palette_layout.addWidget(self.palette_combo)
        layout.addLayout(palette_layout)

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
        self.export_all_btn = QPushButton("Export All Images")
        self.back_btn = QPushButton("Back")
        self.next_btn = QPushButton("Next")
        self.next_save_btn = QPushButton("Next + Save")

        self.export_one_btn.clicked.connect(self.export_one)
        self.export_all_btn.clicked.connect(self.export_all)
        self.back_btn.clicked.connect(self.back)
        self.next_btn.clicked.connect(self.next)
        self.next_save_btn.clicked.connect(self.next_save)

        buttons_row.addWidget(self.export_one_btn)
        buttons_row.addWidget(self.export_all_btn)
        buttons_row.addWidget(self.back_btn)
        buttons_row.addWidget(self.next_btn)
        buttons_row.addWidget(self.next_save_btn)
        layout.addLayout(buttons_row)

        self.export_one_btn.setEnabled(False)
        self.export_all_btn.setEnabled(False)
        self.back_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.next_save_btn.setEnabled(False)

        right_group.setLayout(layout)
        return right_group

    def _schedule_processing(self):
        current_time = time.time()
        if current_time - self._last_process_time > 0.2:  # Every 200ms
            self._processing_timer.stop()
            self.process_image()
            self._last_process_time = current_time
        else:
            self._processing_timer.start(200)  # Waiting 200ms

    def _delayed_process_image(self):
        self.process_image()

    def _cleanup_memory(self):
        if hasattr(self, 'image_processor'):
            self.image_processor.clear_cache()
        gc.collect()

    # Signals
    def load_image(self, test=False):
        """Load an image file and prepare for processing."""
        self._get_image_file_path(test)
        
        if self.file_path and self.file_path != '':
            self._prepare_for_image_mode()
            self.process_image()
    
    def _get_image_file_path(self, test=False):
        """Get the image file path from user or test mode."""
        if test:
            self.file_path = "test.jpg"
            self.file_name = "test.jpg"
        else:
            result = QFileDialog.getOpenFileName(
                self,
                "Select Image",
                "",
                "Image Files (*.jpg *.jpeg *.png *.bmp)",
                options=QFileDialog.Option.DontUseNativeDialog
            )
            self.file_path = result[0]
            self.file_name = os.path.basename(self.file_path) if self.file_path else ""
    
    def _prepare_for_image_mode(self):
        """Prepare the application for image processing mode."""
        self.index = 0
        self.is_video_loaded = False
        self.video_loader.cleanup()
        
        self._cleanup_video_controls()
        self._set_image_mode_buttons()
    
    def _cleanup_video_controls(self):
        """Remove video-specific UI controls."""
        if hasattr(self, 'video_slider'):
            self.video_slider.deleteLater()
        if hasattr(self, 'video_frame_info'):
            self.video_frame_info.deleteLater()
    
    def _set_image_mode_buttons(self):
        """Configure button states for image mode."""
        self.back_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.next_save_btn.setEnabled(False)
        self.export_all_btn.setEnabled(False)
        self.export_one_btn.setEnabled(True)

    def load_video(self):
        """Load a video file and prepare for processing."""
        self._get_video_file_path()
        
        if self.file_path and self.file_path != '':
            self._prepare_for_video_mode()
            self.load_video_file(self.file_path)
    
    def _get_video_file_path(self):
        """Get the video file path from user selection."""
        result = QFileDialog.getOpenFileName(
            self,
            "Select Video",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        self.file_path = result[0]
    
    def _prepare_for_video_mode(self):
        """Configure UI for video processing mode."""
        self.back_btn.setEnabled(True)
        self.next_btn.setEnabled(True)
        self.next_save_btn.setEnabled(True)
        self.export_all_btn.setEnabled(True)
        self.export_one_btn.setEnabled(True)

    def load_video_file(self, video_path):
        progress = None
        try:
            # Showing progressbar
            progress = QProgressDialog("Loading video...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            # Clearing states
            self.video_frames = []
            self.current_frame_index = 0
            self.is_video_loaded = True
            self.image_processor.clear_cache()

            # Opening video for info
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print("Error: Could not open video")
                return

            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()

            print(f"Video loaded: {self.total_frames} frames, {self.fps} FPS")

            # Starting background loading frames
            self.video_loader.start_loading(video_path)

            self.setup_video_controls()

            self.show_video_frame(0)

        except Exception as e:
            print(f"Error loading video: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if progress:
                progress.close()

    def setup_video_controls(self):
        try:
            if hasattr(self, 'video_slider') and self.video_slider is not None:
                try:
                    self.video_slider.deleteLater()
                    self.video_slider = None
                except RuntimeError:
                    self.video_slider = None

            if hasattr(self, 'video_frame_info') and self.video_frame_info is not None:
                try:
                    self.video_frame_info.deleteLater()
                    self.video_frame_info = None
                except RuntimeError:
                    self.video_frame_info = None

            self.video_slider = QSlider(Qt.Orientation.Horizontal)
            self.video_slider.setMinimum(0)
            self.video_slider.setMaximum(self.total_frames - 1)
            self.video_slider.valueChanged.connect(self.on_video_slider_changed)

            self.video_frame_info = QLabel(f"Frame: 1 / {self.total_frames}")
            self.video_frame_info.setFixedHeight(20)

            right_layout = self.image_label.parent().layout()
            right_layout.addWidget(self.video_slider)
            right_layout.addWidget(self.video_frame_info)
        except Exception as e:
            print(f"Error setting up video controls: {e}")

    def show_video_frame(self, frame_index):
        """Display a specific video frame with current processing settings."""
        try:
            pil_image = self._get_video_frame_image(frame_index)
            if pil_image is None:
                return
                
            self._process_and_display_frame(pil_image)
            self._update_frame_info(frame_index)
            
        except Exception as e:
            print(f"Error showing video frame: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_video_frame_image(self, frame_index):
        """Get PIL image for the specified frame index."""
        cached_frame = self.video_loader.get_frame(frame_index)
        
        if cached_frame is not None:
            return Image.fromarray(cached_frame)
        
        return self._load_frame_from_video(frame_index)
    
    def _load_frame_from_video(self, frame_index):
        """Load frame directly from video file as fallback."""
        cap = None
        try:
            cap = cv2.VideoCapture(self.file_path)
            if not cap.isOpened():
                print(f"Error: Could not open video file: {self.file_path}")
                return None
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = cap.read()
            
            if not ret:
                return None
                
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return Image.fromarray(frame_rgb)
        except Exception as e:
            print(f"Error loading frame {frame_index}: {e}")
            return None
        finally:
            if cap:
                cap.release()
    
    def _process_and_display_frame(self, pil_image):
        """Process image with current settings and display it."""
        scale_percent = self.size_slider.value()
        threshold_value = self.threshold_slider.value() / 100.0
        
        self.current_pixmap = self.image_processor.process_frame(
            pil_image, scale_percent, threshold_value,
            self.dither_method, self.palette_method
        )
        
        self.scale_image()
    
    def _update_frame_info(self, frame_index):
        """Update the frame information display."""
        if hasattr(self, 'video_frame_info'):
            self.video_frame_info.setText(f"Frame: {frame_index + 1} / {self.total_frames}")

    def process_image(self):
        if not hasattr(self, 'file_path') or not self.file_path:
            return

        if self.is_video_loaded:
            self.show_video_frame(self.current_frame_index)
        else:
            try:
                image = utils.open_image(self.file_path)
                scale_percent = self.size_slider.value()
                threshold_value = self.threshold_slider.value() / 100.0

                self.current_pixmap = self.image_processor.process_frame(
                    image, scale_percent, threshold_value,
                    self.dither_method, self.palette_method
                )
                self.scale_image()
            except Exception as e:
                print(f"Error loading image: {e}")

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
        self._schedule_processing()

    def on_threshold_changed(self, value):
        self.threshold_value_label.setText(str(value))
        self._schedule_processing()

    def on_dither_changed(self, method):
        self.dither_method = method
        self._schedule_processing()

    def on_palette_changed(self, value):
        self.palette_method = value
        self._schedule_processing()

    def on_video_slider_changed(self, value):
        self.current_frame_index = value
        self.show_video_frame(value)

    @staticmethod
    def open_github():
        github_url = "https://github.com/bezdarnosti-yt/YABM-generator"
        webbrowser.open(github_url)

    def next(self):
        if self.current_frame_index < self.total_frames - 1:
            self.on_video_slider_changed(self.current_frame_index + 1)

    def back(self):
        if self.current_frame_index > 0:
            self.on_video_slider_changed(self.current_frame_index - 1)

    def export_one(self):
        if not hasattr(self, 'current_pixmap') or self.current_pixmap.isNull():
            return

        try:
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            results_dir = f"{base_name}_results"
            os.makedirs(results_dir, exist_ok=True)

            if self.is_video_loaded:
                filename = f"{results_dir}/result_{self.current_frame_index+1}.jpg"
            else:
                filename = f"{results_dir}/result_{self.index+1:04d}.jpg"

            self.current_pixmap.save(filename)
            self.index += 1
        except Exception as e:
            print(f"Error exporting image: {e}")

    def export_all(self):
        """Export all video frames as individual images."""
        if not hasattr(self, 'current_pixmap') or self.current_pixmap.isNull():
            return

        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        results_dir = f"{base_name}_results"
        os.makedirs(results_dir, exist_ok=True)
        
        for frame_idx in range(self.total_frames):
            self._export_single_frame(frame_idx, results_dir)
    
    def _export_single_frame(self, frame_idx, results_dir):
        """Export a single frame to the specified directory."""
        try:
            self.current_frame_index = frame_idx
            self.show_video_frame(frame_idx)
            
            filename = f"{results_dir}/result_{frame_idx+1}.jpg"
            self.current_pixmap.save(filename)
        except Exception as e:
            print(f"Error exporting frame {frame_idx}: {e}")


    def next_save(self):
        """Save current frame and move to next frame."""
        if not hasattr(self, 'current_pixmap') or self.current_pixmap.isNull():
            return

        self._save_current_frame()
        self.next()
    
    def _save_current_frame(self):
        """Save the current frame to file."""
        try:
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            results_dir = f"{base_name}_results"
            os.makedirs(results_dir, exist_ok=True)
            
            filename = f"{results_dir}/result_{self.current_frame_index+1}.jpg"
            self.current_pixmap.save(filename)
        except Exception as e:
            print(f"Error saving current frame: {e}")

    def closeEvent(self, event):
        """Clean up resources when closing the application."""
        self._cleanup_resources()
        event.accept()
    
    def _cleanup_resources(self):
        """Clean up all resources and stop background threads."""
        self.video_loader.cleanup()
        self.image_processor.clear_cache()
        if self.video_capture:
            self.video_capture.release()

available_methods = OrderedDict()

available_methods.update(threshold.available_methods)
available_methods.update(randomized.available_methods)
available_methods.update(ordered_dithering.available_methods)
available_methods.update(error_diffusion.available_methods)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())