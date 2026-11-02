#!/usr/bin/env python3
"""
Generates visual UI previews for KatoyOS documentation:
  - assets/katoyos-desktop-preview.png (1280x720 Windows 11 style LXQt Desktop Preview)
  - assets/katoyos-welcome-preview.png (1000x650 KatoyOS Welcome Wizard Preview)
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
BRANDING_DIR = ROOT / "stage-katoy/01-branding/files"

def get_font(size=14, bold=False):
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

def draw_win11_window_header(draw, x, y, width, height, title, active=True):
    # Katoy-Win11 Openbox flat titlebar: window #202020, border #3a3a3a, text #ffffff
    header_color = (32, 32, 32) if active else (43, 43, 43)
    border_color = (58, 58, 58) if active else (43, 43, 43)

    draw.rectangle([x, y, x + width, y + height], fill=header_color)
    draw.line([x, y, x + width, y], fill=border_color, width=1)

    # Windows 11 caption buttons (minimize, maximize, close)
    btn_w = 46
    bx = x + width - btn_w
    # Close button (hover red style preview or flat active)
    draw.rectangle([bx, y, bx + btn_w, y + height], fill=header_color)
    # Draw 'X' glyph
    cx, cy = bx + btn_w // 2, y + height // 2
    d = 4
    draw.line([cx - d, cy - d, cx + d, cy + d], fill=(255, 255, 255), width=1)
    draw.line([cx + d, cy - d, cx - d, cy + d], fill=(255, 255, 255), width=1)

    # Maximize button
    bx -= btn_w
    draw.rectangle([bx, y, bx + btn_w, y + height], fill=header_color)
    mx, my = bx + btn_w // 2, y + height // 2
    draw.rectangle([mx - 5, my - 5, mx + 5, my + 5], outline=(255, 255, 255), width=1)

    # Minimize button
    bx -= btn_w
    draw.rectangle([bx, y, bx + btn_w, y + height], fill=header_color)
    ix, iy = bx + btn_w // 2, y + height // 2
    draw.line([ix - 5, iy + 4, ix + 5, iy + 4], fill=(255, 255, 255), width=1)

    # Title label
    font_title = get_font(12)
    draw.text((x + 16, y + (height - 14) // 2), title, fill=(255, 255, 255), font=font_title)

def create_desktop_preview():
    # Base wallpaper
    wp_path = BRANDING_DIR / "wallpaper.png"
    if wp_path.exists():
        bg = Image.open(wp_path).convert("RGBA").resize((1280, 720), Image.Resampling.LANCZOS)
    else:
        bg = Image.new("RGBA", (1280, 720), (10, 12, 26, 255))

    draw = ImageDraw.Draw(bg)
    font_bold = get_font(12, bold=True)
    font_small = get_font(11)

    # 1. QTerminal Window (Center-left)
    tx, ty, tw, th = 60, 50, 700, 460
    # Shadow
    draw.rectangle([tx+3, ty+3, tx+tw+3, ty+th+3], fill=(0, 0, 0, 140))
    # Window background & border
    draw.rectangle([tx, ty, tx+tw, ty+th], fill=(32, 32, 32), outline=(58, 58, 58), width=1)
    draw_win11_window_header(draw, tx, ty, tw, 32, "qterminal - katoy@katoyos: ~", active=True)

    # Terminal interior (dark background #1a1a1a)
    draw.rectangle([tx + 1, ty + 33, tx + tw - 1, ty + th - 1], fill=(26, 26, 26))

    term_y = ty + 44
    term_x = tx + 18
    term_font = get_font(12)

    lines = [
        ("katoy@katoyos", (96, 205, 255), ":", (255, 255, 255), "~$", (180, 160, 255), " neofetch", (255, 255, 255)),
        ("       .---.         ", (96, 205, 255), "OS: ", (180, 160, 255), "KatoyOS 1.0 (Debian 13 trixie armhf)", (255, 255, 255)),
        ("      /  .  \\        ", (96, 205, 255), "Host: ", (180, 160, 255), "Raspberry Pi 3 Model B Rev 1.2", (255, 255, 255)),
        ("     |  (o)  |       ", (96, 205, 255), "Kernel: ", (180, 160, 255), "linux-image-6.18.50+rpt-rpi-v7", (255, 255, 255)),
        ("      \\  '  /        ", (96, 205, 255), "Uptime: ", (180, 160, 255), "18 mins", (255, 255, 255)),
        ("       '---'         ", (96, 205, 255), "Packages: ", (180, 160, 255), "1142 (dpkg)", (255, 255, 255)),
        ("                     ", (96, 205, 255), "Shell: ", (180, 160, 255), "bash 5.2.37", (255, 255, 255)),
        ("                     ", (96, 205, 255), "Desktop: ", (180, 160, 255), "LXQt on Openbox (Katoy-Win11 Dark)", (255, 255, 255)),
        ("                     ", (96, 205, 255), "Terminal: ", (180, 160, 255), "qterminal", (255, 255, 255)),
        ("                     ", (96, 205, 255), "CPU: ", (180, 160, 255), "ARMv7 Processor rev 4 (v7l) x 4", (255, 255, 255)),
        ("                     ", (96, 205, 255), "Memory: ", (180, 160, 255), "312 MB / 920 MB (Idle RAM)", (96, 205, 255)),
        ("", (0,0,0)),
        ("katoy@katoyos", (96, 205, 255), ":", (255, 255, 255), "~$", (180, 160, 255), " free -h", (255, 255, 255)),
        ("               total        used        free      shared  buff/cache   available", (160, 160, 160)),
        ("Mem:           920Mi       312Mi       410Mi        12Mi       198Mi       580Mi", (255, 255, 255)),
        ("Swap (zram):   512Mi          0B       512Mi", (96, 205, 255)),
        ("katoy@katoyos", (96, 205, 255), ":", (255, 255, 255), "~$", (180, 160, 255), " █", (96, 205, 255)),
    ]

    for row in lines:
        curr_x = term_x
        for i in range(0, len(row), 2):
            text, color = row[i], row[i+1]
            draw.text((curr_x, term_y), text, fill=color, font=term_font)
            bbox = draw.textbbox((curr_x, term_y), text, font=term_font)
            curr_x += (bbox[2] - bbox[0])
        term_y += 20

    # 2. Desktop Notification (Top Right toast matching lxqt-notificationd.qss: #2c2c2c, border 1px #3a3a3a, radius 8px)
    nx, ny, nw, nh = 890, 50, 360, 92
    draw.rounded_rectangle([nx, ny, nx+nw, ny+nh], fill=(44, 44, 44, 250), outline=(58, 58, 58), width=1, radius=8)
    draw.text((nx + 18, ny + 14), "⚡ KatoyOS PowerWatch", fill=(96, 205, 255), font=font_bold)
    draw.text((nx + 18, ny + 36), "Under-voltage detected (bit 0x1)", fill=(255, 255, 255), font=font_bold)
    draw.text((nx + 18, ny + 58), "Use a quality 5V 2.5A power supply & short cable.", fill=(157, 157, 157), font=font_small)

    # 3. Windows 11 Taskbar (48px high, #202020, border-top 1px #2f2f2f)
    py = 720 - 48
    draw.rectangle([0, py, 1280, 720], fill=(32, 32, 32))
    draw.line([0, py, 1280, py], fill=(47, 47, 47), width=1)

    # Start button (KatoyOS logo icon)
    icon_64_path = BRANDING_DIR / "katoyos-64.png"
    if icon_64_path.exists():
        menu_icon = Image.open(icon_64_path).convert("RGBA").resize((28, 28), Image.Resampling.LANCZOS)
        bg.paste(menu_icon, (10, py + 10), menu_icon)
    else:
        draw.rounded_rectangle([10, py+8, 44, py+40], fill=(46, 46, 46), radius=4)

    # Pinned apps (quicklaunch: pcmanfm-qt, katoy-browser, qterminal)
    draw.rounded_rectangle([52, py + 6, 88, py + 42], fill=(32, 32, 32), radius=4)
    draw.text((64, py + 14), "📁", font=font_small)

    draw.rounded_rectangle([92, py + 6, 128, py + 42], fill=(32, 32, 32), radius=4)
    draw.text((104, py + 14), "🌐", font=font_small)

    # Running app on taskbar with accent underline (#60cdff, 3px solid)
    draw.rounded_rectangle([134, py + 6, 178, py + 42], fill=(48, 48, 48), radius=4)
    draw.line([140, py + 41, 172, py + 41], fill=(96, 205, 255), width=3)
    draw.text((149, py + 14), "💻", font=font_small)

    # Status Notifier & Tray (Right aligned)
    # Clock format: custom "h:mm AP<br/>dd/MM/yyyy"
    clock_x = 1180
    draw.rounded_rectangle([clock_x - 6, py + 4, 1264, py + 44], fill=(32, 32, 32), radius=4)
    draw.text((clock_x, py + 8), "10:24 AM", fill=(255, 255, 255), font=font_small)
    draw.text((clock_x, py + 24), "01/11/2026", fill=(200, 200, 200), font=get_font(10))

    # Tray icons (volume, network)
    draw.text((1115, py + 16), "📶", font=font_small)
    draw.text((1145, py + 16), "🔊", font=font_small)

    # Show desktop thin slice at the right end
    draw.line([1272, py + 6, 1272, py + 42], fill=(47, 47, 47), width=1)

    bg.save(ASSETS_DIR / "katoyos-desktop-preview.png", "PNG")
    print("Generated katoyos-desktop-preview.png")

def create_welcome_preview():
    # Base background (Dark canvas)
    bg = Image.new("RGBA", (1000, 650), (16, 19, 32, 255))
    draw = ImageDraw.Draw(bg)

    font_title = get_font(22, bold=True)
    font_body = get_font(13)
    font_bold = get_font(13, bold=True)
    font_small = get_font(11)

    # Wizard window: 660x480, #202020 background, flat Openbox header
    wx, wy, ww, wh = 170, 85, 660, 480
    # Shadow
    draw.rectangle([wx+4, wy+4, wx+ww+4, wy+wh+4], fill=(0, 0, 0, 160))
    # Dialog frame
    draw.rectangle([wx, wy, wx+ww, wy+wh], fill=(32, 32, 32), outline=(58, 58, 58), width=1)
    draw_win11_window_header(draw, wx, wy, ww, 32, "Welcome to KatoyOS", active=True)

    # Top thin progress bar: QProgressBar 4px height, chunk #60cdff
    p_val = 2  # Step 3 of 5 (Region & Keyboard)
    p_max = 4
    p_w = int(ww * (p_val / p_max))
    draw.rectangle([wx, wy + 32, wx + ww, wy + 36], fill=(58, 58, 58))
    draw.rectangle([wx, wy + 32, wx + p_w, wy + 36], fill=(96, 205, 255))

    # Content Area
    cx = wx + 40
    cy = wy + 60

    draw.text((cx, cy), "Region & Keyboard", fill=(255, 255, 255), font=font_title)
    draw.text((cx, cy + 38), "Configure your timezone, Wi-Fi regulatory country, and keyboard layout.", fill=(197, 197, 197), font=font_body)

    # Form Fields
    fy = cy + 80
    field_w = 420

    # Timezone
    draw.text((cx, fy), "Timezone", fill=(255, 255, 255), font=font_bold)
    draw.rounded_rectangle([cx, fy + 22, cx + field_w, fy + 56], fill=(45, 45, 45), outline=(58, 58, 58), radius=4)
    draw.line([cx, fy + 56, cx + field_w, fy + 56], fill=(154, 154, 154), width=1)
    draw.text((cx + 12, fy + 30), "Asia/Manila (PHT, +0800)", fill=(255, 255, 255), font=font_body)
    draw.polygon([(cx + field_w - 20, fy + 36), (cx + field_w - 10, fy + 36), (cx + field_w - 15, fy + 44)], fill=(255, 255, 255))

    # Wi-Fi Country
    fy += 72
    draw.text((cx, fy), "Wi-Fi Country (Regulatory)", fill=(255, 255, 255), font=font_bold)
    draw.rounded_rectangle([cx, fy + 22, cx + field_w, fy + 56], fill=(45, 45, 45), outline=(58, 58, 58), radius=4)
    draw.line([cx, fy + 56, cx + field_w, fy + 56], fill=(154, 154, 154), width=1)
    draw.text((cx + 12, fy + 30), "Philippines (PH)", fill=(255, 255, 255), font=font_body)
    draw.polygon([(cx + field_w - 20, fy + 36), (cx + field_w - 10, fy + 36), (cx + field_w - 15, fy + 44)], fill=(255, 255, 255))

    # Keyboard Layout
    fy += 72
    draw.text((cx, fy), "Keyboard Layout", fill=(255, 255, 255), font=font_bold)
    draw.rounded_rectangle([cx, fy + 22, cx + field_w, fy + 56], fill=(45, 45, 45), outline=(58, 58, 58), radius=4)
    draw.line([cx, fy + 56, cx + field_w, fy + 56], fill=(154, 154, 154), width=1)
    draw.text((cx + 12, fy + 30), "English (US)", fill=(255, 255, 255), font=font_body)
    draw.polygon([(cx + field_w - 20, fy + 36), (cx + field_w - 10, fy + 36), (cx + field_w - 15, fy + 44)], fill=(255, 255, 255))

    # Navigation buttons: Back, Next (#accent: background #60cdff, text #000000)
    by = wy + wh - 58
    draw.rounded_rectangle([cx, by, cx + 90, by + 34], fill=(45, 45, 45), outline=(58, 58, 58), radius=4)
    draw.text((cx + 26, by + 8), "Back", fill=(255, 255, 255), font=font_bold)

    next_x = wx + ww - 40 - 90
    draw.rounded_rectangle([next_x, by, next_x + 90, by + 34], fill=(96, 205, 255), radius=4)
    draw.text((next_x + 28, by + 8), "Next", fill=(0, 0, 0), font=font_bold)

    bg.save(ASSETS_DIR / "katoyos-welcome-preview.png", "PNG")
    print("Generated katoyos-welcome-preview.png")

def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    create_desktop_preview()
    create_welcome_preview()

if __name__ == "__main__":
    main()
