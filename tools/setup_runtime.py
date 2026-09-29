"""Reproducible local setup. Extract archives; never execute their installers."""
import hashlib
from pathlib import Path
import os
import subprocess
import sys
from urllib.request import urlopen
import venv

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.tools'
ASSETS = [
    ('7zr.exe', 'https://github.com/ip7z/7zip/releases/download/26.03/7zr.exe',
     'ad4c82fadcbdf93c03b4fc440f300509c7d60c5c2f4d183e35d9d70d6957037d'),
    ('7z-setup.exe', 'https://github.com/ip7z/7zip/releases/download/26.03/7z2603-x64.exe',
     '0859c524b8a63551848f0c246abddcb1d0b7b656b0fbfe879f8d85e61a9e6edd'),
    ('tesseract-setup.exe', 'https://github.com/tesseract-ocr/tesseract/releases/download/5.5.3/tesseract-ocr-w64-setup-5.5.3.20260724.exe',
     'bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4'),
]
MODEL_HASHES = {
    'chi_sim': 'a5fcb6f0db1e1d6d8522f39db4e848f05984669172e584e8d76b6b3141e1f730',
    'chi_tra': '529c5b5797d64b126065cd55f2bb4c7fd7b15790798091b1ff259941a829330b',
    'eng': '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2',
    'jpn': '1f5de9236d2e85f5fdf4b3c500f2d4926f8d9449f28f5394472d9e8d83b91b4d',
    'kor': '6b85e11d9bbf07863b97b3523b1b112844c43e713df8b66418a081fd1060b3b2',
}


def download(url, path, digest=None):
    if path.exists() and (digest is None or hashlib.sha256(path.read_bytes()).hexdigest() == digest):
        return
    print('Download:', path.name, flush=True)
    with urlopen(url, timeout=90) as response:
        data = response.read()
    if digest and hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError('SHA256 mismatch: ' + path.name)
    temp = path.with_suffix(path.suffix + '.download')
    temp.write_bytes(data)
    temp.replace(path)


def run(args):
    proc = subprocess.run([str(a) for a in args], cwd=ROOT, capture_output=True,
                          text=True, encoding='utf-8', errors='replace',
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if proc.stdout:
        print(proc.stdout, flush=True)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, flush=True)
    proc.check_returncode()


def main():
    if os.name != 'nt' or sys.version_info < (3, 11):
        raise RuntimeError('Requires Windows and Python 3.11+ (including Tcl/Tk).')
    import tkinter  # Fail before downloading if the interpreter lacks Tcl/Tk.
    TOOLS.mkdir(exist_ok=True)
    if not (ROOT / '.venv/Scripts/python.exe').exists():
        venv.create(ROOT / '.venv', with_pip=True)
    python = ROOT / '.venv/Scripts/python.exe'
    run([python, '-m', 'pip', 'install', '-r', ROOT / 'requirements.txt'])
    for filename, url, digest in ASSETS:
        download(url, TOOLS / filename, digest)
    if not (TOOLS / '7zip/7z.exe').exists():
        run([TOOLS / '7zr.exe', 'x', TOOLS / '7z-setup.exe', '-o' + str(TOOLS / '7zip'), '-y'])
    if not (TOOLS / 'tesseract/tesseract.exe').exists():
        run([TOOLS / '7zip/7z.exe', 'x', TOOLS / 'tesseract-setup.exe', '-o' + str(TOOLS / 'tesseract'), '-y'])
    for language in ('kor', 'eng', 'chi_tra', 'chi_sim', 'jpn'):
        download(f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/{language}.traineddata',
                 TOOLS / 'tesseract/tessdata' / (language + '.traineddata'), MODEL_HASHES[language])
    run([TOOLS / 'tesseract/tesseract.exe', '--list-langs'])
    print('Ready. Run start.cmd. Microsoft Edge is required for DAK.GG lookup.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Setup failed:', exc, file=sys.stderr)
        sys.exit(1)
