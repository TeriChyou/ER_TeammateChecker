"""Local multilingual OCR. Only cropped images reach Tesseract via stdin."""
from dataclasses import dataclass
from pathlib import Path
import csv
import io
import os
import shutil
import subprocess
import unicodedata
from PIL import Image, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = {'自動（韓／英／中／日）': ('kor', 'eng', 'chi_tra', 'chi_sim', 'jpn'),
             '韓文優先': ('kor', 'eng'), '英文': ('eng',),
             '繁體中文': ('chi_tra', 'eng'), '簡體中文': ('chi_sim', 'eng'), '日文': ('jpn', 'eng')}
LABELS = {'kor': '韓', 'eng': '英', 'jpn': '日', 'chi_tra': '繁中', 'chi_sim': '簡中'}


class OcrError(Exception):
    pass


@dataclass(frozen=True)
class Candidate:
    name: str
    confidence: float
    languages: str


def confident_choice(choices):
    """Avoid auto-querying when different name readings score almost equally."""
    return bool(choices and choices[0].confidence >= 75 and
                (len(choices) == 1 or choices[0].confidence - choices[1].confidence >= 8))


def normalize_name(text):
    # OCR splits CJK syllables into words. Preserve symbols and case in names.
    return ''.join(c for c in unicodedata.normalize('NFC', text)
                   if not c.isspace() and unicodedata.category(c) not in ('Cc', 'Cf'))


def parse_tsv(text):
    words = []
    for row in csv.DictReader(io.StringIO(text), delimiter='\t', quoting=csv.QUOTE_NONE):
        try:
            confidence = float(row.get('conf', '-1'))
        except (TypeError, ValueError):
            continue
        word = normalize_name(row.get('text') or '')
        if word and confidence >= 0:
            words.append((word, confidence))
    name = ''.join(w for w, _ in words)
    if not 1 <= len(name) <= 64 or not any(c.isalnum() for c in name):
        return None
    confidence = sum(len(w) * c for w, c in words) / sum(len(w) for w, _ in words)
    return name, confidence


def prepare_image(image, threshold=False):
    gray = ImageOps.autocontrast(image.convert('L'))
    # Name crops generally contain light text over a dark game panel.
    if ImageStat.Stat(gray).mean[0] < 127:
        gray = ImageOps.invert(gray)
    scale = max(1, min(4, 96 / max(1, gray.height)))
    gray = gray.resize((round(gray.width * scale), round(gray.height * scale)), Image.Resampling.LANCZOS)
    if threshold:
        gray = gray.point(lambda p: 255 if p > 150 else 0)
    return ImageOps.expand(gray, border=16, fill=255)


class Recognizer:
    def __init__(self, executable=None):
        local = ROOT / '.tools/tesseract/tesseract.exe'
        self.executable = str(executable or os.getenv('ER_TESSERACT') or
                              (local if local.exists() else shutil.which('tesseract') or ''))
        if not self.executable:
            raise OcrError('找不到 OCR 引擎，請先執行 setup.ps1。')
        self.flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    def recognize(self, image, language='自動（韓／英／中／日）', cancel=None):
        if image.width < 8 or image.height < 8:
            raise OcrError('名稱區域太小，請重新框選完整的一行名稱。')
        if image.width > 2500 or image.height > 500:
            raise OcrError('請只框住名稱，不要框整個畫面（每格最多 2500×500）。')
        pool = {}
        failures = 0
        for threshold in (False, True):
            prepared = prepare_image(image, threshold)
            data = io.BytesIO()
            prepared.save(data, format='PNG')
            for lang in LANGUAGES.get(language, LANGUAGES[next(iter(LANGUAGES))]):
                if cancel and cancel.is_set():
                    raise OcrError('辨識已取消。')
                cmd = [self.executable, 'stdin', 'stdout', '-l', lang, '--psm', '7',
                       '-c', 'tessedit_do_invert=0', '-c', 'load_system_dawg=0', '-c', 'load_freq_dawg=0', 'tsv']
                env = dict(os.environ, OMP_THREAD_LIMIT='1')
                try:
                    proc = subprocess.run(cmd, input=data.getvalue(), capture_output=True, timeout=8,
                                          creationflags=self.flags, env=env)
                except (OSError, subprocess.TimeoutExpired):
                    raise OcrError('OCR 引擎無法啟動或辨識逾時，請檢查 setup.ps1 安裝結果。') from None
                if proc.returncode:
                    failures += 1
                    continue
                parsed = parse_tsv(proc.stdout.decode('utf-8', errors='replace'))
                if parsed:
                    name, confidence = parsed
                    record = pool.setdefault(name, {'confidence': 0, 'langs': set(), 'votes': 0})
                    record['confidence'] = max(record['confidence'], confidence)
                    record['langs'].add(LABELS[lang])
                    record['votes'] += 1
        if failures:
            raise OcrError('OCR 語言模型缺失或不可讀，請重新執行 setup.ps1。')
        ranked = sorted(pool.items(), key=lambda pair: pair[1]['confidence'] + min(pair[1]['votes'] - 1, 3) * 2, reverse=True)
        return [Candidate(name, round(record['confidence'], 1), '/'.join(sorted(record['langs'])))
                for name, record in ranked[:6]]
