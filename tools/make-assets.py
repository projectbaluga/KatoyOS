#!/usr/bin/env python3
"""
Regenerates all derived KatoyOS brand assets from assets/katoyos-brand.png.
Produces:
  - stage-katoy/01-branding/files/wallpaper.png (1920x1080, Windows 11 style "bloom")
  - stage-katoy/01-branding/files/plymouth-splash.png (1280px wide)
  - stage-katoy/01-branding/files/katoyos-256.png (256x256 icon)
  - stage-katoy/01-branding/files/katoyos-64.png (64x64 icon)
"""
import math
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
BRAND_PATH = ROOT / "assets/katoyos-brand.png"
DEST_DIR = ROOT / "stage-katoy/01-branding/files"

def make_bloom(w, h):
    """Soft layered petals on a deep-blue gradient, in the spirit of the Windows 11 look."""
    top, bottom = (3, 14, 38), (6, 40, 98)
    base = Image.new("RGB", (w, h))
    px = base.load()
    for y in range(h):
        t = y / (h - 1)
        row = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = row

    cx, cy = int(w * 0.5), int(h * 0.56)
    petal_len, petal_w = int(h * 0.50), int(h * 0.11)
    colors = [(0, 90, 200), (40, 140, 255), (20, 60, 190), (90, 190, 255)]
    layer = Image.new("RGB", (w, h), (0, 0, 0))
    for ring, scale in enumerate((1.0, 0.62)):
        for k in range(8):
            petal = Image.new("L", (w, h), 0)
            d = ImageDraw.Draw(petal)
            r = petal_len * scale
            pw = petal_w * scale
            d.ellipse([cx - pw, cy - r, cx + pw, cy], fill=255)
            petal = petal.rotate(k * 45 + ring * 22.5, center=(cx, cy), resample=Image.Resampling.BICUBIC)
            petal = petal.filter(ImageFilter.GaussianBlur(12))
            tint = Image.new("RGB", (w, h), colors[(k + ring) % len(colors)])
            layer = ImageChops.screen(layer, Image.composite(tint, Image.new("RGB", (w, h)), petal.point(lambda v: int(v * (0.50 if ring else 0.38)))))

    glow = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=150)
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    layer = ImageChops.screen(layer, Image.composite(Image.new("RGB", (w, h), (170, 225, 255)), Image.new("RGB", (w, h)), glow))

    out = ImageChops.screen(base, layer).convert("RGBA")
    return out


def main():
    if not BRAND_PATH.exists():
        print(f"Error: Brand image not found at {BRAND_PATH}", file=sys.stderr)
        sys.exit(1)

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    brand = Image.open(BRAND_PATH).convert("RGBA")
    bw, bh = brand.size

    # 1. Wallpaper: 1920x1080 abstract blue bloom (original artwork, no logo, so the desktop stays clean)
    make_bloom(1920, 1080).save(DEST_DIR / "wallpaper.png", "PNG")
    print("Generated wallpaper.png (1920x1080)")

    # 2. Plymouth Splash: 1280px wide, keep aspect ratio
    splash_w = 1280
    splash_h = int(bh * (splash_w / bw))
    splash = brand.resize((splash_w, splash_h), Image.Resampling.LANCZOS)
    splash.save(DEST_DIR / "plymouth-splash.png", "PNG")
    print(f"Generated plymouth-splash.png ({splash_w}x{splash_h})")

    # 3. App/panel icon: crop (305,0,725,398), paste onto 420x420 filled (3,6,22) at y offset 22
    cropped = brand.crop((305, 0, 725, 398))
    cw, ch = cropped.size
    icon_bg = Image.new("RGBA", (420, 420), (3, 6, 22, 255))
    paste_x = (420 - cw) // 2
    icon_bg.paste(cropped, (paste_x, 22), cropped)

    # Upscale to 512, apply rounded-rectangle alpha mask (radius ~110)
    icon_512 = icon_bg.resize((512, 512), Image.Resampling.LANCZOS)
    mask = Image.new("L", (512, 512), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, 512, 512], radius=110, fill=255)

    icon_rounded = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    icon_rounded.paste(icon_512, (0, 0), mask)

    # Export 256px and 64px PNGs
    icon_256 = icon_rounded.resize((256, 256), Image.Resampling.LANCZOS)
    icon_256.save(DEST_DIR / "katoyos-256.png", "PNG")
    print("Generated katoyos-256.png")

    icon_64 = icon_rounded.resize((64, 64), Image.Resampling.LANCZOS)
    icon_64.save(DEST_DIR / "katoyos-64.png", "PNG")
    print("Generated katoyos-64.png")

if __name__ == "__main__":
    main()
