import torch
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import datetime
import time
import os
import ctypes
import sys
from pathlib import Path
import threading
import pystray
from pystray import MenuItem as item
from PIL import Image as PILImage
import json


class MultiLayerDepthEngine:
    def __init__(self, image_path, font_path=None, update_interval=1, num_layers=5):
        """
        Optimized Multi-Layer Depth Wallpaper Engine
        AI model runs ONCE, then only updates clock in real-time

        Args:
            image_path: Path to the input image
            font_path: Path to TTF font file (optional)
            update_interval: Seconds between clock updates (default: 1)
            num_layers: Number of depth layers to create (default: 5)
        """
        self.image_path = image_path
        self.font_path = font_path
        self.update_interval = update_interval
        self.num_layers = num_layers
        self.processor = None
        self.model = None
        self.original_image = None
        self.depth_map = None
        self.layers = []  # List of (layer_image, depth_value) tuples
        self.clock_layer_index = (
            2  # Which layer to place clock (0=back, num_layers=front)
        )
        self.font = None
        self.running = False
        self.update_thread = None
        self.icon = None

        # Create output directory
        self.output_dir = Path(
            r"C:\Users\malmi\OneDrive\Documents\Python\wallpaper_engin"
        )
        self.output_dir.mkdir(exist_ok=True)
        self.wallpaper_path = self.output_dir / "current_wallpaper.jpg"
        self.cache_dir = self.output_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)

    def initialize(self):
        """Load models and process image (ONE-TIME ONLY)"""
        print("\n" + "=" * 60)
        print("INITIALIZING DEPTH WALLPAPER ENGINE")
        print("=" * 60)

        print("\n[1/5] Loading image...")
        self.original_image = Image.open(self.image_path).convert("RGBA")
        width, height = self.original_image.size
        print(f"      Image size: {width}x{height}")

        # Try to load cached layers first
        if self._load_cached_layers():
            print("\nâœ“ Loaded pre-processed layers from cache!")
            self._load_font()
            return

        print("\n[2/5] Loading AI depth model...")
        print("      (This only happens once!)")
        self.processor = AutoImageProcessor.from_pretrained(
            "depth-anything/Depth-Anything-V2-Small-hf"
        )
        self.model = AutoModelForDepthEstimation.from_pretrained(
            "depth-anything/Depth-Anything-V2-Small-hf"
        )

        print("\n[3/5] Generating depth map with AI...")
        print("      (Processing...)")
        self.depth_map = self._get_depth_map()
        print("      âœ“ Depth map generated!")

        print(f"\n[4/5] Creating {self.num_layers} depth layers...")
        self._create_multi_layers()
        print(f"      âœ“ Created {len(self.layers)} layers!")

        # Save layers to cache
        self._save_layers_to_cache()

        print("\n[5/5] Loading font...")
        self._load_font()

        # Clear model from memory
        del self.model
        del self.processor
        torch.cuda.empty_cache() if torch.cuda.is_available() else None

        print("\n" + "=" * 60)
        print("âœ“ INITIALIZATION COMPLETE!")
        print("=" * 60)
        print(
            f"Clock will be placed at layer {self.clock_layer_index + 1}/{self.num_layers}"
        )
        print("Now only the clock updates - NO MORE AI PROCESSING!")
        print("=" * 60 + "\n")

    def _load_font(self):
        """Load font for clock display"""
        width, height = self.original_image.size
        try:
            if self.font_path and os.path.exists(self.font_path):
                self.font = ImageFont.truetype(self.font_path, int(height * 0.15))
            else:
                font_options = [
                    "C:\\Windows\\Fonts\\arial.ttf",
                    "C:\\Windows\\Fonts\\calibrib.ttf",
                    "C:\\Windows\\Fonts\\segoeuib.ttf",
                ]
                for font_option in font_options:
                    if os.path.exists(font_option):
                        self.font = ImageFont.truetype(font_option, int(height * 0.15))
                        break
                else:
                    self.font = ImageFont.load_default()
        except Exception as e:
            print(f"      Font loading error: {e}. Using default font.")
            self.font = ImageFont.load_default()
        print("      âœ“ Font loaded!")

    def _get_depth_map(self):
        """Generate depth map from the original image (ONCE)"""
        image_rgb = self.original_image.convert("RGB")
        inputs = self.processor(images=image_rgb, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)
            predicted_depth = outputs.predicted_depth

        prediction = torch.nn.functional.interpolate(
            predicted_depth.unsqueeze(1),
            size=self.original_image.size[::-1],
            mode="bicubic",
            align_corners=False,
        )

        output = prediction.squeeze().cpu().numpy()
        output = (output - output.min()) / (output.max() - output.min())

        return output

    def _create_multi_layers(self):
        """Create multiple depth layers (ONCE)"""
        self.layers = []

        # Create depth thresholds for each layer
        thresholds = np.linspace(0, 1, self.num_layers + 1)

        for i in range(self.num_layers):
            min_depth = thresholds[i]
            max_depth = thresholds[i + 1]

            # Create mask for this depth range
            if i == 0:  # Background (furthest)
                mask_array = (self.depth_map <= max_depth).astype(np.uint8) * 255
            elif i == self.num_layers - 1:  # Foreground (closest)
                mask_array = (self.depth_map > min_depth).astype(np.uint8) * 255
            else:  # Middle layers
                mask_array = (
                    (self.depth_map > min_depth) & (self.depth_map <= max_depth)
                ).astype(np.uint8) * 255

            # Smooth edges
            mask = Image.fromarray(mask_array, mode="L")
            mask = mask.filter(ImageFilter.GaussianBlur(radius=2))

            # Create layer
            layer = Image.new("RGBA", self.original_image.size, (0, 0, 0, 0))
            layer.paste(self.original_image, (0, 0))
            layer.putalpha(mask)

            self.layers.append(
                {
                    "image": layer,
                    "depth_range": (min_depth, max_depth),
                    "name": (
                        f"Layer {i+1}"
                        if i > 0 and i < self.num_layers - 1
                        else ("Background" if i == 0 else "Foreground")
                    ),
                }
            )

            print(
                f"      Layer {i+1}/{self.num_layers}: {self.layers[i]['name']} (depth {min_depth:.2f}-{max_depth:.2f})"
            )

    def _save_layers_to_cache(self):
        """Save processed layers to cache for faster startup next time"""
        try:
            print("\n      Saving layers to cache...")
            cache_file = self.cache_dir / f"{Path(self.image_path).stem}_layers.json"

            # Save layer metadata
            metadata = {
                "num_layers": self.num_layers,
                "image_path": str(self.image_path),
                "layers": [],
            }

            for i, layer_data in enumerate(self.layers):
                layer_path = (
                    self.cache_dir / f"{Path(self.image_path).stem}_layer_{i}.png"
                )
                layer_data["image"].save(str(layer_path))
                metadata["layers"].append(
                    {
                        "path": str(layer_path),
                        "depth_range": layer_data["depth_range"],
                        "name": layer_data["name"],
                    }
                )

            with open(cache_file, "w") as f:
                json.dump(metadata, f)

            print("      âœ“ Layers cached for faster startup next time!")
        except Exception as e:
            print(f"      Warning: Could not save cache: {e}")

    def _load_cached_layers(self):
        """Try to load pre-processed layers from cache"""
        try:
            cache_file = self.cache_dir / f"{Path(self.image_path).stem}_layers.json"
            if not cache_file.exists():
                return False

            print("\n      Found cached layers! Loading...")

            with open(cache_file, "r") as f:
                metadata = json.load(f)

            if metadata["num_layers"] != self.num_layers:
                print("      Layer count mismatch - will regenerate")
                return False

            self.layers = []
            for layer_meta in metadata["layers"]:
                layer_image = Image.open(layer_meta["path"])
                self.layers.append(
                    {
                        "image": layer_image,
                        "depth_range": tuple(layer_meta["depth_range"]),
                        "name": layer_meta["name"],
                    }
                )

            return True

        except Exception as e:
            print(f"      Could not load cache: {e}")
            return False

    def set_clock_layer(self, layer_index):
        """Set which layer the clock appears at (0=back, num_layers-1=front)"""
        if 0 <= layer_index < self.num_layers:
            self.clock_layer_index = layer_index
            print(f"Clock layer set to: {self.layers[layer_index]['name']}")
        else:
            print(f"Invalid layer index! Must be 0-{self.num_layers-1}")

    def _get_realtime_clock(self):
        """Get current time as formatted string"""
        now = datetime.datetime.now()
        return now.strftime("%H:%M")

    def create_wallpaper_frame(self):
        """Create wallpaper with current time (FAST - no AI processing!)"""
        width, height = self.original_image.size
        current_time = self._get_realtime_clock()

        # Create canvas
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        # Composite layers BEFORE clock layer
        for i in range(self.clock_layer_index + 1):
            canvas.alpha_composite(self.layers[i]["image"], (0, 0))

        # Create and add clock layer
        text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        # Draw time
        text_bbox = draw.textbbox((0, 0), current_time, font=self.font)
        text_width = text_bbox[2] - text_bbox[0]
        position = ((width - text_width) // 2, int(height * 0.25))

        # Shadow
        shadow_offset = 4
        draw.text(
            (position[0] + shadow_offset, position[1] + shadow_offset),
            current_time,
            fill=(0, 0, 0, 120),
            font=self.font,
        )
        # Main text
        draw.text(position, current_time, fill=(255, 255, 255, 255), font=self.font)

        # Draw date
        date_text = datetime.datetime.now().strftime("%a %b %d")
        try:
            date_font = ImageFont.truetype(self.font.path, int(height * 0.03))
        except:
            date_font = self.font

        date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
        date_width = date_bbox[2] - date_bbox[0]
        date_position = ((width - date_width) // 2, position[1] - int(height * 0.05))
        draw.text(date_position, date_text, fill=(255, 255, 255, 200), font=date_font)

        canvas.alpha_composite(text_layer, (0, 0))

        # Composite layers AFTER clock layer
        for i in range(self.clock_layer_index + 1, self.num_layers):
            canvas.alpha_composite(self.layers[i]["image"], (0, 0))

        # Save
        canvas.convert("RGB").save(str(self.wallpaper_path), quality=95)

        return canvas

    def set_windows_wallpaper(self, image_path):
        """Set image as Windows wallpaper"""
        try:
            abs_path = str(Path(image_path).resolve())
            SPI_SETDESKWALLPAPER = 0x0014
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02

            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, abs_path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            return result
        except Exception as e:
            print(f"Error setting wallpaper: {e}")
            return False

    def update_loop(self):
        """Main update loop - FAST because no AI processing!"""
        while self.running:
            try:
                start_time = time.time()

                self.create_wallpaper_frame()
                self.set_windows_wallpaper(self.wallpaper_path)

                elapsed = time.time() - start_time
                print(
                    f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Wallpaper updated in {elapsed:.2f}s"
                )

                time.sleep(self.update_interval)

            except Exception as e:
                print(f"Error in update loop: {e}")
                time.sleep(5)

    def start(self):
        """Start the wallpaper engine"""
        if self.running:
            print("Engine already running!")
            return

        print("\nStarting wallpaper engine...")
        self.running = True

        # Create initial wallpaper
        self.create_wallpaper_frame()
        self.set_windows_wallpaper(self.wallpaper_path)

        # Start update thread
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()

        print(f"âœ“ Engine started! Clock updates every {self.update_interval}s")
        print("  (No AI processing - updates are instant!)\n")

    def stop(self):
        """Stop the wallpaper engine"""
        print("Stopping engine...")
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)
        print("âœ“ Engine stopped!")

    def export_debug_images(self):
        """Export all layers for debugging"""
        print("\nExporting debug images...")
        for i, layer_data in enumerate(self.layers):
            output_path = self.output_dir / f"layer_{i}_{layer_data['name']}.png"
            layer_data["image"].save(str(output_path))
            print(f"  Saved: {output_path}")
        print("âœ“ Debug export complete!")

    def create_tray_icon(self):
        """Create system tray icon"""
        icon_image = PILImage.new("RGB", (64, 64), color=(33, 150, 243))
        draw = ImageDraw.Draw(icon_image)
        draw.text((8, 20), "DW", fill="white", font=ImageFont.load_default())

        def on_quit(icon, item):
            self.stop()
            icon.stop()

        def on_update_now(icon, item):
            self.create_wallpaper_frame()
            self.set_windows_wallpaper(self.wallpaper_path)
            print("Wallpaper updated!")

        def change_clock_layer(layer_idx):
            def handler(icon, item):
                self.set_clock_layer(layer_idx)
                self.create_wallpaper_frame()
                self.set_windows_wallpaper(self.wallpaper_path)

            return handler

        # Build layer menu
        layer_menu_items = [
            item(f'{layer_data["name"]} (Layer {i+1})', change_clock_layer(i))
            for i, layer_data in enumerate(self.layers)
        ]

        menu = pystray.Menu(
            item("Depth Wallpaper Engine", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("Update Now", on_update_now),
            item("Clock Position", pystray.Menu(*layer_menu_items)),
            item("Export Layers", lambda: self.export_debug_images()),
            pystray.Menu.SEPARATOR,
            item("Quit", on_quit),
        )

        self.icon = pystray.Icon("depth_wallpaper", icon_image, "Depth Wallpaper", menu)
        self.icon.run()

    def run_with_tray(self):
        """Run with system tray"""
        self.start()
        try:
            self.create_tray_icon()
        except KeyboardInterrupt:
            self.stop()


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("     MULTI-LAYER DEPTH WALLPAPER ENGINE")
    print("     Optimized - AI runs ONCE, clock updates FAST")
    print("=" * 60 + "\n")

    # Configuration
    IMAGE_PATH = "test5.jpg"
    FONT_PATH = None
    UPDATE_INTERVAL = 1  # Update every 1 second (fast!)
    NUM_LAYERS = 5  # More layers = finer depth control
    CLOCK_LAYER = 2  # Which layer to place clock (0=back, 4=front)

    if not os.path.exists(IMAGE_PATH):
        print(f"âŒ Error: Image not found at {IMAGE_PATH}")
        print("Please update IMAGE_PATH in the script\n")
        sys.exit(1)

    # Create engine
    engine = MultiLayerDepthEngine(
        image_path=IMAGE_PATH,
        font_path=FONT_PATH,
        update_interval=UPDATE_INTERVAL,
        num_layers=NUM_LAYERS,
    )

    # Initialize (AI processing happens here - ONCE)
    engine.initialize()
    engine.set_clock_layer(CLOCK_LAYER)

    # Choose mode
    print("\nChoose run mode:")
    print("1. Run with System Tray (Recommended)")
    print("2. Run in Console")
    print("3. Export layers for preview")
    print("4. Test mode (create one wallpaper)")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        engine.run_with_tray()
    elif choice == "2":
        engine.start()
        print("\nPress Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            engine.stop()
    elif choice == "3":
        engine.export_debug_images()
        print(f"\nLayers exported to: {engine.output_dir}")
    elif choice == "4":
        engine.create_wallpaper_frame()
        engine.set_windows_wallpaper(engine.wallpaper_path)
        print(f"\nTest wallpaper created: {engine.wallpaper_path}")
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    main()