from pathlib import Path
import re

p=Path('scripts/kice_inspect.py')
s=p.read_text(encoding='utf-8')
new=r'''def make_clip(page,qrect):
    w,h=page.rect.width,page.rect.height
    right=qrect.x0>w/2
    if right:
        x0,x1=0.505*w,0.965*w
    else:
        x0,x1=0.045*w,0.495*w
    y0=max(0.075*h,qrect.y0-8)

    # Build vertical content elements in this source column. Starting at the
    # question number, keep only the connected content cluster. This retains
    # boxes/graphs while stopping before the distant confirmation footer and
    # printed page number.
    elements=[]
    for b in page.get_text('blocks'):
        bx0,by0,bx1,by1,text,*_=b
        if bx1<x0 or bx0>x1 or by1<y0 or by0>0.915*h: continue
        t=' '.join(str(text).split())
        if any(k in t for k in FOOTER_WORDS): continue
        if by0>0.82*h and re.fullmatch(r'[\\d\\s/]+',t or ''): continue
        elements.append((by0,by1,'text'))
    for d in page.get_drawings():
        r=d.get('rect')
        if not r or r.x1<x0 or r.x0>x1 or r.y1<y0 or r.y0>0.89*h: continue
        if r.height>0.72*h: continue
        elements.append((r.y0,r.y1,'drawing'))
    try:
        for im in page.get_images(full=True):
            for r in page.get_image_rects(im[0]):
                if r.x1>=x0 and r.x0<=x1 and r.y1>=y0 and r.y0<0.89*h:
                    elements.append((r.y0,r.y1,'image'))
    except Exception:
        pass

    elements.sort(key=lambda e:(e[0],e[1]))
    end=max(qrect.y1,y0+12)
    gap_limit=max(105.0,0.105*h)
    used=False
    for ey0,ey1,kind in elements:
        if ey1<y0: continue
        if ey0>end+gap_limit and used:
            break
        if ey0<=end+gap_limit:
            end=max(end,ey1); used=True
    y1=min(0.89*h,end+24)
    if y1-y0<90:
        y1=min(0.70*h,y0+220)
    return fitz.Rect(x0,y0,x1,y1)
'''
pat=r'def make_clip\(page,qrect\):.*?return fitz\.Rect\(x0,y0,x1,y1\)\n'
s2,n=re.subn(pat,new,s,flags=re.S)
if n!=1:
    raise RuntimeError(f'Expected one make_clip replacement, got {n}')
exec(compile(s2,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
