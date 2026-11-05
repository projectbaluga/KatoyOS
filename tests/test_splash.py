"""
tests/test_splash.py

Unit tests for tools/make-splash.py.
"""
import subprocess
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools/make-splash.py"


def test_make_splash_defaults(tmp_path):
    out_png = tmp_path / "default-splash.png"
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out_png)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"make-splash failed: {res.stderr}"
    assert out_png.exists()

    img = Image.open(out_png)
    assert img.size == (1024, 1024)
    assert img.mode == "RGBA"
    # Verify navy background at corner
    assert img.getpixel((0, 0)) == (3, 6, 22, 255)


def test_make_splash_custom_name_and_tagline(tmp_path):
    out_png = tmp_path / "custom-splash.png"
    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--name",
            "SuperKaraoke",
            "--tagline",
            "Sing Your Heart Out",
            "--out",
            str(out_png),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"make-splash failed: {res.stderr}"
    assert out_png.exists()

    img = Image.open(out_png)
    assert img.size == (1024, 1024)
    assert img.mode == "RGBA"


def test_make_splash_transparent_png_logo(tmp_path):
    # Create a small custom transparent PNG logo
    custom_logo = tmp_path / "custom-logo.png"
    logo_img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    for x in range(50, 150):
        for y in range(50, 150):
            logo_img.putpixel((x, y), (255, 255, 255, 255))
    logo_img.save(custom_logo, "PNG")

    out_png = tmp_path / "custom-logo-splash.png"
    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--logo",
            str(custom_logo),
            "--name",
            "LogoTestOS",
            "--out",
            str(out_png),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"make-splash failed: {res.stderr}"
    assert out_png.exists()

    img = Image.open(out_png)
    assert img.size == (1024, 1024)
    assert img.mode == "RGBA"


def test_make_splash_opaque_line_art(tmp_path):
    # Create a black line-art logo on solid white background
    custom_logo = tmp_path / "line-art.png"
    logo_img = Image.new("RGB", (200, 200), (255, 255, 255))
    for x in range(60, 140):
        for y in range(60, 140):
            logo_img.putpixel((x, y), (0, 0, 0))
    logo_img.save(custom_logo, "PNG")

    out_png = tmp_path / "line-art-splash.png"
    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--logo",
            str(custom_logo),
            "--name",
            "LineArtOS",
            "--out",
            str(out_png),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"make-splash failed: {res.stderr}"
    assert out_png.exists()

    img = Image.open(out_png)
    assert img.size == (1024, 1024)
    colors = img.getcolors(maxcolors=100000)
    has_white = any(c[1][:3] == (255, 255, 255) for c in colors)
    assert has_white


def test_make_splash_missing_logo_exits_with_error(tmp_path):
    out_png = tmp_path / "err-splash.png"
    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--logo",
            "/path/to/nonexistent/logo.png",
            "--out",
            str(out_png),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
