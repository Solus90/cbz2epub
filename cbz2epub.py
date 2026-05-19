#!/usr/bin/env python3
"""Convert CBZ comic archives to fixed-layout EPUB3."""

import argparse
import re
import struct
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

MIMETYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
}


def natural_key(s: str) -> list:
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def image_size(data: bytes, ext: str) -> tuple[int, int]:
    """Read image dimensions without external deps. Falls back to 1200x1600."""
    try:
        if ext == '.png' and data[:8] == b'\x89PNG\r\n\x1a\n':
            w, h = struct.unpack('>II', data[16:24])
            return w, h
        if ext in ('.jpg', '.jpeg'):
            i = 2
            while i + 3 < len(data):
                if data[i] != 0xFF:
                    break
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                    h, w = struct.unpack('>HH', data[i + 5:i + 9])
                    return w, h
                seg_len = struct.unpack('>H', data[i + 2:i + 4])[0]
                i += 2 + seg_len
    except Exception:
        pass
    return 1200, 1600


def make_page_xhtml(page_num: int, img_rel: str, width: int, height: int, title: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <meta charset="UTF-8"/>
  <title>{title} — Page {page_num}</title>
  <meta name="viewport" content="width={width}, height={height}"/>
  <style>
    html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #000; }}
    img {{ width: 100%; height: 100%; object-fit: contain; display: block; }}
  </style>
</head>
<body>
  <img src="{img_rel}" alt="Page {page_num}"/>
</body>
</html>'''


def make_nav(title: str, page_count: int) -> str:
    items = '\n'.join(
        f'      <li><a href="pages/page{i:04d}.xhtml">Page {i}</a></li>'
        for i in range(1, page_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops">
<head><meta charset="UTF-8"/><title>{title}</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>{title}</h1>
    <ol>
{items}
    </ol>
  </nav>
</body>
</html>'''


def make_opf(title: str, book_id: str, now: str, manifest: list[str], spine: list[str]) -> str:
    manifest_xml = '\n    '.join(manifest)
    spine_xml = '\n    '.join(spine)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf"
         xmlns:dc="http://purl.org/dc/elements/1.1/"
         version="3.0"
         unique-identifier="book-id">
  <metadata>
    <dc:identifier id="book-id">{book_id}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">{now}</meta>
    <meta property="rendition:layout">pre-paginated</meta>
    <meta property="rendition:spread">landscape</meta>
    <meta property="rendition:orientation">auto</meta>
  </metadata>
  <manifest>
    {manifest_xml}
  </manifest>
  <spine>
    {spine_xml}
  </spine>
</package>'''


def convert(cbz_path: Path, output_path: Path) -> None:
    title = cbz_path.stem
    book_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    with zipfile.ZipFile(cbz_path) as zf:
        image_names = sorted(
            [n for n in zf.namelist() if Path(n).suffix.lower() in IMAGE_EXTS],
            key=natural_key,
        )
        if not image_names:
            sys.exit(f'No images found in {cbz_path}')

        pages = []
        for name in image_names:
            ext = Path(name).suffix.lower()
            data = zf.read(name)
            w, h = image_size(data, ext)
            pages.append((ext, data, w, h))

    manifest: list[str] = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    ]
    spine: list[str] = []

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
        # mimetype — must be first and uncompressed
        info = zipfile.ZipInfo('mimetype')
        info.compress_type = zipfile.ZIP_STORED
        epub.writestr(info, 'application/epub+zip')

        epub.writestr('META-INF/container.xml', '''\
<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>''')

        for i, (ext, data, w, h) in enumerate(pages):
            n = i + 1
            img_id = f'img{n:04d}'
            page_id = f'page{n:04d}'
            img_href = f'images/{n:04d}{ext}'
            page_href = f'pages/page{n:04d}.xhtml'

            epub.writestr(f'OEBPS/{img_href}', data)
            epub.writestr(
                f'OEBPS/{page_href}',
                make_page_xhtml(n, f'../{img_href}', w, h, title),
            )

            manifest.append(
                f'<item id="{img_id}" href="{img_href}" media-type="{MIMETYPES[ext]}"/>'
            )
            manifest.append(
                f'<item id="{page_id}" href="{page_href}" media-type="application/xhtml+xml"/>'
            )
            spine.append(f'<itemref idref="{page_id}"/>')

        epub.writestr('OEBPS/nav.xhtml', make_nav(title, len(pages)))
        epub.writestr('OEBPS/content.opf', make_opf(title, book_id, now, manifest, spine))

    size_mb = output_path.stat().st_size / 1_048_576
    print(f'Created: {output_path}  ({len(pages)} pages, {size_mb:.1f} MB)')


def main() -> None:
    parser = argparse.ArgumentParser(description='Convert CBZ to fixed-layout EPUB3')
    parser.add_argument('input', nargs='+', help='CBZ file(s)')
    parser.add_argument('-o', '--output', help='Output path (single input only)')
    args = parser.parse_args()

    if args.output and len(args.input) > 1:
        sys.exit('--output only works with a single input file')

    for path in args.input:
        cbz = Path(path)
        if not cbz.exists():
            print(f'Not found: {cbz}', file=sys.stderr)
            continue
        out = Path(args.output) if args.output else cbz.with_suffix('.epub')
        convert(cbz, out)


if __name__ == '__main__':
    main()
