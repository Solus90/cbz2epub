#!/usr/bin/env python3
"""CBZ → EPUB web converter — local server."""

import io
import sys
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_file

sys.path.insert(0, str(Path(__file__).parent))
from cbz2epub import convert  # noqa: E402

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CBZ → EPUB</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bangers&family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --paper: #F8F3E8;
  --ink:   #15100A;
  --dot:   #D6CBB5;
  --cyan:  #00A8D6;
  --mag:   #D91E78;
  --yel:   #FFD600;
  --grn:   #28B562;
  --red:   #E63228;
  --b:     3px solid #15100A;
  --sh:    6px 6px 0 #15100A;
}

body {
  font-family: 'Courier Prime', monospace;
  background-color: var(--paper);
  background-image: radial-gradient(circle, var(--dot) 1.2px, transparent 1.2px);
  background-size: 10px 10px;
  min-height: 100vh;
  color: var(--ink);
}

.wrap {
  max-width: 680px;
  margin: 0 auto;
  padding: 2rem 1.5rem 5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* ── panels ── */
.panel {
  background: var(--paper);
  border: var(--b);
  box-shadow: var(--sh);
  position: relative;
}

/* ── header ── */
.hd {
  background: var(--ink);
  padding: 1.5rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.hd-title {
  font-family: 'Bangers', cursive;
  font-size: 3.5rem;
  line-height: 1;
  letter-spacing: 0.05em;
  color: var(--yel);
}

.hd-title .arr { color: var(--cyan); }

.hd-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
}

.hd-sub {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: rgba(248,243,232,0.4);
}

.cmyk {
  display: flex;
  gap: 5px;
  align-items: center;
}

.cmyk-dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 1.5px solid rgba(255,255,255,0.2);
}

/* ── drop zone ── */
.dz {
  border: 3px dashed var(--ink);
  cursor: pointer;
  min-height: 210px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: box-shadow 0.12s, background 0.12s, border-color 0.12s;
  overflow: hidden;
  position: relative;
}

.dz:hover        { background: #FFFBEE; box-shadow: 8px 8px 0 var(--yel); }
.dz.over         { background: #EAF7FF; border-color: var(--cyan); box-shadow: 8px 8px 0 var(--cyan); }

/* corner registration marks */
.dz::before,  .dz::after,
.dz-in::before, .dz-in::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  border-color: var(--ink);
  border-style: solid;
  pointer-events: none;
}
.dz::before   { top: 10px;    left: 10px;  border-width: 2px 0 0 2px; }
.dz::after    { top: 10px;    right: 10px; border-width: 2px 2px 0 0; }
.dz-in::before { bottom: 10px; left: 10px;  border-width: 0 0 2px 2px; }
.dz-in::after  { bottom: 10px; right: 10px; border-width: 0 2px 2px 0; }

.dz-in {
  text-align: center;
  padding: 2.5rem 2rem;
  pointer-events: none;
  position: relative;
  width: 100%;
}

.dz-arrow {
  font-family: 'Bangers', cursive;
  font-size: 3.5rem;
  color: var(--ink);
  line-height: 1;
  display: block;
  margin-bottom: 0.4rem;
}

.dz-label {
  font-family: 'Bangers', cursive;
  font-size: 2.25rem;
  letter-spacing: 0.08em;
  line-height: 1;
}

.dz-hint {
  margin-top: 0.625rem;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #888;
}

#fileInput {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
}

/* ── file list panel ── */
.fl-panel         { display: none; }
.fl-panel.show    { display: block; }

.fl-head {
  background: var(--ink);
  color: var(--yel);
  font-family: 'Bangers', cursive;
  font-size: 1.125rem;
  letter-spacing: 0.12em;
  padding: 0.6rem 1.25rem;
  border-bottom: var(--b);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fl-count {
  font-family: 'Courier Prime', monospace;
  font-size: 0.6875rem;
  letter-spacing: 0.08em;
  color: rgba(248,243,232,0.45);
  font-weight: 400;
}

.fl-list { list-style: none; }

/* ── file item ── */
.fi {
  display: grid;
  grid-template-columns: 30px 1fr auto auto;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.25rem;
  border-bottom: 2px solid #C9BFA8;
  transition: background 0.15s;
}
.fi:last-child       { border-bottom: none; }
.fi.s-converting     { background: #FFFCE6; }
.fi.s-done           { background: #EDFFF4; }
.fi.s-error          { background: #FFF2F1; }

.fi-icon {
  width: 28px;
  height: 28px;
  border: 2.5px solid var(--ink);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  flex-shrink: 0;
  background: var(--paper);
  color: #999;
  transition: background 0.2s, border-color 0.2s;
}

.s-converting .fi-icon { background: var(--yel); color: var(--ink); animation: spin 0.7s linear infinite; }
.s-done       .fi-icon { background: var(--grn); border-color: var(--grn); color: #fff; }
.s-error      .fi-icon { background: var(--red); border-color: var(--red); color: #fff; }

@keyframes spin { to { transform: rotate(360deg); } }

.fi-name {
  font-size: 0.9rem;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.fi-size {
  font-size: 0.75rem;
  color: #888;
  white-space: nowrap;
}

.btn-dl {
  font-family: 'Bangers', cursive;
  font-size: 0.9375rem;
  letter-spacing: 0.06em;
  padding: 0.3rem 0.875rem;
  background: var(--cyan);
  color: #fff;
  border: 2px solid var(--ink);
  box-shadow: 3px 3px 0 var(--ink);
  text-decoration: none;
  display: inline-block;
  white-space: nowrap;
  cursor: pointer;
  transition: transform 0.1s, box-shadow 0.1s;
}
.btn-dl:hover  { transform: translate(-1px,-1px); box-shadow: 4px 4px 0 var(--ink); }
.btn-dl:active { transform: translate(2px,2px);   box-shadow: 1px 1px 0 var(--ink); }

.fi-err {
  font-size: 0.7rem;
  color: var(--red);
  max-width: 110px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── footer bar ── */
.fl-foot {
  background: var(--ink);
  padding: 0.875rem 1.25rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem;
  border-top: var(--b);
}

.btn-cvt {
  font-family: 'Bangers', cursive;
  font-size: 1.5rem;
  letter-spacing: 0.12em;
  padding: 0.5rem 2.25rem;
  background: var(--yel);
  color: var(--ink);
  border: 3px solid var(--paper);
  box-shadow: 4px 4px 0 rgba(248,243,232,0.3);
  cursor: pointer;
  transition: transform 0.1s, box-shadow 0.1s, opacity 0.1s;
}
.btn-cvt:hover:not(:disabled)  { transform: translate(-2px,-2px); box-shadow: 6px 6px 0 rgba(248,243,232,0.3); }
.btn-cvt:active:not(:disabled) { transform: translate(2px,2px);   box-shadow: 2px 2px 0 rgba(248,243,232,0.3); }
.btn-cvt:disabled { opacity: 0.35; cursor: default; }

/* ── sound effects ── */
#sfx {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 999;
}

.sfx-word {
  font-family: 'Bangers', cursive;
  font-size: 9rem;
  letter-spacing: 0.04em;
  -webkit-text-stroke: 4px var(--ink);
  text-shadow: 7px 7px 0 rgba(0,0,0,0.12);
  animation: sfx 0.85s cubic-bezier(0.22, 0.61, 0.36, 1) forwards;
}

@keyframes sfx {
  0%   { transform: scale(0) rotate(-6deg);   opacity: 0; }
  22%  { transform: scale(1.15) rotate(-4deg); opacity: 1; }
  40%  { transform: scale(0.96) rotate(-4deg); opacity: 1; }
  68%  { transform: scale(1.0) rotate(-4deg);  opacity: 1; }
  100% { transform: scale(0.85) rotate(-4deg); opacity: 0; }
}
</style>
</head>
<body>

<div id="sfx"></div>

<div class="wrap">

  <header class="panel hd">
    <div class="hd-title">CBZ<span class="arr">→</span>EPUB</div>
    <div class="hd-right">
      <div class="cmyk">
        <div class="cmyk-dot" style="background:var(--cyan)"></div>
        <div class="cmyk-dot" style="background:var(--mag)"></div>
        <div class="cmyk-dot" style="background:var(--yel)"></div>
        <div class="cmyk-dot" style="background:rgba(248,243,232,0.55)"></div>
      </div>
      <span class="hd-sub">Comic archive converter</span>
    </div>
  </header>

  <div class="panel dz" id="dz" tabindex="0" role="button" aria-label="Drop zone for CBZ files">
    <div class="dz-in">
      <span class="dz-arrow">↓</span>
      <p class="dz-label">DROP COMICS HERE</p>
      <p class="dz-hint">drag .cbz files or click to browse &nbsp;·&nbsp; multiple ok</p>
    </div>
    <input type="file" id="fileInput" accept=".cbz" multiple>
  </div>

  <div class="panel fl-panel" id="flPanel">
    <div class="fl-head">
      <span>QUEUE</span>
      <span class="fl-count" id="flCount"></span>
    </div>
    <ul class="fl-list" id="flList"></ul>
    <div class="fl-foot">
      <button class="btn-cvt" id="cvtBtn" disabled>CONVERT ALL</button>
    </div>
  </div>

</div>

<script>
const dz      = document.getElementById('dz');
const inp     = document.getElementById('fileInput');
const panel   = document.getElementById('flPanel');
const list    = document.getElementById('flList');
const cvtBtn  = document.getElementById('cvtBtn');
const flCount = document.getElementById('flCount');
const sfxEl   = document.getElementById('sfx');

const queue = [];

function sfx(word, color) {
  sfxEl.innerHTML = '';
  const el = document.createElement('span');
  el.className = 'sfx-word';
  el.textContent = word;
  el.style.color = color || 'var(--yel)';
  sfxEl.appendChild(el);
  el.addEventListener('animationend', () => el.remove());
}

function fmt(b) {
  return b < 1048576 ? (b / 1024).toFixed(0) + ' KB' : (b / 1048576).toFixed(1) + ' MB';
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function sync() {
  const waiting = queue.filter(e => e.status === 'waiting').length;
  const done    = queue.filter(e => e.status === 'done').length;
  cvtBtn.disabled = waiting === 0;
  flCount.textContent = `${done} / ${queue.length}`;
  panel.classList.toggle('show', queue.length > 0);
}

function addFiles(files) {
  const cbz = [...files].filter(f => f.name.toLowerCase().endsWith('.cbz'));
  if (!cbz.length) return;

  cbz.forEach(file => {
    if (queue.find(e => e.file.name === file.name && e.file.size === file.size)) return;
    const id = crypto.randomUUID();
    queue.push({ id, file, status: 'waiting' });

    const li = document.createElement('li');
    li.className = 'fi s-waiting';
    li.id = `fi-${id}`;
    li.innerHTML = `
      <div class="fi-icon">○</div>
      <span class="fi-name">${esc(file.name.replace(/\.cbz$/i, ''))}</span>
      <span class="fi-size">${fmt(file.size)}</span>
      <div class="fi-action" id="act-${id}"></div>`;
    list.appendChild(li);
  });

  sync();
  sfx('THWUMP!', 'var(--cyan)');
}

function setStatus(id, status, extra) {
  const entry = queue.find(e => e.id === id);
  if (entry) entry.status = status;

  const li  = document.getElementById(`fi-${id}`);
  if (!li) return;
  li.className = `fi s-${status}`;

  const icon = li.querySelector('.fi-icon');
  icon.textContent = { waiting:'○', converting:'◎', done:'✓', error:'✕' }[status] ?? '?';

  const act = document.getElementById(`act-${id}`);
  act.innerHTML = '';

  if (status === 'done' && extra?.blob) {
    const url = URL.createObjectURL(extra.blob);
    const a = document.createElement('a');
    a.className = 'btn-dl';
    a.href = url;
    a.download = (extra.name || 'comic') + '.epub';
    a.textContent = 'DOWNLOAD';
    act.appendChild(a);
  }

  if (status === 'error') {
    const span = document.createElement('span');
    span.className = 'fi-err';
    span.title = extra?.msg || 'Error';
    span.textContent = extra?.msg || 'Error';
    act.appendChild(span);
  }

  sync();
}

async function convertEntry(entry) {
  setStatus(entry.id, 'converting');
  const fd = new FormData();
  fd.append('file', entry.file);
  try {
    const res = await fetch('/convert', { method: 'POST', body: fd });
    if (!res.ok) {
      const j = await res.json().catch(() => ({ error: 'Conversion failed' }));
      setStatus(entry.id, 'error', { msg: j.error });
      sfx('BZZT!', 'var(--red)');
      return false;
    }
    const blob = await res.blob();
    const stem = entry.file.name.replace(/\.cbz$/i, '');
    setStatus(entry.id, 'done', { blob, name: stem });
    return true;
  } catch (e) {
    setStatus(entry.id, 'error', { msg: e.message });
    sfx('BZZT!', 'var(--red)');
    return false;
  }
}

cvtBtn.addEventListener('click', async () => {
  const waiting = queue.filter(e => e.status === 'waiting');
  if (!waiting.length) return;
  cvtBtn.disabled = true;
  sfx('ZAP!', 'var(--mag)');
  let ok = 0;
  for (const entry of waiting) {
    if (await convertEntry(entry)) ok++;
  }
  if (ok > 0) sfx('KAPOW!', 'var(--yel)');
  sync();
});

dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('over'); });
dz.addEventListener('dragleave', e => { if (!dz.contains(e.relatedTarget)) dz.classList.remove('over'); });
dz.addEventListener('drop',      e => { e.preventDefault(); dz.classList.remove('over'); addFiles(e.dataTransfer.files); });
inp.addEventListener('change',   () => { addFiles(inp.files); inp.value = ''; });
dz.addEventListener('keydown',   e => { if (e.key === 'Enter' || e.key === ' ') inp.click(); });
</script>
</body>
</html>"""


@app.route('/')
def index():
    return HTML, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/convert', methods=['POST'])
def convert_route():
    if 'file' not in request.files:
        return jsonify(error='No file provided'), 400
    f = request.files['file']
    if not f.filename or not f.filename.lower().endswith('.cbz'):
        return jsonify(error='File must be a .cbz archive'), 400

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cbz = tmp / 'input.cbz'
        epub = tmp / 'output.epub'
        f.save(str(cbz))
        try:
            convert(cbz, epub)
        except SystemExit as e:
            return jsonify(error=str(e)), 500
        except Exception as e:
            return jsonify(error=str(e)), 500
        data = epub.read_bytes()

    stem = Path(f.filename).stem
    return send_file(
        io.BytesIO(data),
        mimetype='application/epub+zip',
        as_attachment=True,
        download_name=f'{stem}.epub',
    )


if __name__ == '__main__':
    port = 5757
    print(f'\n  CBZ → EPUB  →  http://localhost:{port}\n')
    app.run(host='127.0.0.1', port=port, debug=False)
