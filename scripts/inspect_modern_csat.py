import csv
import re
from pathlib import Path
from urllib.parse import quote

import fitz
import requests

ROOT = Path('inspect_csat')
ROOT.mkdir(exist_ok=True)
S = requests.Session()
S.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36'})

def hu(name):
    return 'https://horaeng.com/wp-content/uploads/' + quote(name, safe='-_.')

URLS = {
    2022: hu('2022학년도-대학수학능력시험-수학-문제.pdf'),
    2023: hu('2023학년도-대학수학능력시험-수학-문제.pdf'),
    2024: hu('2024학년도-대학수학능력시험-수학-문제.pdf'),
    2025: hu('2025학년도-대학수학능력시험-수학-문제.pdf'),
    2026: hu('2026학년도-대학수학능력시험-수학-문제.pdf'),
}

def has_q(page, q):
    if page.search_for(f'{q}.'):
        return True
    for w in page.get_text('words'):
        t = str(w[4]).replace(' ', '').strip()
        if t == f'{q}.' or t.startswith(f'{q}.'):
            return True
    return False

rows=[]
for year,url in URLS.items():
    path=ROOT/f'{year}.pdf'
    r=S.get(url,timeout=90,headers={'Referer':'https://horaeng.com/'})
    r.raise_for_status(); path.write_bytes(r.content)
    doc=fitz.open(path)
    for pno,page in enumerate(doc, start=1):
        text=' '.join(page.get_text().split())
        flags={str(q):has_q(page,q) for q in [23,24,25,26,27,28,29,30]}
        markers=[]
        for term in ['확률과 통계','미적분','기하','선택과목','홀수형','짝수형']:
            if term in text: markers.append(term)
        if markers or any(flags.values()):
            rows.append({
                'year':year,'page':pno,'markers':'|'.join(markers),
                **{f'q{q}':int(flags[str(q)]) for q in [23,24,25,26,27,28,29,30]},
                'text_start':text[:350]
            })
    print(year, doc.page_count)

fields=['year','page','markers']+[f'q{q}' for q in [23,24,25,26,27,28,29,30]]+['text_start']
with open(ROOT/'modern_csat_pages.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
print('rows',len(rows))
