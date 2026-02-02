# Wallpaper Engine

A Python-based multi-layer depth wallpaper engine that uses AI to create dynamic, depth-aware wallpapers for Windows.

## Features

- 🎨 **AI-Powered Depth Estimation** - Uses transformer models to analyze image depth
- 🖼️ **Multi-Layer Rendering** - Creates multiple depth layers for parallax effects
- 🕐 **Real-Time Clock** - Overlays animated clock on wallpapers
- 🎯 **Automatic Background Removal** - Separates foreground and background
- 🖥️ **Windows Integration** - Sets wallpapers directly on Windows desktop
- 🎛️ **User-Friendly GUI** - PySide6-based interface for easy configuration

## Project Structure

```
wallpaper_engin/
├── app.py                      # Main GUI application
├── windows_wallpaper_engin.py  # Core depth engine and wallpaper renderer
├── depth_map.py                # Depth map processing utilities
├── image_separate.py           # Background/foreground separation
├── requirements.txt            # Python dependencies
└── rendered_wallpapers/        # Output directory for generated wallpapers
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows OS (for wallpaper integration)
- GPU support recommended (for faster AI processing)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Navanjana2005/AI-DEPTH-Wallpaper-Engine.git
cd wallpaper_engin
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Run the GUI Application

```bash
python app.py
```

### Basic Usage
1. Select an image from your computer
2. Configure depth layers and settings
3. Choose font and colors
4. Generate the wallpaper
5. Apply to your Windows desktop

## Dependencies

- **torch** - Deep learning framework
- **transformers** - Pre-trained AI models for depth estimation
- **Pillow** - Image processing
- **numpy** - Numerical computing
- **PySide6** - GUI framework
- **pystray** - System tray integration
- **rembg** - Background removal

## How It Works

1. **Depth Estimation** - Uses pre-trained transformer models to estimate depth from images
2. **Layer Separation** - Creates multiple layers based on depth information
3. **Dynamic Rendering** - Renders real-time clock with parallax effect
4. **Wallpaper Application** - Applies the rendered image to Windows desktop background

## Performance Notes

- First run may be slow due to model download (~500MB)
- Subsequent runs are optimized to only update the clock in real-time
- GPU acceleration significantly speeds up processing

## License

This project is open source. Feel free to use, modify, and distribute.

## Troubleshooting

- **Model not found**: Ensure internet connection for first-time model download
- **GPU out of memory**: Reduce number of layers or image resolution
- **Wallpaper not updating**: Check Windows permissions and Administrator rights

## Contributing

Feel free to submit issues and pull requests!

