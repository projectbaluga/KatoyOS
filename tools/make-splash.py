#!/usr/bin/env python3
"""
tools/make-splash.py

Generates a Plymouth boot splash image (1024x1024 RGBA) with customizable
logo image, OS name text, and tagline text on KatoyOS navy background (3, 6, 22).

Usage:
    python3 tools/make-splash.py \
        --logo assets/katoyos-brand.png \
        --name "KatoyOS" \
        --tagline "Stable. Rapid. Resilient." \
        --out stage-katoy/01-branding/files/plymouth-splash.png
"""
import argparse
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NAVY_BG = (3, 6, 22)
CANVAS_SIZE = 1024


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


def get_font(font_names, size):
    """Attempts to load a font from candidate names or paths, falling back to default."""
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            continue
    return ImageFont.load_default()


def fit_text_font(font_names, text, max_w, max_h, start_size, min_size=12):
    """Finds the largest font size within constraints that fits the text."""
    for sz in range(start_size, min_size - 1, -2):
        font = get_font(font_names, sz)
        if not hasattr(font, "size"):
            return font
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h:
            return font
    return get_font(font_names, min_size)


def extract_logo(logo_path):
    """
    Loads and prepares the logo image.
    Supports transparent background PNGs directly or uses luminance-to-alpha
    conversion for dark line-art logos on white/opaque backgrounds.
    If multiple stacked components are found (e.g. oyster + brand text row),
    extracts the top icon/symbol.
    """
    raw_img = Image.open(logo_path)
    w, h = raw_img.size

    has_alpha = False
    if raw_img.mode in ("RGBA", "LA") or (raw_img.mode == "P" and "transparency" in raw_img.info):
        alpha_channel = raw_img.convert("RGBA").getchannel("A")
        if alpha_channel.getextrema()[0] < 255:
            has_alpha = True

    if has_alpha:
        img_rgba = raw_img.convert("RGBA")
        alpha = img_rgba.getchannel("A")
        # Check if the non-transparent artwork is dark line-art
        gray = img_rgba.convert("L")
        alpha_bytes = alpha.tobytes()
        gray_bytes = gray.tobytes()
        opaque_lums = [g for a, g in zip(alpha_bytes, gray_bytes) if a > 30]
        if opaque_lums and (sum(opaque_lums) / len(opaque_lums)) < 128:
            logo_rgba = recolor_with_alpha(alpha, (255, 255, 255))
        else:
            logo_rgba = img_rgba
    else:
        gray = raw_img.convert("L")
        alpha = gray.point(lum_to_alpha)
        logo_rgba = recolor_with_alpha(alpha, (255, 255, 255))

    # Detect any vertical separation between rows (e.g. oyster symbol above text row)
    alpha_bytes = logo_rgba.getchannel("A").tobytes()
    row_counts = [
        sum(1 for b in alpha_bytes[y * w : (y + 1) * w] if b > 0)
        for y in range(h)
    ]
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
        top_y0, top_y1 = ranges[0]
        cropped_logo = logo_rgba.crop((0, top_y0, w, top_y1 + 1))
    elif len(ranges) == 1:
        top_y0, top_y1 = ranges[0]
        cropped_logo = logo_rgba.crop((0, top_y0, w, top_y1 + 1))
    else:
        cropped_logo = logo_rgba

    bbox = cropped_logo.getbbox()
    if bbox is not None:
        cropped_logo = cropped_logo.crop(bbox)

    return cropped_logo


def make_splash(logo_path, os_name, tagline, out_path):
    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (*NAVY_BG, 255))

    # Upper ~65% region for logo: y from 0 to 665
    upper_h = int(CANVAS_SIZE * 0.65)
    logo_img = extract_logo(logo_path)
    lw, lh = logo_img.size

    # Scale logo to fit comfortably in upper 65% (max w ~ 700, max h ~ 520)
    max_logo_w = 700
    max_logo_h = int(upper_h * 0.82)  # ~545px
    scale = min(max_logo_w / lw, max_logo_h / lh, 1.0)
    # If original logo was small, allow scaling up proportionally
    if lw < max_logo_w and lh < max_logo_h:
        scale = min(max_logo_w / lw, max_logo_h / lh)

    target_lw = max(1, int(lw * scale))
    target_lh = max(1, int(lh * scale))
    scaled_logo = logo_img.resize((target_lw, target_lh), Image.Resampling.LANCZOS)

    # Center logo in upper ~65%
    logo_x = (CANVAS_SIZE - target_lw) // 2
    logo_y = (upper_h - target_lh) // 2 + int(upper_h * 0.05)
    canvas.alpha_composite(scaled_logo, (logo_x, logo_y))

    draw = ImageDraw.Draw(canvas)

    # Text area: from upper_h downwards
    bold_font_candidates = [
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    reg_font_candidates = [
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    has_tagline = bool(tagline and tagline.strip())

    if os_name and os_name.strip():
        name_text = os_name.strip()
        max_name_w = 850
        max_name_h = 90 if has_tagline else 120
        start_sz = 72 if has_tagline else 80
        name_font = fit_text_font(bold_font_candidates, name_text, max_name_w, max_name_h, start_size=start_sz, min_size=16)

        n_bbox = draw.textbbox((0, 0), name_text, font=name_font)
        nw = n_bbox[2] - n_bbox[0]
        nh = n_bbox[3] - n_bbox[1]

        if has_tagline:
            name_y = upper_h + 30
        else:
            name_y = upper_h + (CANVAS_SIZE - upper_h - nh) // 2 - 10

        name_x = (CANVAS_SIZE - nw) // 2 - n_bbox[0]
        name_y_draw = name_y - n_bbox[1]
        draw.text((name_x, name_y_draw), name_text, font=name_font, fill=(255, 255, 255, 255))
        last_bottom = name_y + nh
    else:
        last_bottom = upper_h + 30

    if has_tagline:
        tagline_text = tagline.strip()
        max_tag_w = 880
        max_tag_h = 50
        tag_font = fit_text_font(reg_font_candidates, tagline_text, max_tag_w, max_tag_h, start_size=32, min_size=12)

        t_bbox = draw.textbbox((0, 0), tagline_text, font=tag_font)
        tw = t_bbox[2] - t_bbox[0]
        th = t_bbox[3] - t_bbox[1]

        tag_y = last_bottom + 22
        tag_x = (CANVAS_SIZE - tw) // 2 - t_bbox[0]
        tag_y_draw = tag_y - t_bbox[1]
        draw.text((tag_x, tag_y_draw), tagline_text, font=tag_font, fill=(220, 225, 240, 230))

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_file, "PNG")
    print(f"Generated splash image: {out_file} ({CANVAS_SIZE}x{CANVAS_SIZE})")


def main():
    root = Path(__file__).resolve().parent.parent
    default_logo = root / "assets/katoyos-brand.png"
    default_out = root / "stage-katoy/01-branding/files/plymouth-splash.png"

    parser = argparse.ArgumentParser(description="Generate customizable Plymouth boot splash.")
    parser.add_argument("--logo", default=str(default_logo), help=f"Path to logo image (default: {default_logo})")
    parser.add_argument("--name", default="KatoyOS", help="OS name text to render in bold (default: KatoyOS)")
    parser.add_argument("--tagline", default="", help="Optional tagline text to render under name")
    parser.add_argument("--out", default=str(default_out), help=f"Path to output PNG (default: {default_out})")

    args = parser.parse_args()

    logo_path = Path(args.logo)
    if not logo_path.exists():
        print(f"Error: logo image not found at {logo_path}", file=sys.stderr)
        sys.exit(1)

    make_splash(logo_path, args.name, args.tagline, args.out)


if __name__ == "__main__":
    main()
