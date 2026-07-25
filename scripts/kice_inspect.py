import csv
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path('work')
ROOT.mkdir(exist_ok=True)
S = requests.Session()
S.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36'})

POSTS = {
    (2017,'6월'): 'https://legendstudy.com/m/967',
    (2017,'9월'): 'https://legendstudy.com/m/1037',
    (2018,'6월'): 'https://legendstudy.com/1127',
    (2018,'9월'): 'https://legendstudy.com/m/1216',
    (2019,'6월'): 'https://legendstudy.com/m/1289',
    (2019,'9월'): 'https://legendstudy.com/m/1355',
    (2020,'6월'): 'https://legendstudy.com/m/1447',
    (2020,'9월'): 'https://legendstudy.com/m/1416',
    (2021,'6월'): 'https://legendstudy.com/m/1433',
    (2021,'9월'): 'https://legendstudy.com/m/1435',
}

rows=[]
for (year,exam), post_url in POSTS.items():
    r=S.get(post_url,timeout=45); r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser')
    found=[]
    for a in soup.find_all('a',href=True):
        href=urljoin(r.url,a['href'])
        text=re.sub(r'\s+',' ',a.get_text(' ')).strip()
        decoded=requests.utils.unquote(href)
        hay=(text+' '+decoded).lower()
        if '.pdf' not in hay: continue
        if '수학' not in hay and 'math' not in hay: continue
        if '가형' not in hay and 'matha' not in hay: continue
        if '문제' not in hay and 'mun' not in hay: continue
        if any(x in hay for x in ['해설','정답','답지','answer','solution']): continue
        try:
            rr=S.get(href,timeout=60,headers={'Referer':r.url})
            ok=rr.status_code==200 and rr.content[:5]==b'%PDF-'
            size=len(rr.content)
        except Exception as e:
            ok=False; size=0
        found.append((href,text,ok,size))
    # Prefer verified direct PDF links and de-duplicate by URL.
    seen=set()
    for href,text,ok,size in found:
        if href in seen: continue
        seen.add(href)
        rows.append({'school_year':year,'exam':exam,'post_url':r.url,'anchor':text,'pdf_url':href,'is_pdf':ok,'size':size})
        print(year,exam,ok,size,text,href)

fields=['school_year','exam','post_url','anchor','pdf_url','is_pdf','size']
with open(ROOT/'legendstudy_math_sources.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
print('rows',len(rows),'verified',sum(bool(r['is_pdf']) for r in rows))
