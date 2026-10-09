import sys, json; sys.path.insert(0,'tools')
from PIL import Image
import downscale as d
from collections import deque

def comps_of(path, minpx=300):
    img=Image.open(path).convert('RGBA'); key=d.sample_key(img)
    k=d.remove_background(img,key,60); w,h=k.size; a=k.getchannel('A').load()
    seen=bytearray(w*h); out=[]
    for y in range(h):
        for x in range(w):
            if a[x,y]>110 and not seen[y*w+x]:
                q=deque([(x,y)]); seen[y*w+x]=1; xs=[x]; ys=[y]; n=0
                while q:
                    cx,cy=q.popleft(); n+=1; xs.append(cx); ys.append(cy)
                    for nx,ny in ((cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)):
                        if 0<=nx<w and 0<=ny<h and not seen[ny*w+nx] and a[nx,ny]>110:
                            seen[ny*w+nx]=1; q.append((nx,ny))
                out.append((n,min(xs),min(ys),max(xs),max(ys)))
    out=[c for c in out if c[0]>minpx]; out.sort(key=lambda c:c[1])
    return img,k,out

def merge_by_columns(cs, gap=40):
    groups=[]
    for c in cs:
        if groups and c[1]-groups[-1][3] < gap:
            g=groups[-1]; groups[-1]=(g[0]+c[0],min(g[1],c[1]),min(g[2],c[2]),max(g[3],c[3]),max(g[4],c[4]))
        else: groups.append(c)
    return groups

for sheet,names in [('nodes',['tree','rock','ore_copper','ore_iron','crystal_node']),('icons',['ic_wood','ic_stone','ic_copper','ic_iron','ic_crystal'])]:
    img,k,cs=comps_of(f'art-src/sheet_{sheet}.jpg')
    cs=merge_by_columns(cs)
    print(sheet,len(cs),cs)
    assert len(cs)==5
    for c,nm in zip(cs,names):
        pad=24
        img.crop((max(0,c[1]-pad),max(0,c[2]-pad),min(img.width,c[3]+pad+1),min(img.height,c[4]+pad+1))).save(f'art-src/{nm}.png')

# smith strip
img,k,cs=comps_of('art-src/sheet_smith.jpg',2000)
cs=merge_by_columns(cs,60); print('smith',len(cs),cs); assert len(cs)==3
top=min(c[2] for c in cs); bot=max(c[4] for c in cs); H=bot-top+1
FW=FH=26
strip=Image.new('RGBA',(FW*3,FH),(0,0,0,0))
frames=[]
for i,c in enumerate(cs):
    cx=(c[1]+c[3])//2
    win=k.crop((cx-H//2,top,cx-H//2+H,top+H))
    opaque=[p for p in d.pixels(win) if p[3]>110]
    mean=tuple(sum(p[j] for p in opaque)//len(opaque) for j in range(3))
    a=win.getchannel('A').point(lambda v:255 if v>110 else 0)
    rgb=Image.composite(win.convert('RGB'),Image.new('RGB',win.size,mean),a)
    small=rgb.resize((FW,FH),Image.BOX).convert('RGBA')
    sa=win.getchannel('A').resize((FW,FH),Image.BOX).point(lambda v:255 if v>=110 else 0)
    small.putalpha(sa); strip.alpha_composite(small,(i*FW,0))
from PIL import ImageEnhance
t=ImageEnhance.Color(strip.convert('RGB')).enhance(1.0); t=ImageEnhance.Brightness(t).enhance(1.0)
t=t.convert('RGBA'); t.putalpha(strip.getchannel('A'))
out=d.quantise(t,24)
import os; os.makedirs('assets/smith',exist_ok=True); out.save('assets/smith/smith.png'); print('saved smith',out.size)
