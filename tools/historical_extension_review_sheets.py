"""Expose every manual historical name interval in enlarged scan context."""

import json
import argparse
from PIL import Image, ImageDraw

from historical_extension import LABELS, OUT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows",action="store_true")
    parser.add_argument("--details",action="store_true")
    parser.add_argument("--corrected",action="store_true")
    args=parser.parse_args()
    baselines={"33r":(325,1380),"66r":(325,1405),"99r":(345,1460),
               "132r":(330,1440),"165r":(337,1420)}
    panels=[]
    row_panels=[]
    if args.details:
        crops=[("132r",11,590,790),("132r",12,600,800),("132r",11,320,520),
               ("132r",14,780,980),("132r",16,360,560),("132r",17,620,820),
               ("132r",18,380,580),("165r",8,720,920),("66r",17,720,920)]
        details=[]
        for folio,row,left,right in crops:
            with Image.open(OUT/f'folio-{folio}.jpg') as raw:
                image=raw.convert("RGB")
                image=image.resize((1000,round(image.height*1000/image.width)))
            first,last=baselines[folio]
            cy=first+(row-1)*(last-first)/17
            top=round(cy)-45
            panel=Image.new("RGB",(800,360),"white")
            panel.paste(image.crop((left,top,right,top+80)).resize((800,320)),(0,40))
            draw=ImageDraw.Draw(panel)
            draw.text((2,0),f'{folio} row {row}',fill="black")
            for x in range(left,right,10):
                sx=(x-left)*4
                draw.text((sx,20),str(x),fill="blue")
                draw.line((sx,40,sx,360),fill=(100,180,210))
            details.append(panel)
        for start in range(0,len(details),3):
            sheet=Image.new("RGB",(800,1080),"white")
            for i,panel in enumerate(details[start:start+3]):
                sheet.paste(panel,(0,i*360))
            sheet.save(OUT/f'edge-detail-{start//3+1}.jpg')
        return
    wanted={"33r":[18],"66r":[5,11,12,15,17],"99r":[3,10],"132r":[11,12,14,16,17,18],"165r":[8]}
    labels=json.loads(LABELS.read_text())
    if args.corrected:
        from historical_extension_final_review import corrected_labels,CORRECTIONS
        labels=corrected_labels(labels,json.loads(CORRECTIONS.read_text()))
    for page in labels["pages"]:
        with Image.open(OUT/f'folio-{page["folio"]}.jpg') as raw:
            image=raw.convert("RGB")
            image=image.resize((1000,round(image.height*1000/image.width)))
        first,last=baselines[page["folio"]]
        if args.rows:
            for row in wanted[page["folio"]]:
                cy=first+(row-1)*(last-first)/17
                y0=round(cy)-45
                panel=Image.new("RGB",(1220,210),"white")
                panel.paste(image.crop((300,y0,910,y0+85)).resize((1220,170)),(0,40))
                draw=ImageDraw.Draw(panel)
                draw.text((2,0),f'{page["folio"]} physical row {row}',fill="black")
                for x in range(300,910,10):
                    sx=(x-300)*2
                    draw.line((sx,40,sx,210),fill=(100,180,210))
                    if x%20==0:
                        draw.text((sx+1,20),str(x),fill="blue")
                row_panels.append(panel)
            continue
        for verse,ordinal,word,row,left,right in page["names"]:
            cy=first+(row-1)*(last-first)/17
            x0=round((left+right)/2)-60
            y0=round(cy)-45
            crop=image.crop((x0,y0,x0+120,y0+80)).resize((360,240))
            panel=Image.new("RGB",(360,270),"white")
            panel.paste(crop,(0,30))
            draw=ImageDraw.Draw(panel)
            draw.text((3,3),f'{page["folio"]} {verse} #{ordinal} row{row} x{left}-{right}',fill="black")
            for x in (left,right):
                sx=(x-x0)*3
                draw.line((sx,30,sx,270),fill=(0,100,230),width=2)
            panels.append(panel)
    if args.rows:
        for start in range(0,len(row_panels),4):
            sheet=Image.new("RGB",(1220,840),"white")
            for i,panel in enumerate(row_panels[start:start+4]):
                sheet.paste(panel,(0,i*210))
            sheet.save(OUT/f'row-context-{start//4+1}.jpg')
        print("Saved full-width row contexts")
        return
    for start in range(0,len(panels),12):
        sheet=Image.new("RGB",(1080,1080),"white")
        for index,panel in enumerate(panels[start:start+12]):
            sheet.paste(panel,((index%3)*360,(index//3)*270))
        prefix="corrected-name-contact" if args.corrected else "name-contact"
        sheet.save(OUT/f'{prefix}-{start//12+1}.jpg')
    print("Saved",len(panels),"name contexts on",(len(panels)+11)//12,"sheets")


if __name__=="__main__":
    main()
