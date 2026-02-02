from rembg import remove
from PIL import Image

wallpaper = Image.open("test.jpg").convert("RGBA")

# Extract foreground (subject)
foreground = remove(wallpaper)

# Background remains unchanged
background = wallpaper.copy()

background.save("background.png")
foreground.save("foreground.png")

print("Layers saved successfully")
