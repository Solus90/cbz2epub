# cbz2epub

Convert CBZ comic archives to fixed-layout EPUB3. Works as a CLI tool or a local web app.

No external dependencies for the core converter — stdlib only.

## Web UI

```bash
pip install flask
python server.py
```

Open **http://localhost:5757** — drag and drop CBZ files, click **Convert All**, download EPUBs.

## CLI

```bash
# Single file
python cbz2epub.py mycomic.cbz

# Custom output path
python cbz2epub.py mycomic.cbz -o ~/Books/mycomic.epub

# Batch convert
python cbz2epub.py *.cbz
```

## Details

- Produces **fixed-layout EPUB3** — pages don't reflow, correct for comics and manga
- Reads actual image dimensions from PNG and JPEG headers for accurate viewports
- Natural sort order (`page10` comes after `page9`)
- Supports JPG, PNG, GIF, WebP images inside the archive
- No dependencies beyond Python stdlib (Flask only needed for the web UI)

## License

MIT
