"""Trusted deterministic fixture generator. Pillow only, no downloaded images."""
from pathlib import Path
import json,random
from PIL import Image,ImageDraw

def generate(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    def canvas():return Image.new('RGB',(256,256),'white')
    im=canvas();ImageDraw.Draw(im).line((128,15,128,240),fill='black',width=3);im.save(root/'strong_edge.png')
    im=canvas();ImageDraw.Draw(im).arc((40,35,220,220),10,280,fill='black',width=4);im.save(root/'curved_contour.png')
    rng=random.Random(431);im=Image.new('RGB',(256,256));im.putdata([(v,v,v) for v in [rng.randrange(165,216) for _ in range(256*256)]])
    ImageDraw.Draw(im).line((110,10,110,246),fill=(105,105,105),width=3);im.save(root/'weak_noisy.png')
    im=canvas();draw=ImageDraw.Draw(im);draw.polygon([(35,160),(45,110),(90,105),(110,65),(175,65),(205,110),(230,125),(230,165),(35,165)],fill='#345068')
    draw.ellipse((55,145,95,185),fill='#17232c');draw.ellipse((180,145,220,185),fill='#17232c');im.save(root/'body_mask.png')
    im=canvas();draw=ImageDraw.Draw(im)
    for cx in (70,185):draw.ellipse((cx-27,145-27,cx+27,145+27),outline='black',width=4)
    im.save(root/'circle_wheels.png')
    im=canvas();draw=ImageDraw.Draw(im);draw.rectangle((30,30,100,150),outline='black',width=3);draw.line((10,220,240,10),fill='#888888',width=3);im.save(root/'false_positive.png')
    (root/'expected.json').write_text(json.dumps({'size':[256,256],'strong_edge_x':128,'wheel_centers':[[70,145],[185,145]],'wheel_radius':27,
        'semantics':'Analytical fixtures, no claim of semantic vehicle understanding'},indent=2)+'\n',encoding='utf-8')
    return root

if __name__=='__main__':
    import sys
    generate(sys.argv[1])
