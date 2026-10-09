import sys; sys.path.insert(0,'tools')
from PIL import Image
import downscale as d
exec(open('tools/split_sheet_smith_nodes.py').read().split('for sheet,names in')[0])

def convert(sheet, names, outdir, target, mode, colours, gap=40, minpx=300, bright=None, sat=None, purge=False):
    img,k,cs=comps_of(f'art-src/sheet_{sheet}.jpg',minpx)
    if purge:
        px=k.load()
        for y in range(k.height):
            for x in range(k.width):
                r,g,b,a=px[x,y]
                if a and r-g>28 and b-g>28: px[x,y]=(0,0,0,0)
    cs=merge_by_columns(cs,gap); print(sheet,len(cs)); assert len(cs)==len(names),(len(cs),cs)
    dims=[(c[3]-c[1]+1,c[4]-c[2]+1) for c in cs]
    ref = max(h for w,h in dims) if mode=='h' else max(max(w,h) for w,h in dims)
    f=target/ref
    for c,nm in zip(cs,names):
        win=k.crop((c[1],c[2],c[3]+1,c[4]+1))
        w,h=win.size; nw,nh=max(1,round(w*f)),max(1,round(h*f))
        opaque=[p for p in d.pixels(win) if p[3]>110]
        mean=tuple(sum(p[j] for p in opaque)//len(opaque) for j in range(3))
        a=win.getchannel('A').point(lambda v:255 if v>110 else 0)
        rgb=Image.composite(win.convert('RGB'),Image.new('RGB',win.size,mean),a)
        small=rgb.resize((nw,nh),Image.BOX).convert('RGBA')
        small.putalpha(win.getchannel('A').resize((nw,nh),Image.BOX).point(lambda v:255 if v>=110 else 0))
        from PIL import ImageEnhance
        t=small.convert('RGB')
        if sat: t=ImageEnhance.Color(t).enhance(sat)
        if bright: t=ImageEnhance.Brightness(t).enhance(bright)
        t=t.convert('RGBA'); t.putalpha(small.getchannel('A'))
        out=d.quantise(t,colours); out.save(f'assets/{outdir}/{nm}.png'); print(nm,out.size)

convert('trees',['tree','tree_pine','tree_birch','tree_autumn'],'resources',38,'h',24,gap=8)
convert('rocks',['rock','rock_moss','rock_pair','rock_tall'],'resources',20,'m',16,sat=1.1,purge=True)
convert('plants',['grass_s','grass_tall','grass_daisy','grass_violet','grass_mush','fern'],'resources',14,'h',14,gap=30,minpx=150)
