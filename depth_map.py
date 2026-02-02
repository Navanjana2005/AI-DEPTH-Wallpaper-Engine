import torch
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
import numpy as np
import datetime
import time
import os


def get_depth_map(image_path):
    print("Loading image...")
    image = Image.open(image_path)

    print("Loading depth map model....")
    processor = AutoImageProcessor.from_pretrained(
        "depth-anything/Depth-Anything-V2-Small-hf"
    )
    model = AutoModelForDepthEstimation.from_pretrained(
        "depth-anything/Depth-Anything-V2-Small-hf"
    )

    inputs = processor(images=image, return_tensors="pt")

    print("Generating depth map....")

    with torch.no_grad():
        outputs = model(**inputs)
        predicted_depth = outputs.predicted_depth

    prediction = torch.nn.functional.interpolate(
        predicted_depth.unsqueeze(1),
        size=image.size[::-1],
        mode="bicubic",
        align_corners=False,
    )

    output = prediction.squeeze().cpu().numpy()
    formatted = (output * 255 / np.max(output)).astype("uint8")
    return Image.fromarray(formatted)


def getting_realtime_clock():
    now = datetime.datetime.now()
    return now.strftime("%H:%M:%S")


def create_depth_wallpaper(image_path, realtime_clock):
    original_image = Image.open(image_path).convert("RGBA")
    width, height = original_image.size

    print("Recognizing the background and foreground...")

    foreground = remove(original_image).convert("RGBA")

    # Create base with original image
    combined = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    combined.paste(original_image, (0, 0), original_image)

    try:
        font = ImageFont.truetype("test.ttf", int(height * 0.2))
    except:
        font = ImageFont.load_default()

    # Create text layer
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    text_bbox = draw.textbbox((0, 0), realtime_clock, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    position = ((width - text_width) // 2, (height // 4))

    draw.text(position, realtime_clock, fill="white", font=font)

    # Composite layers: background -> text -> foreground
    combined.alpha_composite(text_layer, (0, 0))
    combined.alpha_composite(foreground, (0, 0))

    combined.convert("RGB").save("output_image.png")
    print("Successfully saved image with clock overlay as output_image.png")
