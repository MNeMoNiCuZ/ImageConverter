"""Generate a programmatic icon for Image Converter and save as icon.ico."""

import os
from PIL import Image, ImageDraw


def generate_icon():
    """Create an icon with small overlapping frames and a large conversion arrow."""
    sizes = [16, 32, 48, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        pad = max(1, size // 16)
        r = max(1, size // 16)
        w = max(1, size // 32)

        # Small back frame — folder-icon yellow
        bx1, by1 = size * 2 // 5, pad
        bx2, by2 = size * 3 // 4, size * 2 // 5
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=r,
                               fill=(240, 200, 60, 220), outline=(200, 160, 20, 255), width=w)

        # Small front frame — blue
        fx1, fy1 = pad, size // 4
        fx2, fy2 = size * 2 // 5, size * 3 // 5
        draw.rounded_rectangle([fx1, fy1, fx2, fy2], radius=r,
                               fill=(100, 160, 220, 220), outline=(60, 120, 180, 255), width=w)

        # Large arrow spanning most of the icon (left-to-right, centered vertically)
        arrow_y = size * 3 // 5
        shaft_x1 = size // 6
        shaft_x2 = size * 3 // 4
        arrow_w = max(2, size // 6)
        # Shaft
        draw.line([(shaft_x1, arrow_y), (shaft_x2, arrow_y)],
                  fill=(255, 255, 255, 245), width=arrow_w)
        # Arrowhead
        head_size = max(3, size // 4)
        draw.polygon([
            (size - pad, arrow_y),
            (shaft_x2 - max(1, size // 16), arrow_y - head_size // 2),
            (shaft_x2 - max(1, size // 16), arrow_y + head_size // 2),
        ], fill=(255, 255, 255, 245))

        images.append(img)

    ico_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    images[-1].save(ico_path, format="ICO",
                    sizes=[(s, s) for s in sizes],
                    append_images=images[:-1])
    print(f"Icon saved to {ico_path}")
    return ico_path


if __name__ == "__main__":
    generate_icon()
