import sys
import os
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QComboBox, QFileDialog, QSpinBox,
    QGroupBox, QColorDialog, QFontDialog, QCheckBox, QTabWidget,
    QListWidget, QMessageBox, QProgressBar, QFrame, QTextEdit,
    QLineEdit, QRadioButton, QButtonGroup, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QPixmap, QIcon, QPalette
import datetime

# Import your engine (assuming it's in the same directory)
try:
    from windows_wallpaper_engin import MultiLayerDepthEngine
except ImportError:
    print("Error: Could not import MultiLayerDepthEngine")
    print("Make sure windows_wallpaper_engin_2.py is in the same directory")
    sys.exit(1)


class EngineWorker(QThread):
    """Worker thread for AI processing to keep UI responsive"""
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        
    def run(self):
        try:
            self.progress.emit("Initializing engine...")
            self.engine.initialize()
            self.finished.emit(True, "Engine initialized successfully!")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class PreviewWidget(QLabel):
    """Custom widget to display wallpaper preview"""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 300)
        self.setMaximumSize(800, 600)
        self.setScaledContents(True)
        self.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.setAlignment(Qt.AlignCenter)
        self.setText("No preview available")
        self.setStyleSheet("background-color: #2b2b2b; color: #888;")


class DepthWallpaperGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = None
        self.config_file = Path("wallpaper_config.json")
        self.default_config = {
            "image_path": "",
            "font_path": "",
            "font_size": 150,
            "font_color": "#FFFFFF",
            "shadow_color": "#000000",
            "shadow_opacity": 120,
            "shadow_offset": 4,
            "update_interval": 1,
            "num_layers": 5,
            "clock_layer": 2,
            "show_date": True,
            "date_font_size": 30,
            "clock_format": "%H:%M",
            "date_format": "%a %b %d",
            "clock_position_x": 50,  # percentage
            "clock_position_y": 25,  # percentage
            "auto_start": False
        }
        self.config = self.load_config()
        self.init_ui()
        self.load_saved_settings()
        
    def init_ui(self):
        self.setWindowTitle("Depth Wallpaper Engine - Control Panel")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(self.get_stylesheet())
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Controls
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 2)
        
        # Right panel - Preview and status
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def create_left_panel(self):
        """Create the main control panel"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Tab widget for organized controls
        tabs = QTabWidget()
        
        # Tab 1: Image & Layers
        tabs.addTab(self.create_image_tab(), "Image & Layers")
        
        # Tab 2: Clock Settings
        tabs.addTab(self.create_clock_tab(), "Clock & Date")
        
        # Tab 3: Appearance
        tabs.addTab(self.create_appearance_tab(), "Appearance")
        
        # Tab 4: Advanced
        tabs.addTab(self.create_advanced_tab(), "Advanced")
        
        layout.addWidget(tabs)
        
        # Bottom control buttons
        control_group = self.create_control_buttons()
        layout.addWidget(control_group)
        
        scroll.setWidget(container)
        return scroll
        
    def create_image_tab(self):
        """Image selection and layer configuration"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Image selection
        image_group = QGroupBox("Image Selection")
        image_layout = QVBoxLayout()
        
        self.image_path_label = QLabel("No image selected")
        self.image_path_label.setWordWrap(True)
        image_layout.addWidget(self.image_path_label)
        
        btn_select_image = QPushButton("📁 Select Background Image")
        btn_select_image.clicked.connect(self.select_image)
        image_layout.addWidget(btn_select_image)
        
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)
        
        # Layer configuration
        layer_group = QGroupBox("Depth Layers Configuration")
        layer_layout = QVBoxLayout()
        
        # Number of layers
        layers_h = QHBoxLayout()
        layers_h.addWidget(QLabel("Number of Layers:"))
        self.num_layers_spin = QSpinBox()
        self.num_layers_spin.setRange(3, 10)
        self.num_layers_spin.setValue(self.config.get("num_layers", 5))
        self.num_layers_spin.setToolTip("More layers = finer depth control (requires regeneration)")
        layers_h.addWidget(self.num_layers_spin)
        layers_h.addStretch()
        layer_layout.addLayout(layers_h)
        
        # Clock layer selection
        layer_layout.addWidget(QLabel("Clock Depth Position:"))
        self.layer_list = QListWidget()
        self.layer_list.setMaximumHeight(150)
        layer_layout.addWidget(self.layer_list)
        
        layer_info = QLabel("Select which depth layer should display the clock.\n"
                           "Layers are generated after image processing.")
        layer_info.setStyleSheet("color: #888; font-size: 11px;")
        layer_info.setWordWrap(True)
        layer_layout.addWidget(layer_info)
        
        layer_group.setLayout(layer_layout)
        layout.addWidget(layer_group)
        
        layout.addStretch()
        return widget
        
    def create_clock_tab(self):
        """Clock and date settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Time format
        time_group = QGroupBox("Time Display")
        time_layout = QVBoxLayout()
        
        # Clock format
        format_h = QHBoxLayout()
        format_h.addWidget(QLabel("Time Format:"))
        self.clock_format_combo = QComboBox()
        self.clock_format_combo.addItems([
            "%H:%M (24-hour)",
            "%I:%M %p (12-hour)",
            "%H:%M:%S (with seconds)"
        ])
        format_h.addWidget(self.clock_format_combo)
        time_layout.addLayout(format_h)
        
        # Custom format
        custom_h = QHBoxLayout()
        custom_h.addWidget(QLabel("Custom Format:"))
        self.custom_format_input = QLineEdit()
        self.custom_format_input.setPlaceholderText("e.g., %H:%M")
        custom_h.addWidget(self.custom_format_input)
        time_layout.addLayout(custom_h)
        
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # Date settings
        date_group = QGroupBox("Date Display")
        date_layout = QVBoxLayout()
        
        self.show_date_check = QCheckBox("Show Date")
        self.show_date_check.setChecked(self.config.get("show_date", True))
        date_layout.addWidget(self.show_date_check)
        
        date_format_h = QHBoxLayout()
        date_format_h.addWidget(QLabel("Date Format:"))
        self.date_format_combo = QComboBox()
        self.date_format_combo.addItems([
            "%a %b %d (Mon Jan 27)",
            "%A, %B %d (Monday, January 27)",
            "%d/%m/%Y (27/01/2026)",
            "%B %d, %Y (January 27, 2026)"
        ])
        date_format_h.addWidget(self.date_format_combo)
        date_layout.addLayout(date_format_h)
        
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        # Position
        pos_group = QGroupBox("Clock Position")
        pos_layout = QVBoxLayout()
        
        # Horizontal position
        h_pos_layout = QHBoxLayout()
        h_pos_layout.addWidget(QLabel("Horizontal:"))
        self.h_pos_slider = QSlider(Qt.Horizontal)
        self.h_pos_slider.setRange(0, 100)
        self.h_pos_slider.setValue(self.config.get("clock_position_x", 50))
        self.h_pos_label = QLabel(f"{self.h_pos_slider.value()}%")
        self.h_pos_slider.valueChanged.connect(
            lambda v: self.h_pos_label.setText(f"{v}%")
        )
        h_pos_layout.addWidget(self.h_pos_slider)
        h_pos_layout.addWidget(self.h_pos_label)
        pos_layout.addLayout(h_pos_layout)
        
        # Vertical position
        v_pos_layout = QHBoxLayout()
        v_pos_layout.addWidget(QLabel("Vertical:"))
        self.v_pos_slider = QSlider(Qt.Horizontal)
        self.v_pos_slider.setRange(0, 100)
        self.v_pos_slider.setValue(self.config.get("clock_position_y", 25))
        self.v_pos_label = QLabel(f"{self.v_pos_slider.value()}%")
        self.v_pos_slider.valueChanged.connect(
            lambda v: self.v_pos_label.setText(f"{v}%")
        )
        v_pos_layout.addWidget(self.v_pos_slider)
        v_pos_layout.addWidget(self.v_pos_label)
        pos_layout.addLayout(v_pos_layout)
        
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)
        
        layout.addStretch()
        return widget
        
    def create_appearance_tab(self):
        """Font and color settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Font settings
        font_group = QGroupBox("Font Settings")
        font_layout = QVBoxLayout()
        
        # Font selection
        font_btn_layout = QHBoxLayout()
        self.font_path_label = QLabel("System Default Font")
        font_btn_layout.addWidget(self.font_path_label)
        btn_select_font = QPushButton("Select Font")
        btn_select_font.clicked.connect(self.select_font)
        font_btn_layout.addWidget(btn_select_font)
        font_layout.addLayout(font_btn_layout)
        
        # Font size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Clock Size:"))
        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setRange(50, 300)
        self.font_size_slider.setValue(self.config.get("font_size", 150))
        self.font_size_label = QLabel(f"{self.font_size_slider.value()}px")
        self.font_size_slider.valueChanged.connect(
            lambda v: self.font_size_label.setText(f"{v}px")
        )
        size_layout.addWidget(self.font_size_slider)
        size_layout.addWidget(self.font_size_label)
        font_layout.addLayout(size_layout)
        
        # Date font size
        date_size_layout = QHBoxLayout()
        date_size_layout.addWidget(QLabel("Date Size:"))
        self.date_size_slider = QSlider(Qt.Horizontal)
        self.date_size_slider.setRange(10, 100)
        self.date_size_slider.setValue(self.config.get("date_font_size", 30))
        self.date_size_label = QLabel(f"{self.date_size_slider.value()}px")
        self.date_size_slider.valueChanged.connect(
            lambda v: self.date_size_label.setText(f"{v}px")
        )
        date_size_layout.addWidget(self.date_size_slider)
        date_size_layout.addWidget(self.date_size_label)
        font_layout.addLayout(date_size_layout)
        
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        # Color settings
        color_group = QGroupBox("Colors")
        color_layout = QVBoxLayout()
        
        # Font color
        font_color_layout = QHBoxLayout()
        font_color_layout.addWidget(QLabel("Text Color:"))
        self.font_color_btn = QPushButton()
        self.font_color = QColor(self.config.get("font_color", "#FFFFFF"))
        self.update_color_button(self.font_color_btn, self.font_color)
        self.font_color_btn.clicked.connect(self.select_font_color)
        font_color_layout.addWidget(self.font_color_btn)
        font_color_layout.addStretch()
        color_layout.addLayout(font_color_layout)
        
        # Shadow color
        shadow_color_layout = QHBoxLayout()
        shadow_color_layout.addWidget(QLabel("Shadow Color:"))
        self.shadow_color_btn = QPushButton()
        self.shadow_color = QColor(self.config.get("shadow_color", "#000000"))
        self.update_color_button(self.shadow_color_btn, self.shadow_color)
        self.shadow_color_btn.clicked.connect(self.select_shadow_color)
        shadow_color_layout.addWidget(self.shadow_color_btn)
        shadow_color_layout.addStretch()
        color_layout.addLayout(shadow_color_layout)
        
        # Shadow opacity
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Shadow Opacity:"))
        self.shadow_opacity_slider = QSlider(Qt.Horizontal)
        self.shadow_opacity_slider.setRange(0, 255)
        self.shadow_opacity_slider.setValue(self.config.get("shadow_opacity", 120))
        self.shadow_opacity_label = QLabel(f"{self.shadow_opacity_slider.value()}")
        self.shadow_opacity_slider.valueChanged.connect(
            lambda v: self.shadow_opacity_label.setText(str(v))
        )
        opacity_layout.addWidget(self.shadow_opacity_slider)
        opacity_layout.addWidget(self.shadow_opacity_label)
        color_layout.addLayout(opacity_layout)
        
        # Shadow offset
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("Shadow Offset:"))
        self.shadow_offset_spin = QSpinBox()
        self.shadow_offset_spin.setRange(0, 20)
        self.shadow_offset_spin.setValue(self.config.get("shadow_offset", 4))
        offset_layout.addWidget(self.shadow_offset_spin)
        offset_layout.addStretch()
        color_layout.addLayout(offset_layout)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        layout.addStretch()
        return widget
        
    def create_advanced_tab(self):
        """Advanced settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Update settings
        update_group = QGroupBox("Update Settings")
        update_layout = QVBoxLayout()
        
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Update Interval:"))
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(1, 60)
        self.update_interval_spin.setValue(self.config.get("update_interval", 1))
        self.update_interval_spin.setSuffix(" seconds")
        interval_layout.addWidget(self.update_interval_spin)
        interval_layout.addStretch()
        update_layout.addLayout(interval_layout)
        
        self.auto_start_check = QCheckBox("Auto-start engine on launch")
        self.auto_start_check.setChecked(self.config.get("auto_start", False))
        update_layout.addWidget(self.auto_start_check)
        
        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
        
        # Export options
        export_group = QGroupBox("Export & Debug")
        export_layout = QVBoxLayout()
        
        btn_export_layers = QPushButton("Export All Layers")
        btn_export_layers.clicked.connect(self.export_layers)
        export_layout.addWidget(btn_export_layers)
        
        btn_export_config = QPushButton("Export Configuration")
        btn_export_config.clicked.connect(self.export_config)
        export_layout.addWidget(btn_export_config)
        
        btn_import_config = QPushButton("Import Configuration")
        btn_import_config.clicked.connect(self.import_config)
        export_layout.addWidget(btn_import_config)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        return widget
        
    def create_right_panel(self):
        """Create preview and status panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_widget = PreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        
        btn_refresh_preview = QPushButton("🔄 Refresh Preview")
        btn_refresh_preview.clicked.connect(self.update_preview)
        preview_layout.addWidget(btn_refresh_preview)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Status and logs
        status_group = QGroupBox("Status & Logs")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        status_layout.addWidget(self.status_text)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        return widget
        
    def create_control_buttons(self):
        """Create main control buttons"""
        group = QGroupBox("Engine Control")
        layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        
        self.btn_initialize = QPushButton("⚙️ Initialize Engine")
        self.btn_initialize.clicked.connect(self.initialize_engine)
        self.btn_initialize.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 10px; font-weight: bold; }"
        )
        btn_layout.addWidget(self.btn_initialize)
        
        self.btn_start = QPushButton("▶️ Start Engine")
        self.btn_start.clicked.connect(self.start_engine)
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }"
        )
        btn_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("⏹️ Stop Engine")
        self.btn_stop.clicked.connect(self.stop_engine)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { background-color: #F44336; color: white; padding: 10px; font-weight: bold; }"
        )
        btn_layout.addWidget(self.btn_stop)
        
        layout.addLayout(btn_layout)
        
        btn_apply = QPushButton("💾 Apply Settings")
        btn_apply.clicked.connect(self.apply_settings)
        layout.addWidget(btn_apply)
        
        group.setLayout(layout)
        return group
        
    # Event handlers
    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.config["image_path"] = file_path
            self.image_path_label.setText(Path(file_path).name)
            self.log(f"Selected image: {Path(file_path).name}")
            
    def select_font(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Font File", "",
            "Font Files (*.ttf *.otf)"
        )
        if file_path:
            self.config["font_path"] = file_path
            self.font_path_label.setText(Path(file_path).name)
            self.log(f"Selected font: {Path(file_path).name}")
            
    def select_font_color(self):
        color = QColorDialog.getColor(self.font_color, self, "Select Text Color")
        if color.isValid():
            self.font_color = color
            self.update_color_button(self.font_color_btn, color)
            self.config["font_color"] = color.name()
            
    def select_shadow_color(self):
        color = QColorDialog.getColor(self.shadow_color, self, "Select Shadow Color")
        if color.isValid():
            self.shadow_color = color
            self.update_color_button(self.shadow_color_btn, color)
            self.config["shadow_color"] = color.name()
            
    def update_color_button(self, button, color):
        button.setStyleSheet(
            f"QPushButton {{ background-color: {color.name()}; "
            f"border: 2px solid #555; min-width: 60px; min-height: 30px; }}"
        )
        
    def initialize_engine(self):
        if not self.config.get("image_path"):
            QMessageBox.warning(self, "Warning", "Please select an image first!")
            return
            
        self.save_current_settings()
        self.log("Initializing engine... This may take a moment.")
        self.btn_initialize.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        # Create engine with current settings
        self.engine = MultiLayerDepthEngine(
            image_path=self.config["image_path"],
            font_path=self.config.get("font_path"),
            update_interval=self.config["update_interval"],
            num_layers=self.config["num_layers"]
        )
        
        # Start worker thread
        self.worker = EngineWorker(self.engine)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.on_engine_initialized)
        self.worker.start()
        
    def on_engine_initialized(self, success, message):
        self.progress_bar.setVisible(False)
        self.btn_initialize.setEnabled(True)
        
        if success:
            self.log(message)
            self.btn_start.setEnabled(True)
            self.update_layer_list()
            QMessageBox.information(self, "Success", message)
        else:
            self.log(f"Error: {message}")
            QMessageBox.critical(self, "Error", message)
            
    def update_layer_list(self):
        """Update the layer selection list"""
        if not self.engine or not self.engine.layers:
            return
            
        self.layer_list.clear()
        for i, layer_data in enumerate(self.engine.layers):
            item_text = f"Layer {i+1}: {layer_data['name']}"
            self.layer_list.addItem(item_text)
            
        # Select current clock layer
        self.layer_list.setCurrentRow(self.config.get("clock_layer", 2))
        self.layer_list.itemClicked.connect(self.on_layer_selected)
        
    def on_layer_selected(self, item):
        layer_index = self.layer_list.currentRow()
        if self.engine:
            self.engine.set_clock_layer(layer_index)
            self.config["clock_layer"] = layer_index
            self.log(f"Clock layer changed to: {layer_index + 1}")
            
    def start_engine(self):
        if self.engine:
            self.apply_settings()
            self.engine.start()
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.log("Engine started! Wallpaper updating...")
            self.statusBar().showMessage("Engine Running")
            
    def stop_engine(self):
        if self.engine:
            self.engine.stop()
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.log("Engine stopped.")
            self.statusBar().showMessage("Engine Stopped")
            
    def apply_settings(self):
        """Apply current UI settings to engine"""
        if not self.engine:
            self.log("Please initialize engine first!")
            return
            
        self.save_current_settings()
        
        # Apply settings to engine
        self.engine.update_interval = self.config["update_interval"]
        
        # If engine is running, update it
        if hasattr(self.engine, 'running') and self.engine.running:
            self.engine.create_wallpaper_frame()
            self.engine.set_windows_wallpaper(self.engine.wallpaper_path)
            
        self.log("Settings applied!")
        self.update_preview()
        
    def update_preview(self):
        """Update the wallpaper preview"""
        if self.engine and self.engine.wallpaper_path.exists():
            pixmap = QPixmap(str(self.engine.wallpaper_path))
            self.preview_widget.setPixmap(
                pixmap.scaled(self.preview_widget.size(), 
                            Qt.KeepAspectRatio, 
                            Qt.SmoothTransformation)
            )
            self.log("Preview updated")
        else:
            self.log("No preview available yet")
            
    def export_layers(self):
        if self.engine:
            self.engine.export_debug_images()
            self.log(f"Layers exported to: {self.engine.output_dir}")
            QMessageBox.information(self, "Success", 
                                  f"Layers exported to:\n{self.engine.output_dir}")
        else:
            QMessageBox.warning(self, "Warning", "Please initialize engine first!")
            
    def export_config(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Configuration", "", "JSON Files (*.json)"
        )
        if file_path:
            self.save_current_settings()
            with open(file_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.log(f"Configuration exported to: {file_path}")
            
    def import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    imported_config = json.load(f)
                self.config.update(imported_config)
                self.load_saved_settings()
                self.log(f"Configuration imported from: {file_path}")
                QMessageBox.information(self, "Success", "Configuration imported!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import: {str(e)}")
                
    def save_current_settings(self):
        """Save current UI settings to config"""
        self.config.update({
            "num_layers": self.num_layers_spin.value(),
            "font_size": self.font_size_slider.value(),
            "date_font_size": self.date_size_slider.value(),
            "font_color": self.font_color.name(),
            "shadow_color": self.shadow_color.name(),
            "shadow_opacity": self.shadow_opacity_slider.value(),
            "shadow_offset": self.shadow_offset_spin.value(),
            "update_interval": self.update_interval_spin.value(),
            "show_date": self.show_date_check.isChecked(),
            "clock_position_x": self.h_pos_slider.value(),
            "clock_position_y": self.v_pos_slider.value(),
            "auto_start": self.auto_start_check.isChecked()
        })
        self.save_config()
        
    def load_saved_settings(self):
        """Load config into UI elements"""
        if self.config.get("image_path"):
            self.image_path_label.setText(Path(self.config["image_path"]).name)
        if self.config.get("font_path"):
            self.font_path_label.setText(Path(self.config["font_path"]).name)
            
        self.num_layers_spin.setValue(self.config.get("num_layers", 5))
        self.font_size_slider.setValue(self.config.get("font_size", 150))
        self.date_size_slider.setValue(self.config.get("date_font_size", 30))
        self.shadow_opacity_slider.setValue(self.config.get("shadow_opacity", 120))
        self.shadow_offset_spin.setValue(self.config.get("shadow_offset", 4))
        self.update_interval_spin.setValue(self.config.get("update_interval", 1))
        self.show_date_check.setChecked(self.config.get("show_date", True))
        self.h_pos_slider.setValue(self.config.get("clock_position_x", 50))
        self.v_pos_slider.setValue(self.config.get("clock_position_y", 25))
        self.auto_start_check.setChecked(self.config.get("auto_start", False))
        
        self.font_color = QColor(self.config.get("font_color", "#FFFFFF"))
        self.update_color_button(self.font_color_btn, self.font_color)
        
        self.shadow_color = QColor(self.config.get("shadow_color", "#000000"))
        self.update_color_button(self.shadow_color_btn, self.shadow_color)
        
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    config = self.default_config.copy()
                    config.update(loaded_config)
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
        return self.default_config.copy()
        
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
            
    def log(self, message):
        """Add message to log display"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        self.statusBar().showMessage(message)
        
    def closeEvent(self, event):
        """Handle window close event"""
        if self.engine and hasattr(self.engine, 'running') and self.engine.running:
            reply = QMessageBox.question(
                self, 'Confirm Exit',
                'Engine is still running. Stop and exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.stop_engine()
                self.save_current_settings()
                event.accept()
            else:
                event.ignore()
        else:
            self.save_current_settings()
            event.accept()
            
    def get_stylesheet(self):
        """Return application stylesheet"""
        return """
        QMainWindow {
            background-color: #1e1e1e;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #3a3a3a;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #3a3a3a;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 8px 16px;
            color: #e0e0e0;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
            border: 1px solid #666;
        }
        QPushButton:pressed {
            background-color: #2a2a2a;
        }
        QPushButton:disabled {
            background-color: #252525;
            color: #666;
        }
        QLineEdit, QSpinBox, QComboBox {
            background-color: #2b2b2b;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            padding: 6px;
            color: #e0e0e0;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border: 1px solid #2196F3;
        }
        QSlider::groove:horizontal {
            height: 6px;
            background: #3a3a3a;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #2196F3;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        QSlider::handle:horizontal:hover {
            background: #42A5F5;
        }
        QTabWidget::pane {
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            background-color: #1e1e1e;
        }
        QTabBar::tab {
            background-color: #2b2b2b;
            border: 1px solid #3a3a3a;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #3a3a3a;
            border-bottom-color: #3a3a3a;
        }
        QTabBar::tab:hover {
            background-color: #4a4a4a;
        }
        QListWidget {
            background-color: #2b2b2b;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
        }
        QListWidget::item:selected {
            background-color: #2196F3;
        }
        QListWidget::item:hover {
            background-color: #3a3a3a;
        }
        QTextEdit {
            background-color: #2b2b2b;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            padding: 8px;
        }
        QCheckBox {
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #3a3a3a;
            border-radius: 3px;
            background-color: #2b2b2b;
        }
        QCheckBox::indicator:checked {
            background-color: #2196F3;
            border-color: #2196F3;
        }
        QProgressBar {
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            text-align: center;
            background-color: #2b2b2b;
        }
        QProgressBar::chunk {
            background-color: #2196F3;
            border-radius: 3px;
        }
        QScrollArea {
            border: none;
        }
        QScrollBar:vertical {
            background: #2b2b2b;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #3a3a3a;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #4a4a4a;
        }
        """


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = DepthWallpaperGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()