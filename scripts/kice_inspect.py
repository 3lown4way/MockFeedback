import csv
import io
import json
import os
import zipfile
from pathlib import Path

import gdown

ROOT = Path('work')
ROOT.mkdir(exist_ok=True)

PDF_LIST_ID = '1nByzdtGHT07SJjeE7qfYOcrt0ofCyBOt'
META_ID = '1ZSZPoFtkWSLR8aDMg8Hw-bOzM6IqXvvQ'

pdf_list_path = ROOT / 'kcsat-ml.json'
meta_zip_path = ROOT / 'kcsat-ml-meta.zip'

gdown.download(id=PDF_LIST_ID, output=str(pdf_list_path), quiet=False)
gdown.download(id=META_ID, output=str(meta_zip_path), quiet=False)

with open(pdf_list_path, 'r', encoding='utf-8') as f:
    source_map = json.load(f)

meta_dir = ROOT / 'meta'
meta_dir.mkdir(exist_ok=True)
with zipfile.ZipFile(meta_zip_path) as zf:
    zf.extractall(meta_dir)

rows = []
for p in sorted(meta_dir.rglob('*.json')):
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    m = data.get('meta', {})
    year = m.get('year')
    q = m.get('question_number')
    try:
        year_i = int(year)
        q_i = int(q)
    except Exception:
        continue
    if not (2017 <= year_i <= 2025 and q_i >= 21):
        continue
    subject = str(m.get('subject', ''))
    if 'Math' not in subject and '수학' not in subject:
        continue
    error = data.get('error', {})
    rate = error.get('wrong_error_rate', '')
    image = data.get('image', {})
    image_items = image.get('short_answer') or image.get('multiple_choice') or []
    image_names = sorted({str(it.get('image_name', '')) for it in image_items if isinstance(it, dict)})
    rows.append({
        'meta_file': p.name,
        'year': year_i,
        'question': q_i,
        'subject': subject,
        'domain': str(m.get('domain', '')),
        'exam': str(m.get('exam', m.get('test', m.get('month', '')))),
        'wrong_rate': rate,
        'image_names': '|'.join(image_names),
        'image_json': json.dumps(image_items, ensure_ascii=False),
        'answer': json.dumps(data.get('answer', {}), ensure_ascii=False),
    })

rows.sort(key=lambda r: (r['year'], r['image_names'], r['question']))

out_csv = ROOT / 'math_items_2017_2025.csv'
with open(out_csv, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['year'])
    w.writeheader()
    w.writerows(rows)

(ROOT / 'source_map.json').write_text(json.dumps(source_map, ensure_ascii=False, indent=2), encoding='utf-8')
print('source files:', len(source_map))
print('matching items:', len(rows))
for r in rows[:80]:
    print(r['year'], r['image_names'], r['question'], r['domain'], r['wrong_rate'])
