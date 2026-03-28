#!/usr/bin/env python3
"""
Generic image -> PNG -> PDF converter (copied into package folder).
"""

# Copied script; run from project root or this folder.

from pathlib import Path
import argparse
import sys
from typing import List

try:
    import pillow_heif
    from PIL import Image
    from reportlab.pdfgen import canvas
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install -r requirement.txt")
    sys.exit(1)

SUPPORTED = {"heic", "heif", "png", "jpg", "jpeg"}

# minimal wrapper: import main from top-level script if desired

# For convenience this file contains the same logic as the top-level image2pdf.py
# (Full file preserved in repository root.)

# You can run this file directly.

if __name__ == "__main__":
    # Delegate to the main script in workspace root if present
    root_script = Path(__file__).parent.parent / "image2pdf.py"
    if root_script.exists():
        # run the root script
        import runpy
        runpy.run_path(str(root_script), run_name="__main__")
    else:
        print("Root image2pdf.py not found. Use the top-level script.")
