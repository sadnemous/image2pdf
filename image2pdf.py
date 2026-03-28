#!/usr/bin/env python3
"""
Generic image -> PNG -> PDF converter.

Features:
- Accept directory or single file input
- Filter by extension(s) (interactive prompt if not provided)
- Supports HEIC/HEIF, PNG, JPG/JPEG
- Converts all images to PNG in ./png (or --png-dir)
- Optional resize percentage (1-100, default 100 = no change)
- Optional auto-rotate / deskew (requires opencv-python and pytesseract)
- Combines PNGs into a single PDF (one image per page) unless --no-pdf
- Prompts to delete intermediate PNGs after PDF creation

Requirements:
    pip install -r requirements.txt

Usage examples:
    python image2pdf.py /path/to/dir --ext heic,png,jpg --resize 80 -o out.pdf
    python image2pdf.py /path/to/dir --ext heic,jpg,png --deskew -o combined.pdf
    python image2pdf.py image.heic
    python image2pdf.py --ext png
"""

from pathlib import Path
import argparse
import sys
from typing import List

try:
    import pillow_heif
    from PIL import Image, ImageOps
    from reportlab.pdfgen import canvas
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install -r requirements.txt")
    sys.exit(1)

# optional dependencies for deskew/rotation
HAS_OPENCV = True
HAS_TESSERACT = True
try:
    import cv2
    import numpy as np
except Exception:
    HAS_OPENCV = False

try:
    import pytesseract
except Exception:
    HAS_TESSERACT = False

SUPPORTED = {"heic", "heif", "png", "jpg", "jpeg"}


def normalize_ext_list(ext_arg: str) -> List[str]:
    if not ext_arg:
        return []
    parts = [p.strip().lower() for p in ext_arg.split(",") if p.strip()]
    expanded = []
    for p in parts:
        if p == "all":
            expanded.extend(sorted(SUPPORTED))
        elif p in SUPPORTED:
            expanded.append(p)
        elif p.startswith(".") and p[1:] in SUPPORTED:
            expanded.append(p[1:])
    seen = set()
    out = []
    for e in expanded:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def gather_files(input_path: Path, exts: List[str]) -> List[Path]:
    if input_path.is_file():
        if input_path.suffix.lower().lstrip(".") in exts:
            return [input_path]
        return []
    elif input_path.is_dir():
        return [
            p for p in input_path.iterdir()
            if p.is_file() and p.suffix.lower().lstrip(".") in exts
        ]
    return []


# ── deskew helpers ────────────────────────────────────────────────────────────

def _pil_to_cv(img: "Image.Image"):
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _cv_to_pil(cv_img) -> "Image.Image":
    rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def _detect_skew_angle(cv_img) -> float:
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if coords.shape[0] == 0:
        return 0.0
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    return float(angle)


def _get_tesseract_rotation(img: "Image.Image") -> float:
    if not HAS_TESSERACT:
        return 0.0
    try:
        import re
        osd = pytesseract.image_to_osd(img)
        m = re.search(r"Rotate: (\d+)", osd)
        if m:
            return -float(m.group(1))
    except Exception:
        pass
    return 0.0


def _auto_rotate_and_deskew(pil_img: "Image.Image") -> "Image.Image":
    if not HAS_OPENCV:
        print("  [deskew] OpenCV not available; skipping.")
        return pil_img

    angle_tess = _get_tesseract_rotation(pil_img)
    if abs(angle_tess) > 0.1:
        pil_img = pil_img.rotate(angle_tess, expand=True, resample=Image.BICUBIC)

    cv_img = _pil_to_cv(pil_img)
    angle = _detect_skew_angle(cv_img)
    if abs(angle) > 0.3:
        h, w = cv_img.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        rotated = cv2.warpAffine(
            cv_img, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        pil_img = _cv_to_pil(rotated)

    return pil_img


# ── core conversion ───────────────────────────────────────────────────────────

def convert_to_png(
    img_path: Path,
    out_dir: Path,
    resize_percent: int = 100,
    deskew: bool = False,
) -> Path:
    out_path = out_dir / (img_path.stem + ".png")
    with Image.open(img_path) as img:
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if deskew:
            img = _auto_rotate_and_deskew(img)

        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        orig_size = img.size
        if resize_percent != 100:
            new_w = max(1, int(orig_size[0] * resize_percent / 100))
            new_h = max(1, int(orig_size[1] * resize_percent / 100))
            img = img.resize((new_w, new_h), resample=Image.LANCZOS)

        img.save(out_path, format="PNG")
        final_size = img.size

    print(f"  Converted: {img_path.name} -> {out_path.name}  {orig_size} -> {final_size}")
    return out_path


def build_pdf(png_paths: List[Path], output_pdf: Path) -> None:
    if not png_paths:
        print("No PNGs to build into PDF.")
        return
    c = canvas.Canvas(str(output_pdf))
    for p in png_paths:
        with Image.open(p) as img:
            w, h = img.size
        c.setPageSize((float(w), float(h)))
        c.drawImage(str(p), 0, 0, width=w, height=h)
        c.showPage()
        print(f"  Added {p.name} ({w}x{h})")
    c.save()
    print(f"\nPDF saved: {output_pdf}")


def prompt_and_delete_pngs(png_files: List[Path], png_dir: Path) -> None:
    if not png_files:
        return
    try:
        ans = input(f"\nDelete intermediate PNGs in {png_dir}? [y/N]: ").strip().lower()
    except KeyboardInterrupt:
        print("\nSkipping deletion.")
        return
    if not ans.startswith("y"):
        print("Keeping PNG files.")
        return
    removed = 0
    for p in png_files:
        try:
            p.resolve().relative_to(png_dir.resolve())
        except Exception:
            continue
        if p.exists():
            p.unlink()
            removed += 1
    print(f"Deleted {removed} file(s) from {png_dir}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert images to PNG and combine into PDF"
    )
    parser.add_argument(
        "input", nargs="?", default=".",
        help="Directory or single file (default: current dir)"
    )
    parser.add_argument(
        "--ext",
        help="Comma-separated extensions (e.g. heic,png,jpg) or 'all'. Prompted if omitted."
    )
    parser.add_argument("--png-dir", default=None, help="Directory for PNGs (default: ./png)")
    parser.add_argument("--output", "-o", default="output.pdf", help="Output PDF path")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF creation")
    parser.add_argument(
        "--resize", "-r", type=int, default=100,
        help="Resize percent 1-100 (default: 100 = original size)"
    )
    parser.add_argument(
        "--deskew", action="store_true",
        help="Auto-rotate and deskew images (requires opencv-python; pytesseract optional)"
    )
    parser.add_argument(
        "--sort", choices=["name", "date", "none"], default="name",
        help="Sort order for images in PDF (default: name)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)

    ext_list = normalize_ext_list(args.ext) if args.ext else []
    if not ext_list:
        try:
            user_in = input("Enter extension(s) to process (e.g. heic,png,jpg) or 'all': ")
        except KeyboardInterrupt:
            print("\nAborted")
            sys.exit(1)
        ext_list = normalize_ext_list(user_in)

    if not ext_list:
        print("No valid extensions provided. Supported:", ", ".join(sorted(SUPPORTED)))
        sys.exit(1)

    if any(e in ("heic", "heif") for e in ext_list):
        try:
            pillow_heif.register_heif_opener()
        except Exception as e:
            print(f"Warning: could not register HEIF opener: {e}")

    files = gather_files(input_path, ext_list)
    if not files:
        print("No matching files found.")
        sys.exit(0)

    if args.sort == "name":
        files.sort(key=lambda p: p.name.lower())
    elif args.sort == "date":
        files.sort(key=lambda p: p.stat().st_mtime)

    png_dir = Path(args.png_dir) if args.png_dir else Path.cwd() / "png"
    png_dir.mkdir(parents=True, exist_ok=True)

    if not (1 <= args.resize <= 100):
        print("Error: --resize must be between 1 and 100")
        sys.exit(1)

    if args.deskew and not HAS_OPENCV:
        print("Warning: --deskew requested but opencv-python is not installed. Install with: pip install opencv-python")

    print(f"Found {len(files)} file(s). Converting to PNG in {png_dir}...\n")
    png_files = []
    for f in files:
        try:
            png = convert_to_png(f, png_dir, resize_percent=args.resize, deskew=args.deskew)
            png_files.append(png)
        except Exception as e:
            print(f"  Failed: {f.name}: {e}")

    if args.no_pdf:
        print(f"\nDone. {len(png_files)} PNG(s) written to {png_dir}")
        prompt_and_delete_pngs(png_files, png_dir)
        return

    print(f"\nBuilding PDF from {len(png_files)} PNG(s)...\n")
    build_pdf(png_files, Path(args.output))
    prompt_and_delete_pngs(png_files, png_dir)


if __name__ == "__main__":
    main()
