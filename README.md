# Batch Image Converter — GUI Edition

> A standalone desktop application for batch converting images with a graphical interface.  
> Based on [Batch Image Converter](https://github.com/EdoardoTosin/Batch-Image-Converter) by Edoardo Tosin.


---

## ⬇️ Download

Go to the [Releases](../../releases/latest) page and download the latest `.exe` for Windows.  
**No installation required** — just double-click and run.

---

## ✨ What's new in this fork

The original project is a command-line tool. This fork turns it into a fully graphical desktop app with additional features:

- 🖥️ Graphical interface — no terminal needed
- 📷 Native RAW support (NEF, CR2, ARW, DNG and more)
- 🔄 Choose output format: **PNG** or **JPG**
- 📂 Optional recursive subfolder processing
- 📋 Real-time conversion log

---

## 🖼️ Supported formats

| Type | Extensions |
|------|-----------|
| Standard | JPG, JPEG, PNG, TIF, TIFF, BMP, WebP |
| Nikon RAW | NEF, NRW |
| Canon RAW | CR2, CR3 |
| Sony RAW | ARW |
| Olympus RAW | ORF |
| Panasonic RAW | RW2 |
| Adobe DNG | DNG |
| Fujifilm RAW | RAF |
| Pentax RAW | PEF |
| Samsung RAW | SRW |

---

## ⚙️ Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Folder | Source folder for images | — |
| DPI | Output pixel density | 72 |
| Max size (px) | Max long side in pixels | 1000 |
| Quality | JPEG output quality (1–100) | 80 |
| Filter | Resampling filter | Lanczos |
| Max Megapixels | Limit input resolution (0 = unlimited) | 0 |
| Color space | Convert to RGB | Off |
| Optimize | Compress palette | On |
| Output format | PNG or JPG | PNG |
| Subfolders | Process subfolders recursively | On |

---

## ⚠️ Important

> **Files are overwritten in place.** The original file is replaced by the converted version.  
> Make a backup before converting if you need to keep the originals.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0**.  
See the [LICENSE](LICENSE) file for details.

Based on original work by [Edoardo Tosin](https://github.com/EdoardoTosin/Batch-Image-Converter), © 2022–2025.
