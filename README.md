# image2pdf

Small utility to convert HEIC/PNG/JPEG images to PNG and combine them into a single PDF.

Setup
```
cd image2pdf
./setup.sh
. venv/bin/activate
```

Quick run
```
python image2pdf.py /path/to/images --ext heic,jpg,png --resize 80 -o combined.pdf
```

Notes
- HEIC support requires system `libheif` and a decoder (e.g. `libde265`) on Linux/macOS.
- The script writes intermediate PNGs into `./png` by default and will ask to delete them when finished.
- The `setup.sh` installs dependencies from `requirement.txt` (note filename).
