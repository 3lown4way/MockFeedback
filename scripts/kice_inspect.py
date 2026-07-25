import csv
import io
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import quote

import fitz
import requests
from PIL import Image, ImageOps, ImageDraw

ROOT = Path('work')
SRC = ROOT / 'sources'
OUT = Path('out')
SRC.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

S = requests.Session()
S.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36'})

# Verified official KICE-distribution copies from LegendStudy (June/September, old GA format).
LEGEND = {
 (2017,'6월'): ('https://t1.daumcdn.net/cfile/tistory/2607BC405771F43717','https://legendstudy.com/m/967'),
 (2017,'9월'): ('https://t1.daumcdn.net/cfile/tistory/2215524658005A7D11','https://legendstudy.com/m/1037'),
 (2018,'6월'): ('https://t1.daumcdn.net/cfile/tistory/255C1F4B5959713C23','https://legendstudy.com/1127'),
 (2018,'9월'): ('https://t1.daumcdn.net/cfile/tistory/99A25D3359CB4EA61E','https://legendstudy.com/m/1216'),
 (2019,'6월'): ('https://t1.daumcdn.net/cfile/tistory/999AFE385B3BA1173E','https://legendstudy.com/m/1289'),
 (2019,'9월'): ('https://t1.daumcdn.net/cfile/tistory/99D4203A5BB3359310','https://legendstudy.com/m/1355'),
 (2020,'6월'): ('https://t1.daumcdn.net/cfile/tistory/99B599355FBB3A5725','https://legendstudy.com/m/1447'),
 (2020,'9월'): ('https://t1.daumcdn.net/cfile/tistory/99790F3F5E69FAE219','https://legendstudy.com/m/1416'),
 (2021,'6월'): ('https://t1.daumcdn.net/cfile/tistory/9965E2445F7C17F640','https://legendstudy.com/m/1433'),
 (2021,'9월'): ('https://t1.daumcdn.net/cfile/tistory/996DF2465F7C183101','https://legendstudy.com/m/1435'),
}

# Direct KICE source archives for the CSAT. KCSAT-ML's source map points to these public KICE files.
KICE_ZIP = {
 2017:'https://www.suneung.re.kr/boardCnts/fileDown.do?fileSeq=f9282e44289e046bb7821696d15134c8',
 2018:'https://www.suneung.re.kr/boardCnts/fileDown.do?fileSeq=23796a8ae718563729ef7122e17631b7',
 2019:'https://www.suneung.re.kr/boardCnts/fileDown.do?fileSeq=4553b864eb3fde8ee1278518054792e2',
 2020:'https://www.suneung.re.kr/boardCnts/fileDown.do?fileSeq=96bd784674f047d6767cce15b7ffb5e4',
 2021:'https://www.suneung.re.kr/boardCnts/fileDown.do?fileSeq=f5325111f2fe0e289d26b0cf444b1401',
}

# Verified official KICE PDF copies from Horaeng for the current choice-subject format.
def hu(name):
    return 'https://horaeng.com/wp-content/uploads/' + quote(name, safe='-_.')
MODERN = {
 (2022,'6월'): hu('2022학년도-대수능-6월-모의평가-수학-문제.pdf'),
 (2022,'9월'): hu('2022학년도-대수능-9월-모의평가-수학-문제.pdf'),
 (2022,'수능'): hu('2022학년도-대학수학능력시험-수학-문제.pdf'),
 (2023,'6월'): hu('2023학년도-6월-모의평가-수학-문제.pdf'),
 (2023,'9월'): hu('2023학년도-9월-모의평가-수학-문제.pdf'),
 (2023,'수능'): hu('2023학년도-대학수학능력시험-수학-문제.pdf'),
 (2024,'6월'): hu('2024학년도-6월-모의평가-수학-문제.pdf'),
 (2024,'9월'): hu('2024학년도-9월-모의평가-수학-문제.pdf'),
 (2024,'수능'): hu('2024학년도-대학수학능력시험-수학-문제.pdf'),
 (2025,'6월'): hu('2025학년도-6월-모의평가-수학-문제.pdf'),
 (2025,'9월'): hu('2025학년도-9월-모의평가-수학-문제.pdf'),
 (2025,'수능'): hu('2025학년도-대학수학능력시험-수학-문제.pdf'),
 (2026,'6월'): hu('2026학년도-6월-모의평가-수학-문제.pdf'),
 (2026,'9월'): hu('2025년-9월-고3-모의고사-수학-문제.pdf'),
 (2026,'수능'): hu('2026학년도-대학수학능력시험-수학-문제.pdf'),
 (2027,'6월'): hu('2027학년도-6월-모의평가-수학-문제.pdf'),
}

# High-difficulty selection agreed in the conversation. This list controls selection only;
# every visible problem is cropped directly from the official source above.
SELECTION = [
 (2017,'6월','GA',29),(2017,'6월','GA',30),(2017,'9월','GA',21),(2017,'9월','GA',30),(2017,'수능','GA',21),
 (2018,'6월','GA',21),(2018,'6월','GA',30),(2018,'9월','GA',21),(2018,'9월','GA',30),(2018,'수능','GA',21),(2018,'수능','NA',30),(2018,'수능','GA',30),
 (2019,'6월','GA',21),(2019,'6월','GA',30),(2019,'9월','GA',21),(2019,'9월','GA',30),(2019,'수능','GA',21),(2019,'수능','GA',30),
 (2020,'6월','GA',21),(2020,'6월','GA',30),(2020,'9월','GA',30),(2020,'수능','GA',21),(2020,'수능','GA',30),
 (2021,'6월','GA',30),(2021,'9월','GA',30),(2021,'수능','GA',30),
 (2022,'6월','CALC',29),(2022,'6월','CALC',30),(2022,'9월','CALC',29),(2022,'9월','CALC',30),(2022,'수능','CALC',29),(2022,'수능','CALC',30),
 (2023,'6월','CALC',29),(2023,'6월','CALC',30),(2023,'9월','CALC',29),(2023,'9월','CALC',30),(2023,'수능','CALC',28),(2023,'수능','CALC',29),(2023,'수능','CALC',30),
 (2024,'6월','CALC',29),(2024,'6월','CALC',30),(2024,'9월','CALC',29),(2024,'9월','CALC',30),(2024,'수능','CALC',29),(2024,'수능','CALC',30),
 (2025,'6월','CALC',29),(2025,'6월','CALC',30),(2025,'9월','CALC',30),(2025,'수능','CALC',30),
 (2026,'6월','CALC',29),(2026,'6월','CALC',30),(2026,'9월','CALC',29),(2026,'9월','CALC',30),(2026,'수능','CALC',29),(2026,'수능','CALC',30),
 (2027,'6월','CALC',29),(2027,'6월','CALC',30),
]


def download(url, path, referer=None):
    if path.exists() and path.stat().st_size > 1000:
        return path
    h = {'Referer': referer} if referer else {}
    with S.get(url, headers=h, timeout=90, stream=True) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for ch in r.iter_content(1024*128):
                if ch: f.write(ch)
    magic = path.read_bytes()[:5]
    if path.suffix.lower()=='.pdf' and magic != b'%PDF-':
        raise RuntimeError(f'Not a PDF: {url}, magic={magic!r}, size={path.stat().st_size}')
    return path

source_info = {}
# Old June/September PDFs.
for key,(url,post) in LEGEND.items():
    p=SRC/f'{key[0]}_{key[1]}_GA.pdf'
    download(url,p,post)
    source_info[(key[0],key[1],'GA')] = (p,url,post)

# Old CSAT archives. KCSAT-ML generator enumerates members as year-index;
# its metadata identifies GA as index 2 and NA as index 4.
for year,url in KICE_ZIP.items():
    zp=SRC/f'{year}_csat.zip'; download(url,zp,'https://www.suneung.re.kr/')
    with zipfile.ZipFile(zp) as zf:
        names=[n for n in zf.namelist() if not n.endswith('/')]
        if len(names)<4: raise RuntimeError(f'{year} archive has only {len(names)} members: {names}')
        for subj,idx in [('GA',1),('NA',3)]:
            out=SRC/f'{year}_수능_{subj}.pdf'
            out.write_bytes(zf.read(names[idx]))
            if out.read_bytes()[:5]!=b'%PDF-': raise RuntimeError(f'Bad member {year} {subj}: {names[idx]}')
            source_info[(year,'수능',subj)] = (out,url+'#member='+str(idx+1),'https://www.suneung.re.kr/')

# Modern PDFs.
for key,url in MODERN.items():
    p=SRC/f'{key[0]}_{key[1]}_수학.pdf'
    download(url,p,'https://horaeng.com/')
    source_info[(key[0],key[1],'CALC')] = (p,url,'https://horaeng.com/')


def number_rects(page,q):
    rects=[]
    for token in (f'{q}.', f'{q} .'):
        try: rects += page.search_for(token)
        except Exception: pass
    if rects: return rects
    for w in page.get_text('words'):
        t=str(w[4]).strip().replace(' ', '')
        if t==f'{q}.' or t.startswith(f'{q}.'):
            rects.append(fitz.Rect(w[:4]))
    return rects


def locate(doc,q,modern=False):
    hits=[]
    for pno,page in enumerate(doc):
        rs=number_rects(page,q)
        if rs:
            # Deduplicate close rectangles and prefer the uppermost actual number.
            rs=sorted(rs,key=lambda r:(r.y0,r.x0))
            hits.append((pno,rs[0]))
    # One page per subject occurrence is expected. Modern booklets contain
    # probability/calculus/geometry in that order, so calculus is the middle hit.
    if not hits:
        raise RuntimeError(f'Question {q} not found in {doc.name}, pages={doc.page_count}')
    if modern and len(hits)>=3:
        return hits[len(hits)//2]
    return hits[0]

FOOTER_WORDS=('확인 사항','답안지의 해당란','이어서','선택과목','저작권','한국교육과정평가원')

def make_clip(page,qrect):
    w,h=page.rect.width,page.rect.height
    right=qrect.x0>w/2
    if right:
        x0,x1=0.505*w,0.965*w
    else:
        x0,x1=0.045*w,0.495*w
    y0=max(0.075*h,qrect.y0-8)
    candidates=[qrect.y1]
    for b in page.get_text('blocks'):
        bx0,by0,bx1,by1,text,*_=b
        if bx1<x0 or bx0>x1 or by1<y0 or by0>0.915*h: continue
        t=' '.join(str(text).split())
        if any(s in t for s in FOOTER_WORDS): continue
        # Bare printed page numbers near the bottom are not problem content.
        if by0>0.86*h and re.fullmatch(r'[\d\s/]+',t or ''): continue
        candidates.append(by1)
    # Include boxes, graphs, and diagrams, but reject page-spanning rules.
    for d in page.get_drawings():
        r=d.get('rect')
        if not r or r.x1<x0 or r.x0>x1 or r.y1<y0 or r.y0>0.91*h: continue
        if r.height>0.78*h: continue
        candidates.append(r.y1)
    try:
        for im in page.get_images(full=True):
            for r in page.get_image_rects(im[0]):
                if r.x1>=x0 and r.x0<=x1 and r.y1>=y0 and r.y0<0.91*h:
                    candidates.append(r.y1)
    except Exception:
        pass
    y1=min(0.925*h,max(candidates)+24)
    if y1-y0<100: y1=min(0.9*h,y0+0.55*h)
    return fitz.Rect(x0,y0,x1,y1)

# Open source docs once.
docs={k:fitz.open(str(v[0])) for k,v in source_info.items()}
items=[]
for year,exam,subj,q in SELECTION:
    key=(year,exam,subj)
    if key not in docs: raise RuntimeError(f'Missing source {key}')
    doc=docs[key]
    pno,qrect=locate(doc,q,modern=(subj=='CALC'))
    clip=make_clip(doc[pno],qrect)
    if not clip.contains(qrect): raise RuntimeError(f'Number excluded {year} {exam} {q}')
    p,url,ref=source_info[key]
    items.append({'year':year,'exam':exam,'subject':subj,'q':q,'doc':doc,'pno':pno,'clip':clip,'source_file':p.name,'source_url':url,'referer':ref,'number_rect':qrect})
    print('ITEM',year,exam,subj,q,'page',pno+1,'qrect',tuple(round(x,1) for x in qrect),'clip',tuple(round(x,1) for x in clip))

# A4 portrait, two columns, fixed source-column scale, top aligned.
out=fitz.open(); A4=fitz.paper_rect('a4')
margin=29; gutter=17; top=27; bottom=A4.height-28
colw=(A4.width-2*margin-gutter)/2
for i in range(0,len(items),2):
    dp=out.new_page(width=A4.width,height=A4.height)
    for j in range(2):
        if i+j>=len(items): break
        it=items[i+j]; clip=it['clip']
        x=margin+j*(colw+gutter)
        scale=colw/clip.width
        ph=clip.height*scale
        if top+ph>bottom:
            raise RuntimeError(f'Problem too tall at fixed scale: {it["year"]} {it["exam"]} {it["q"]}, height={ph}')
        dest=fitz.Rect(x,top,x+colw,top+ph)
        dp.show_pdf_page(dest,it['doc'],it['pno'],clip=clip,keep_proportion=True)

pdf_path=OUT/'평가원_미적분_고난도_공식원본_2017-2027_1차.pdf'
out.save(pdf_path,garbage=4,deflate=True)
out.close()

csv_path=OUT/'평가원_미적분_고난도_공식원본_2017-2027_1차_대응표.csv'
with open(csv_path,'w',newline='',encoding='utf-8-sig') as f:
    fields=['순번','학년도','시험','유형','문항','공식원본파일','원본PDF페이지','crop_x0','crop_y0','crop_x1','crop_y1','원본URL','게시물/배포처']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for n,it in enumerate(items,1):
        c=it['clip']; w.writerow({'순번':n,'학년도':it['year'],'시험':it['exam'],'유형':it['subject'],'문항':it['q'],'공식원본파일':it['source_file'],'원본PDF페이지':it['pno']+1,'crop_x0':round(c.x0,2),'crop_y0':round(c.y0,2),'crop_x1':round(c.x1,2),'crop_y1':round(c.y1,2),'원본URL':it['source_url'],'게시물/배포처':it['referer']})

# Raster preview/contact sheet for visual regression review.
check=fitz.open(pdf_path)
thumbs=[]
for pno,p in enumerate(check):
    pix=p.get_pixmap(matrix=fitz.Matrix(0.85,0.85),alpha=False)
    img=Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    img.thumbnail((420,595))
    canvas=Image.new('RGB',(440,630),'white'); canvas.paste(img,((440-img.width)//2,20))
    ImageDraw.Draw(canvas).text((10,605),f'page {pno+1}',fill='black')
    thumbs.append(canvas)
check.close()
cols=3; rows=(len(thumbs)+cols-1)//cols
sheet=Image.new('RGB',(cols*440,rows*630),(225,225,225))
for i,t in enumerate(thumbs): sheet.paste(t,((i%cols)*440,(i//cols)*630))
sheet.save(OUT/'평가원_미적분_공식원본_2017-2027_1차_검수.jpg',quality=88)

for d in docs.values(): d.close()
# Source PDFs were temporary runner files and are removed after creation.
shutil.rmtree(SRC,ignore_errors=True)
print('DONE',pdf_path,len(items),'items',len(items)+1>>1,'pages')
