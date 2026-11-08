"""Same projection pixels, palette, layout and selected quantities as offline HTML."""
from __future__ import annotations
import gzip,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent

def load_spec(root=ROOT):
 s=json.loads((root/'render_spec.json').read_text());s['lut']=np.frombuffer(gzip.decompress((root/'data/projection.bin.gz').read_bytes()),dtype='<i4').reshape(s['map_height'],s['map_width']);s['overlay']=Image.open(root/'viewer/coast.png').convert('RGBA');return s
def color_indices(values,limit):
 if not math.isfinite(limit) or limit<=0:raise ValueError('Scale must be finite and positive')
 a=np.asarray(values,dtype='float64');ci=np.full(a.shape,10,dtype=np.uint8);good=np.isfinite(a);neg=good&(a<0);pos=good&(a>0)
 ci[neg]=9-np.clip(np.ceil(-a[neg]/limit*10).astype(int)-1,0,9);ci[pos]=11+np.clip(np.ceil(a[pos]/limit*10).astype(int)-1,0,9);ci[~good]=21;return ci
def map_rgb(field,limit,s):
 palette=np.array(s['palette']+[s['missing']],dtype='uint8');ci=color_indices(np.asarray(field).ravel(),limit);lut=s['lut'];rgb=palette[ci[np.maximum(lut,0)]];rgb[lut<0]=255
 overlay=np.asarray(s['overlay']);opaque=overlay[:,:,3]==255;rgb[opaque]=overlay[:,:,:3][opaque];return rgb
def render_scene(fields,limits,selected,mode,meta,index,total,s,definitions,root=ROOT):
 im=Image.new('RGB',(1920,1080),'white');d=ImageDraw.Draw(im)
 def text(x,y,t,size=24,bold=False,align='left',color='#12232b'):
  font=ImageFont.truetype(str(root/'fonts'/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size);d.text((x,y),t,font=font,fill=color,anchor={'left':'ls','center':'ms','right':'rs'}[align])
 text(36,64,'CERES Evropa · radiační pole a povrchová teplota',32,True)
 text(1884,64,('Střed okna: ' if mode=='rolling' else 'Období: ')+meta['label'],23,False,'right')
 titles={'rolling':'12měsíční klouzavý průměr · krok 1 měsíc','annual':'Kalendářní roční průměr','fiveyear':'Pětiletý průměr ročních anomálií'}
 text(36,112,titles[mode]+'  |  Reference 2001–2025',22);d.line((36,148,1884,148),fill='#d8dfe2',width=1)
 text(36,192,' + '.join(definitions[k]['label'] for k in selected),23)
 for key,field,limit,x in zip(selected,fields,limits,s['map_x']):
  info=definitions[key];text(x,235,info['title'],23,True);text(x+s['map_width'],235,info['unit'],20,False,'right')
  im.paste(Image.fromarray(map_rgb(field,limit,s)),(x,s['map_y']))
  left=x+70;width=460;y=s['map_y']+s['map_height']+24
  for j,c in enumerate(s['palette']):
   a=left+math.floor(j*width/21);b=left+math.floor((j+1)*width/21);d.rectangle((a,y,b-1,y+17),fill=tuple(c))
  n=f'{limit:g}'.replace('.',',');text(left,y+52,'−'+n+' '+info['unit'],21);text(left+width/2,y+52,'0',21,False,'center');text(left+width,y+52,'+'+n+' '+info['unit'],21,False,'right')
 text(36,870,'Okno: '+meta['window'],25,True);text(1884,870,f'Snímek {index+1} / {total}',22,False,'right')
 text(36,915,'Šedá: chybějící data nebo neúplná reference. Bílá: přesná nula. Mimo rozsah: krajní barva.',20)
 text(36,953,'Albedo a oblačnost: rozdíl v procentních bodech (p. b.), nikoli relativní změna v procentech.',20)
 d.line((36,983,1884,983),fill='#d8dfe2',width=1);text(36,1032,'CERES EBAF Ed4.2.1 × Berkeley Earth High-Resolution TAVG · 1° × 1° · Lambert LAEA (EPSG:3035) · hranice: Natural Earth',19)
 return im
