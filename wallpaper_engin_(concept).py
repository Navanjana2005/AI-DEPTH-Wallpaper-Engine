import torch
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import datetime
import time
import os


class DepthWallpaperEngine:
    def __init__(self, image_path, font_path=None, update_interval=1, depth_threshold=0.5):
        """
        Initialize the wallpaper engine with depth-based segmentation
        
        Args:
            image_path: Path to the input image
            font_path: Path to TTF font file (optional)
            update_interval: Seconds between updates (default: 1)
            depth_threshold: Threshold for foreground/background split (0-1, default: 0.5)
        """
        self.image_path = image_path
        self.font_path = font_path
        self.update_interval = update_interval
        self.depth_threshold = depth_threshold
        self.processor = None
        self.model = None
        self.original_image = None
        self.foreground = None
        self.background = None
        self.depth_map = None
        self.depth_mask = None
        self.font = None
        
    def initialize(self):
        """Load models and process image (one-time setup)"""
        print("Loading image...")
        self.original_image = Image.open(self.image_path).convert("RGBA")
        width, height = self.original_image.size
        
        print("Loading depth estimation model...")
        self.processor = AutoImageProcessor.from_pretrained(
            "depth-anything/Depth-Anything-V2-Small-hf"
        )
        self.model = AutoModelForDepthEstimation.from_pretrained(
            "depth-anything/Depth-Anything-V2-Small-hf"
        )
        
        print("Generating depth map...")
        self.depth_map = self._get_depth_map()
        
        print("Creating depth-based segmentation...")
        self._create_depth_layers()
        
        # Load font
        try:
            if self.font_path and os.path.exists(self.font_path):
                self.font = ImageFont.truetype(self.font_path, int(height * 0.15))
            else:
                # Try common system fonts
                font_options = [
                    "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
                    "C:\\Windows\\Fonts\\arial.ttf",  # Windows
                ]
                for font_option in font_options:
                    if os.path.exists(font_option):
                        self.font = ImageFont.truetype(font_option, int(height * 0.15))
                        break
                else:
                    self.font = ImageFont.load_default()
                    print("Warning: Using default font. For better results, provide a TTF font.")
        except Exception as e:
            print(f"Font loading error: {e}. Using default font.")
            self.font = ImageFont.load_default()
            
        print("Initialization complete!")
        
    def _get_depth_map(self):
        """Generate depth map from the original image"""
        # Convert RGBA to RGB for depth estimation
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
        
        # Normalize to 0-1 range
        output = (output - output.min()) / (output.max() - output.min())
        
        return output
    
    def _create_depth_layers(self):
        """Create foreground and background layers using depth map"""
        # Create binary mask based on depth threshold
        # Higher depth values = closer to camera (foreground)
        mask_array = (self.depth_map > self.depth_threshold).astype(np.uint8) * 255
        
        # Apply morphological operations to clean up the mask
        mask = Image.fromarray(mask_array, mode='L')
        
        # Slight blur to smooth edges (removes harsh transitions)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=2))
        
        # Optional: erode slightly to avoid edge artifacts
        # mask = mask.filter(ImageFilter.MinFilter(3))
        
        self.depth_mask = mask
        
        # Create foreground layer (closer objects)
        self.foreground = Image.new("RGBA", self.original_image.size, (0, 0, 0, 0))
        self.foreground.paste(self.original_image, (0, 0))
        self.foreground.putalpha(mask)
        
        # Create background layer (farther objects)
        # Invert the mask for background
        bg_mask = Image.fromarray(255 - np.array(mask), mode='L')
        self.background = Image.new("RGBA", self.original_image.size, (0, 0, 0, 0))
        self.background.paste(self.original_image, (0, 0))
        self.background.putalpha(bg_mask)
        
    def adjust_threshold(self, new_threshold):
        """
        Adjust depth threshold and regenerate layers
        
        Args:
            new_threshold: New threshold value (0-1)
                          Lower = more foreground, Higher = less foreground
        """
        self.depth_threshold = new_threshold
        print(f"Adjusting depth threshold to {new_threshold}...")
        self._create_depth_layers()
        print("Layers regenerated!")
    
    def _get_realtime_clock(self):
        """Get current time as formatted string"""
        now = datetime.datetime.now()
        return now.strftime("%H:%M")
    
    def create_frame(self, output_path="output_image.png", save_debug=False):
        """Create a single wallpaper frame with current time"""
        width, height = self.original_image.size
        current_time = self._get_realtime_clock()
        
        # Create base canvas
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        
        # Paste background (far objects)
        canvas.alpha_composite(self.background, (0, 0))
        
        # Create text layer
        text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        # Calculate text position
        text_bbox = draw.textbbox((0, 0), current_time, font=self.font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position text in upper-middle area
        position = ((width - text_width) // 2, int(height * 0.25))
        
        # Draw time with shadow for depth
        shadow_offset = 3
        draw.text((position[0] + shadow_offset, position[1] + shadow_offset), 
                 current_time, fill=(0, 0, 0, 100), font=self.font)
        draw.text(position, current_time, fill=(255, 255, 255, 255), font=self.font)
        
        # Add date
        date_text = datetime.datetime.now().strftime("%a %b %d")
        try:
            date_font = ImageFont.truetype(self.font.path, int(height * 0.03))
        except:
            date_font = self.font
            
        date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
        date_width = date_bbox[2] - date_bbox[0]
        date_position = ((width - date_width) // 2, position[1] - int(height * 0.05))
        draw.text(date_position, date_text, fill=(255, 255, 255, 200), font=date_font)
        
        # Composite: background -> text -> foreground (creates depth effect)
        canvas.alpha_composite(text_layer, (0, 0))
        canvas.alpha_composite(self.foreground, (0, 0))
        
        # Save output
        canvas.convert("RGB").save(output_path)
        print(f"Saved wallpaper: {output_path} [{current_time}]")
        
        # Save debug images
        if save_debug:
            self.depth_map_vis = Image.fromarray(
                (self.depth_map * 255).astype('uint8'), mode='L'
            )
            self.depth_map_vis.save("debug_depth_map.png")
            self.depth_mask.save("debug_mask.png")
            self.foreground.save("debug_foreground.png")
            self.background.save("debug_background.png")
            print("Debug images saved!")
            
        return canvas
    
    def run_continuous(self, output_dir="wallpapers", max_updates=None):
        """
        Run the wallpaper engine continuously
        
        Args:
            output_dir: Directory to save wallpaper updates
            max_updates: Maximum number of updates (None for infinite)
        """
        os.makedirs(output_dir, exist_ok=True)
        
        update_count = 0
        try:
            while max_updates is None or update_count < max_updates:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(output_dir, f"wallpaper_{timestamp}.png")
                
                self.create_frame(output_path)
                update_count += 1
                
                time.sleep(self.update_interval)
        except KeyboardInterrupt:
            print("\nWallpaper engine stopped by user")
        
        print(f"Total updates: {update_count}")


def main():
    """Example usage"""
    # Configuration
    IMAGE_PATH = "test5.jpg"  # Change to your image path
    FONT_PATH = None  # Or specify path to TTF font
    UPDATE_INTERVAL = 60  # Update every 60 seconds
    DEPTH_THRESHOLD = 0.5  # 0-1, adjust based on your image
    
    # Create and initialize engine
    engine = DepthWallpaperEngine(
        image_path=IMAGE_PATH,
        font_path=FONT_PATH,
        update_interval=UPDATE_INTERVAL,
        depth_threshold=DEPTH_THRESHOLD
    )
    
    engine.initialize()
    
    # Create single frame with debug images to check segmentation
    engine.create_frame("output_image.png", save_debug=True)
    
    print("\nCheck the debug images to see if segmentation is good:")
    print("- debug_depth_map.png: Raw depth map")
    print("- debug_mask.png: Binary mask (white=foreground)")
    print("- debug_foreground.png: Extracted foreground")
    print("- debug_background.png: Extracted background")
    print("\nIf segmentation isn't good, adjust threshold:")
    print("  engine.adjust_threshold(0.6)  # More foreground")
    print("  engine.adjust_threshold(0.4)  # Less foreground")
    
    # Uncomment to run continuously
    # engine.run_continuous(max_updates=10)


if __name__ == "__main__":
    main()