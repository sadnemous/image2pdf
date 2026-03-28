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

Typical workflow

- Use your iPhone or Android phone to take pictures of your notes.
- Transfer the images to your PC or laptop (USB, AirDrop, cloud, etc.).
- Clone this repository:

```bash
git clone https://github.com/sadnemous/image2pdf.git
cd image2pdf
```

- Install and activate the virtual environment:

```bash
./setup.sh
. venv/bin/activate
```

- Convert your images (example for JPG/PNG):

```bash
python image2pdf.py /path/to/your/photos --ext jpg,png --resize 100 -o notes.pdf
```

The script will write intermediate PNGs into `./png` and ask whether to delete them after creating the PDF.
