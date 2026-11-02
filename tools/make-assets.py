#!/usr/bin/env python3
"""
Regenerates all derived KatoyOS brand assets from assets/katoyos-brand.png.

WARNING: this OVERWRITES the committed wallpaper, boot splash and icons, including any that
were edited by hand. It is therefore NOT part of the build; run it only on purpose:
    python3 tools/make-assets.py --force

Produces:
  - stage-katoy/01-branding/files/wallpaper.png (1920x1080)
  - stage-katoy/01-branding/files/plymouth-splash.png (centered splash image)
  - stage-katoy/01-branding/files/katoyos-256.png (256x256 icon)
  - stage-katoy/01-branding/files/katoyos-64.png (64x64 icon)
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
BRAND_PATH = ROOT / "assets/katoyos-brand.png"
DEST_DIR = ROOT / "stage-katoy/01-branding/files"

# Standard KatoyOS navy background
NAVY_BG = (3, 6, 22)

def lum_to_alpha(p):
    """
    Converts white background to transparent using luminance.
    Dark lines (p <= 40) become fully opaque (alpha = 255).
    White background (p >= 245) becomes fully transparent (alpha = 0).
    Smooth transition for anti-aliased edges.
    """
    if p >= 245:
        return 0
    if p <= 40:
        return 255
    return int(255 * (245 - p) / (245 - 40))

def recolor_with_alpha(alpha_img, rgb_color):
    """Creates an RGBA image filled with rgb_color and masked with alpha_img."""
    img = Image.new("RGBA", alpha_img.size, (*rgb_color, 0))
    img.putalpha(alpha_img)
    return img

def main():
    if "--force" not in sys.argv[1:]:
        sys.exit("Refusing to overwrite the committed brand assets (splash, wallpaper, icons).\n"
                 "Run with --force if you really want to regenerate them from assets/katoyos-brand.png.")
    if not BRAND_PATH.exists():
        print(f"Error: Brand image not found at {BRAND_PATH}", file=sys.stderr)
        sys.exit(1)

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    brand_raw = Image.open(BRAND_PATH)
    gray = brand_raw.convert("L")
    w, h = gray.size

    # Alpha mask from luminance: dark lines become opaque
    alpha = gray.point(lum_to_alpha)

    # 1. Wallpaper: 1920x1080 solid KatoyOS navy (3, 6, 22)
    # Recolor logo lines to white and center logo at ~60% screen height
    wp_w, wp_h = 1920, 1080
    wallpaper = Image.new("RGBA", (wp_w, wp_h), (*NAVY_BG, 255))

    target_logo_h = int(wp_h * 0.60)  # ~648px
    logo_scale = target_logo_h / h
    target_logo_w = int(w * logo_scale)

    white_logo = recolor_with_alpha(alpha, (255, 255, 255))
    resized_logo = white_logo.resize((target_logo_w, target_logo_h), Image.Resampling.LANCZOS)

    wp_x = (wp_w - target_logo_w) // 2
    wp_y = (wp_h - target_logo_h) // 2
    wallpaper.alpha_composite(resized_logo, (wp_x, wp_y))
    wallpaper.save(DEST_DIR / "wallpaper.png", "PNG")
    print(f"Generated wallpaper.png ({wp_w}x{wp_h})")

    # 2. Plymouth Splash: light-on-dark logo centered on dark background
    # plymouth/katoyos.script auto-scales and centers the splash image on boot.
    # We provide a 1024x1024 splash with the light logo on transparent / navy background.
    splash = Image.new("RGBA", (w, h), (*NAVY_BG, 255))
    splash.alpha_composite(white_logo, (0, 0))
    splash.save(DEST_DIR / "plymouth-splash.png", "PNG")
    print(f"Generated plymouth-splash.png ({w}x{h})")

    # 3. Icons (256x256 and 64x64): oyster only, without 'KatoyOS' text.
    # Automatically locate the oyster bounding box above the text row without hardcoded crops.
    # Count non-zero alpha pixels per row to identify the gap between the oyster and text.
    row_counts = [sum(1 for x in range(w) if alpha.getpixel((x, y)) > 0) for y in range(h)]
    ranges = []
    start = None
    for y, count in enumerate(row_counts):
        if count > 0 and start is None:
            start = y
        elif count == 0 and start is not None:
            ranges.append((start, y - 1))
            start = None
    if start is not None:
        ranges.append((start, h - 1))

    if len(ranges) >= 2:
        oyster_y0, oyster_y1 = ranges[0]
    elif len(ranges) == 1:
        oyster_y0, oyster_y1 = ranges[0]
    else:
        oyster_y0, oyster_y1 = 0, h - 1

    # Crop the oyster's non-transparent bounding box
    oyster_alpha = Image.new("L", (w, h), 0)
    oyster_alpha.paste(alpha.crop((0, oyster_y0, w, oyster_y1 + 1)), (0, oyster_y0))
    bbox = oyster_alpha.getbbox()
    if bbox is None:
        bbox = (0, 0, w, h)
    crop_oyster = oyster_alpha.crop(bbox)
    cw, ch = crop_oyster.size

    # Pad to a square so oyster stays well-proportioned with comfortable padding
    pad_ratio = 0.12  # ~12% padding on each side
    max_side = max(cw, ch)
    square_side = int(max_side / (1 - 2 * pad_ratio))

    square_alpha = Image.new("L", (square_side, square_side), 0)
    square_alpha.paste(crop_oyster, ((square_side - cw) // 2, (square_side - ch) // 2))

    # Base rounded-rectangle icon: KatoyOS navy background with white lines
    icon_canvas = Image.new("RGBA", (square_side, square_side), (*NAVY_BG, 255))
    white_oyster = Image.new("RGBA", (square_side, square_side), (255, 255, 255, 0))
    white_oyster.putalpha(square_alpha)
    icon_canvas.alpha_composite(white_oyster)

    # Rounded-rectangle alpha mask (corner radius ~22%)
    mask = Image.new("L", (square_side, square_side), 0)
    mask_draw = ImageDraw.Draw(mask)
    corner_radius = int(square_side * 0.22)
    mask_draw.rounded_rectangle([0, 0, square_side, square_side], radius=corner_radius, fill=255)

    icon_rounded = Image.new("RGBA", (square_side, square_side), (0, 0, 0, 0))
    icon_rounded.paste(icon_canvas, (0, 0), mask)

    # Export 256px and 64px PNGs
    icon_256 = icon_rounded.resize((256, 256), Image.Resampling.LANCZOS)
    icon_256.save(DEST_DIR / "katoyos-256.png", "PNG")
    print("Generated katoyos-256.png (256x256)")

    # Also keep plymouth-logo.png updated if present
    icon_256.save(DEST_DIR / "plymouth-logo.png", "PNG")

    icon_64 = icon_rounded.resize((64, 64), Image.Resampling.LANCZOS)
    icon_64.save(DEST_DIR / "katoyos-64.png", "PNG")
    print("Generated katoyos-64.png (64x64)")

if __name__ == "__main__":
    main()
