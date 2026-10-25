#!/usr/bin/env python3
"""
Generates visual UI previews for KatoyOS documentation:
  - assets/katoyos-desktop-preview.png (1280x720 LXQt Desktop Preview)
  - assets/katoyos-welcome-preview.png (1000x650 KatoyOS Welcome Wizard Preview)
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
BRANDING_DIR = ROOT / "stage-katoy/01-branding/files"

def get_font(size=14, bold=False):
    # Try system fonts, fallback to default PIL font
    try:
        font_names = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for fn in font_names:
            if Path(fn).exists():
                return ImageFont.truetype(fn, size)
    except Exception:
        pass
    return ImageFont.load_default()

def draw_window_header(draw, x, y, width, height, title, active=True):
    header_color = (26, 30, 46) if active else (18, 20, 30)
    border_color = (45, 212, 191) if active else (50, 55, 75)

    # Top header bar
    draw.rectangle([x, y, x + width, y + height], fill=header_color)
    draw.line([x, y, x + width, y], fill=border_color, width=1)

    # Window controls (close, minimize, maximize)
    btn_radius = 5
    cy = y + height // 2
    draw.ellipse([x + width - 18 - btn_radius, cy - btn_radius, x + width - 18 + btn_radius, cy + btn_radius], fill=(239, 68, 68))
    draw.ellipse([x + width - 36 - btn_radius, cy - btn_radius, x + width - 36 + btn_radius, cy + btn_radius], fill=(245, 158, 11))
    draw.ellipse([x + width - 54 - btn_radius, cy - btn_radius, x + width - 54 + btn_radius, cy + btn_radius], fill=(16, 185, 129))

    # Title
    font_title = get_font(13, bold=True)
    draw.text((x + 15, y + (height - 14) // 2), title, fill=(226, 232, 240), font=font_title)

def create_desktop_preview():
    # Base wallpaper
    wp_path = BRANDING_DIR / "wallpaper.png"
    if wp_path.exists():
        bg = Image.open(wp_path).convert("RGBA").resize((1280, 720), Image.Resampling.LANCZOS)
    else:
        bg = Image.new("RGBA", (1280, 720), (10, 12, 26, 255))

    draw = ImageDraw.Draw(bg)
    font_main = get_font(13)
    font_bold = get_font(13, bold=True)
    font_small = get_font(11)

    # 1. QTerminal Window (Center-left)
    tx, ty, tw, th = 60, 60, 680, 440
    # Window background & shadow
    draw.rectangle([tx+4, ty+4, tx+tw+4, ty+th+4], fill=(0, 0, 0, 120))
    draw.rectangle([tx, ty, tx+tw, ty+th], fill=(14, 17, 23, 245), outline=(45, 212, 191), width=1)
    draw_window_header(draw, tx, ty, tw, 30, "qterminal - katoy@katoyos: ~", active=True)

    # Terminal text content
    term_y = ty + 40
    term_x = tx + 15
    term_font = get_font(12)

    lines = [
        ("katoy@katoyos", (45, 212, 191), ":", (255, 255, 255), "~$", (124, 58, 237), " neofetch", (226, 232, 240)),
        ("       .---.         ", (45, 212, 191), "OS: ", (124, 58, 237), "KatoyOS 1.0 (Debian 13 trixie armhf)", (226, 232, 240)),
        ("      /  .  \\        ", (45, 212, 191), "Host: ", (124, 58, 237), "Raspberry Pi 3 Model B Rev 1.2", (226, 232, 240)),
        ("     |  (o)  |       ", (45, 212, 191), "Kernel: ", (124, 58, 237), "linux-image-6.18.50+rpt-rpi-v7", (226, 232, 240)),
        ("      \\  '  /        ", (45, 212, 191), "Uptime: ", (124, 58, 237), "12 mins", (226, 232, 240)),
        ("       '---'         ", (45, 212, 191), "Packages: ", (124, 58, 237), "1142 (dpkg)", (226, 232, 240)),
        ("                     ", (45, 212, 191), "Shell: ", (124, 58, 237), "bash 5.2.37", (226, 232, 240)),
        ("                     ", (45, 212, 191), "Desktop: ", (124, 58, 237), "LXQt 2.1.0 on Openbox (X11)", (226, 232, 240)),
        ("                     ", (45, 212, 191), "Terminal: ", (124, 58, 237), "qterminal", (226, 232, 240)),
        ("                     ", (45, 212, 191), "CPU: ", (124, 58, 237), "ARMv7 Processor rev 4 (v7l) x 4", (226, 232, 240)),
        ("                     ", (45, 212, 191), "Memory: ", (124, 58, 237), "312 MB / 920 MB (Idle RAM)", (16, 185, 129)),
        ("", (0,0,0)),
        ("katoy@katoyos", (45, 212, 191), ":", (255, 255, 255), "~$", (124, 58, 237), " free -h", (226, 232, 240)),
        ("               total        used        free      shared  buff/cache   available", (148, 163, 184)),
        ("Mem:           920Mi       312Mi       410Mi        12Mi       198Mi       580Mi", (226, 232, 240)),
        ("Swap (zram):   512Mi          0B       512Mi", (16, 185, 129)),
        ("katoy@katoyos", (45, 212, 191), ":", (255, 255, 255), "~$", (124, 58, 237), " █", (45, 212, 191)),
    ]

    for row in lines:
        curr_x = term_x
        for i in range(0, len(row), 2):
            text, color = row[i], row[i+1]
            draw.text((curr_x, term_y), text, fill=color, font=term_font)
            bbox = draw.textbbox((curr_x, term_y), text, font=term_font)
            curr_x += (bbox[2] - bbox[0])
        term_y += 20

    # 2. Desktop Notification (Top Right)
    nx, ny, nw, nh = 900, 50, 350, 90
    draw.rectangle([nx, ny, nx+nw, ny+nh], fill=(22, 26, 42, 240), outline=(245, 158, 11), width=1)
    draw.rectangle([nx, ny, nx+5, ny+nh], fill=(245, 158, 11))
    draw.text((nx + 18, ny + 12), "⚡ KatoyOS PowerWatch", fill=(245, 158, 11), font=font_bold)
    draw.text((nx + 18, ny + 34), "Under-voltage detected (bit 0x1)", fill=(226, 232, 240), font=font_bold)
    draw.text((nx + 18, ny + 54), "Use a quality 5V 2.5A power supply & short cable.", fill=(148, 163, 184), font=font_small)

    # 3. Bottom Panel (40px high)
    py = 720 - 40
    draw.rectangle([0, py, 1280, 720], fill=(10, 12, 26, 245))
    draw.line([0, py, 1280, py], fill=(45, 212, 191), width=1)

    # Menu icon
    icon_64_path = BRANDING_DIR / "katoyos-64.png"
    if icon_64_path.exists():
        menu_icon = Image.open(icon_64_path).convert("RGBA").resize((28, 28), Image.Resampling.LANCZOS)
        bg.paste(menu_icon, (8, py + 6), menu_icon)
    else:
        draw.rectangle([8, py+6, 36, py+34], fill=(45, 212, 191))

    # Quicklaunch separators and launchers
    draw.line([44, py + 8, 44, py + 32], fill=(40, 45, 65))

    # Taskbar items
    draw.rectangle([150, py + 4, 340, py + 36], fill=(26, 30, 46), outline=(45, 212, 191), width=1)
    draw.text((165, py + 12), "💻 qterminal - katoy@katoyos", fill=(226, 232, 240), font=font_small)

    draw.rectangle([348, py + 4, 538, py + 36], fill=(18, 20, 32))
    draw.text((363, py + 12), "🚀 Welcome to KatoyOS", fill=(148, 163, 184), font=font_small)

    # Tray items (Right aligned)
    draw.text((1120, py + 12), "📶 Wi-Fi: Connected", fill=(45, 212, 191), font=font_small)
    draw.text((1215, py + 12), "🔊 100%", fill=(226, 232, 240), font=font_small)
    draw.text((1260, py + 12), "", fill=(226, 232, 240), font=font_small)

    bg.save(ASSETS_DIR / "katoyos-desktop-preview.png", "PNG")
    print("Generated katoyos-desktop-preview.png")

def create_welcome_preview():
    # Base background (Dark canvas)
    bg = Image.new("RGBA", (1000, 650), (10, 12, 26, 255))
    draw = ImageDraw.Draw(bg)

    font_title = get_font(16, bold=True)
    font_main = get_font(13)
    font_bold = get_font(13, bold=True)
    font_small = get_font(11)

    # Main Wizard Dialog Window
    wx, wy, ww, wh = 100, 50, 800, 550
    draw.rectangle([wx, wy, wx+ww, wy+wh], fill=(22, 26, 42, 255), outline=(45, 212, 191), width=1)
    draw_window_header(draw, wx, wy, ww, 36, "Welcome to KatoyOS Setup Wizard", active=True)

    # Left Sidebar
    sb_w = 210
    draw.rectangle([wx, wy+36, wx+sb_w, wy+wh-50], fill=(16, 19, 32))
    draw.line([wx+sb_w, wy+36, wx+sb_w, wy+wh-50], fill=(40, 45, 65))

    steps = [
        ("1. Welcome", False),
        ("2. Network", False),
        ("3. Region & Keyboard", True),  # Active
        ("4. Password", False),
        ("5. Finish", False)
    ]

    sy = wy + 60
    for step_text, is_active in steps:
        if is_active:
            draw.rounded_rectangle([wx + 10, sy - 4, wx + sb_w - 10, sy + 24], fill=(124, 58, 237), radius=4)
            draw.text((wx + 25, sy + 2), step_text, fill=(255, 255, 255), font=font_bold)
        else:
            draw.text((wx + 25, sy + 2), step_text, fill=(148, 163, 184), font=font_main)
        sy += 45

    # Content Area
    cx = wx + sb_w + 30
    cy = wy + 60

    draw.text((cx, cy), "Region & Keyboard Settings", fill=(45, 212, 191), font=font_title)
    draw.text((cx, cy + 28), "Configure your time zone, Wi-Fi country code, and keyboard layout.", fill=(148, 163, 184), font=font_main)

    # Form Fields
    fy = cy + 70

    # Timezone
    draw.text((cx, fy), "Time Zone:", fill=(226, 232, 240), font=font_bold)
    draw.rounded_rectangle([cx, fy + 22, cx + 480, fy + 58], fill=(14, 17, 26), outline=(60, 66, 90), radius=4)
    draw.text((cx + 15, fy + 31), "UTC (Coordinated Universal Time)", fill=(226, 232, 240), font=font_main)
    draw.polygon([(cx + 460, fy + 36), (cx + 470, fy + 36), (cx + 465, fy + 44)], fill=(148, 163, 184))

    # Wi-Fi Country
    fy += 80
    draw.text((cx, fy), "Wi-Fi Country Code (Regulatory):", fill=(226, 232, 240), font=font_bold)
    draw.rounded_rectangle([cx, fy + 22, cx + 480, fy + 58], fill=(14, 17, 26), outline=(60, 66, 90), radius=4)
    draw.text((cx + 15, fy + 31), "US - United States", fill=(226, 232, 240), font=font_main)
    draw.polygon([(cx + 460, fy + 36), (cx + 470, fy + 36), (cx + 465, fy + 44)], fill=(148, 163, 184))

    # Keyboard Layout
    fy += 80
    draw.text((cx, fy), "Keyboard Layout:", fill=(226, 232, 240), font=font_bold)
    draw.rounded_rectangle([cx, fy + 22, cx + 480, fy + 58], fill=(14, 17, 26), outline=(60, 66, 90), radius=4)
    draw.text((cx + 15, fy + 31), "English (US)", fill=(226, 232, 240), font=font_main)
    draw.polygon([(cx + 460, fy + 36), (cx + 470, fy + 36), (cx + 465, fy + 44)], fill=(148, 163, 184))

    # Bottom Button Bar
    by = wy + wh - 50
    draw.line([wx, by, wx + ww, by], fill=(40, 45, 65))

    # Buttons
    draw.rounded_rectangle([wx + 20, by + 10, wx + 180, by + 40], fill=(22, 26, 42), outline=(60, 66, 90), radius=4)
    draw.text((wx + 35, by + 18), "☐ Don't show again", fill=(148, 163, 184), font=font_small)

    draw.rounded_rectangle([wx + ww - 220, by + 10, wx + ww - 120, by + 40], fill=(30, 35, 55), outline=(60, 66, 90), radius=4)
    draw.text((wx + ww - 192, by + 18), "< Back", fill=(226, 232, 240), font=font_main)

    draw.rounded_rectangle([wx + ww - 110, by + 10, wx + ww - 20, by + 40], fill=(45, 212, 191), radius=4)
    draw.text((wx + ww - 80, by + 18), "Next >", fill=(10, 12, 26), font=font_bold)

    bg.save(ASSETS_DIR / "katoyos-welcome-preview.png", "PNG")
    print("Generated katoyos-welcome-preview.png")

def create_karaoke_preview():
    # Base canvas (1000x650)
    wp_path = BRANDING_DIR / "wallpaper.png"
    if wp_path.exists():
        bg = Image.open(wp_path).convert("RGBA").resize((1000, 650), Image.Resampling.LANCZOS)
    else:
        bg = Image.new("RGBA", (1000, 650), (18, 22, 32, 255))

    # Dark overlay to simulate player background
    overlay = Image.new("RGBA", (1000, 650), (10, 14, 24, 180))
    bg = Image.alpha_composite(bg, overlay)

    draw = ImageDraw.Draw(bg)

    font_title = get_font(22, bold=True)
    font_sub = get_font(16)
    font_lyric_cur = get_font(28, bold=True)
    font_lyric_other = get_font(18)
    font_small = get_font(12)

    # Top Header Bar
    # Song Code badge
    draw.rounded_rectangle([30, 20, 120, 58], fill=(0, 210, 255, 220), radius=6)
    draw.text((45, 27), "00042", fill=(10, 14, 24), font=get_font(18, bold=True))

    # Song Title & Artist
    draw.text((140, 25), "Anak", fill=(255, 255, 255), font=font_title)
    draw.text((220, 29), "- Freddie Aguilar", fill=(208, 213, 224), font=font_sub)

    # Key / Pitch badge
    draw.rounded_rectangle([440, 20, 530, 58], fill=(245, 158, 11, 220), radius=6)
    draw.text((450, 28), "KEY: +2", fill=(10, 14, 24), font=get_font(15, bold=True))

    # Return button (right)
    draw.rounded_rectangle([840, 20, 970, 58], fill=(43, 50, 69, 200), radius=6)
    draw.text((855, 30), "🔙 Song List", fill=(255, 255, 255), font=font_small)

    # NEXT UP Ticker Banner
    draw.rounded_rectangle([30, 68, 970, 102], fill=(16, 185, 129, 60), outline=(16, 185, 129), width=1, radius=6)
    draw.text((45, 76), "NEXT UP: [00108] Push - Eraserheads  |  [00215] Harana - Parokya Ni Edgar", fill=(167, 243, 208), font=get_font(13, bold=True))

    # Lyrics Container (Center)
    cy = 220
    # Previous line
    draw.rounded_rectangle([150, cy - 60, 850, cy - 10], fill=(0, 0, 0, 100), radius=8)
    draw.text((500, cy - 43), "Welcome to the Hotel California", fill=(255, 255, 255, 120), font=font_lyric_other, anchor="mm")

    # Current line (highlighted)
    draw.rounded_rectangle([100, cy + 10, 900, cy + 90], fill=(0, 0, 0, 160), outline=(0, 210, 255), width=2, radius=12)
    # Highlighted word "lovely" and normal text
    draw.text((500, cy + 50), "Such a lovely place, such a lovely face", fill=(0, 240, 255), font=font_lyric_cur, anchor="mm")

    # Next line
    draw.rounded_rectangle([150, cy + 110, 850, cy + 160], fill=(0, 0, 0, 100), radius=8)
    draw.text((500, cy + 127), "Plenty of room at the Hotel California", fill=(255, 255, 255, 180), font=font_lyric_other, anchor="mm")

    # Bottom Progress & Controls Bar
    by = 560
    # Time
    draw.text((900, by), "01:45 / 06:30", fill=(255, 255, 255), font=font_small)

    # Progress bar
    draw.rounded_rectangle([30, by + 20, 970, by + 28], fill=(255, 255, 255, 50), radius=4)
    draw.rounded_rectangle([30, by + 20, 290, by + 28], fill=(0, 210, 255), radius=4)

    # Controls button
    draw.rounded_rectangle([440, by + 38, 560, by + 72], fill=(0, 122, 204, 200), radius=6)
    draw.text((500, by + 47), "⏸ Pause", fill=(255, 255, 255), font=font_small, anchor="mm")

    bg.save(ASSETS_DIR / "katoyos-karaoke-preview.png", "PNG")
    print("Generated katoyos-karaoke-preview.png")

def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    create_desktop_preview()
    create_welcome_preview()
    create_karaoke_preview()

if __name__ == "__main__":
    main()
