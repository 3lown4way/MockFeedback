import csv
import json
import re
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path('work')
ROOT.mkdir(exist_ok=True)
S = requests.Session()
S.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36'})


def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()

posts = []
for page in range(1, 80):
    url = f'https://horaeng.com/wp-json/wp/v2/posts?per_page=100&page={page}&_fields=id,date,link,title,content'
    r = S.get(url, timeout=40)
    if r.status_code == 400 and 'rest_post_invalid_page_number' in r.text:
        break
    r.raise_for_status()
    batch = r.json()
    if not batch:
        break
    posts.extend(batch)
    print('posts page', page, 'count', len(batch))

(ROOT/'horaeng_posts.json').write_text(json.dumps(posts, ensure_ascii=False), encoding='utf-8')
rows = []
for post in posts:
    title = norm(BeautifulSoup(post.get('title', {}).get('rendered', ''), 'html.parser').get_text(' '))
    soup = BeautifulSoup(post.get('content', {}).get('rendered', ''), 'html.parser')
    text = norm(soup.get_text(' '))
    combined = title + ' ' + text[:1200]
    found_years = {int(x) for x in re.findall(r'(20(?:1[2-9]|2[0-7]))\s*학년도', combined)}
    for cal in re.findall(r'(20(?:1[1-9]|2[0-6]))\s*년', combined):
        found_years.add(int(cal) + 1)
    target_years = sorted(y for y in found_years if 2012 <= y <= 2027)
    if not target_years:
        continue
    exam = ''
    if re.search(r'6\s*월', combined): exam = '6월'
    if re.search(r'9\s*월', combined): exam = '9월'
    if re.search(r'수능|대학수학능력시험', combined): exam = '수능'
    if not exam:
        continue
    for a in soup.find_all('a', href=True):
        href = urljoin(post.get('link',''), a['href'])
        anchor = norm(a.get_text(' '))
        decoded = requests.utils.unquote(href)
        hay = (anchor + ' ' + decoded).lower()
        if '.pdf' not in hay or not ('수학' in hay or 'math' in hay):
            continue
        if not ('문제' in hay or 'question' in hay or 'mun' in hay):
            continue
        if any(bad in hay for bad in ['해설', '정답', '답지', 'solution', 'answer']):
            continue
        for y in target_years:
            rows.append({'school_year': y, 'exam': exam, 'post_title': title, 'post_url': post.get('link',''), 'anchor': anchor, 'pdf_url': href})

# Modern direct URL patterns as fallback.
def enc_name(name):
    return 'https://horaeng.com/wp-content/uploads/' + quote(name, safe='-_.')
for y in range(2022, 2028):
    exams = [('6월', f'{y}학년도-6월-모의평가-수학-문제.pdf'), ('9월', f'{y}학년도-9월-모의평가-수학-문제.pdf')]
    if y <= 2026:
        exams.append(('수능', f'{y}학년도-대학수학능력시험-수학-문제.pdf'))
    for exam, fn in exams:
        url = enc_name(fn)
        try:
            rr = S.head(url, timeout=20, allow_redirects=True)
            if rr.status_code < 400:
                rows.append({'school_year': y, 'exam': exam, 'post_title': 'direct-pattern', 'post_url': '', 'anchor': fn, 'pdf_url': url})
        except Exception:
            pass

uniq = {}
for r in rows:
    uniq[(r['school_year'], r['exam'], r['pdf_url'])] = r
verified = []
for r in sorted(uniq.values(), key=lambda x: (x['school_year'], {'6월':0,'9월':1,'수능':2}.get(x['exam'],9), x['pdf_url'])):
    try:
        rr = S.get(r['pdf_url'], timeout=45, headers={'Referer': r['post_url'] or 'https://horaeng.com/'})
        ok = rr.status_code == 200 and rr.content[:5] == b'%PDF-'
        r.update(status=rr.status_code, size=len(rr.content), is_pdf=ok, error='')
        if ok: verified.append(r)
        print(r['school_year'], r['exam'], rr.status_code, len(rr.content), ok, r['pdf_url'])
    except Exception as e:
        r.update(status='ERR', size=0, is_pdf=False, error=repr(e))

all_rows = sorted(uniq.values(), key=lambda x: (x['school_year'], x['exam'], x['pdf_url']))
fields = ['school_year','exam','post_title','post_url','anchor','pdf_url','status','size','is_pdf','error']
for name, data in [('horaeng_candidates.csv', all_rows), ('horaeng_verified.csv', verified)]:
    with open(ROOT/name, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(data)
print('posts', len(posts), 'candidates', len(all_rows), 'verified', len(verified))
