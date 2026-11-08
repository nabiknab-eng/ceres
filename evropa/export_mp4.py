#!/usr/bin/env python3
"""Export three synchronized CERES Evropa maps using the exact offline viewer data."""
from __future__ import annotations
import argparse,base64,gzip,hashlib,json,math,os,platform,shutil,subprocess,tempfile
from pathlib import Path
import numpy as np
from render_core import ROOT,load_spec,map_rgb,render_scene

def ffmpeg_path():
 if os.environ.get('FFMPEG_BINARY'):return os.environ['FFMPEG_BINARY']
 if platform.system()=='Darwin' and platform.machine()=='arm64' and (ROOT/'bin/ffmpeg-macos-arm64').exists():return str(ROOT/'bin/ffmpeg-macos-arm64')
 if shutil.which('ffmpeg'):return shutil.which('ffmpeg')
 import imageio_ffmpeg
 return imageio_ffmpeg.get_ffmpeg_exe()
def validate_settings(settings,manifest):
 if settings.get('schema')!=2 or settings.get('region')!=manifest['region']['id']:
  raise ValueError('Použijte JSON z webu CERES Evropa.')
 mode=settings.get('mode','rolling');selected=settings.get('fields',[]);limits=settings.get('limits',[])
 if mode not in manifest['modes']:raise ValueError('Neznámý časový režim.')
 if len(selected)!=3 or selected[2]!='temperature' or any(k not in manifest['fields'] or k=='temperature' for k in selected[:2]):raise ValueError('Neplatný výběr tří veličin.')
 if len(limits)!=3:raise ValueError('Chybí tři meze barevných škál.')
 limits=list(map(float,limits))
 for key,L in zip(selected,limits):
  info=manifest['fields'][key]
  if not math.isfinite(L) or not info['minimum']<=L<=info['maximum'] or abs(L/info['step']-round(L/info['step']))>1e-7:raise ValueError('Neplatná škála '+key)
 n=len(manifest['modes'][mode]['frames']);start=settings.get('start',0);end=settings.get('end',n-1);fps=float(settings.get('fps',6))
 if isinstance(start,bool) or isinstance(end,bool) or not isinstance(start,int) or not isinstance(end,int) or not 0<=start<=end<n:raise ValueError('Neplatný interval snímků.')
 if not math.isfinite(fps) or not .25<=fps<=60:raise ValueError('Rychlost musí být 0,25 až 60 snímků/s.')
 if settings.get('reference')!='2001-2025':raise ValueError('Reference musí být 2001–2025.')
 return mode,start,end,selected,limits,fps
def load_chunk(chunk,grid,root=ROOT):
 source=(root/chunk['script']).read_text();prefix='CeresData.register('+json.dumps(chunk['id'])+','
 if not source.startswith(prefix) or not source.endswith(');\n'):raise ValueError('Neplatný lokální datový blok.')
 raw=gzip.decompress(base64.b64decode(json.loads(source[len(prefix):-3]),validate=True))
 if hashlib.sha256(raw).hexdigest()!=chunk['sha256']:raise ValueError('Nesouhlasí kontrolní součet '+chunk['id'])
 return np.frombuffer(raw,dtype='<f4').reshape(chunk['frames'],grid['lat'],grid['lon'])
def frame_fields(manifest,mode,index,selected,cache):
 fields=[]
 for key in selected:
  chunk=next(c for c in manifest['modes'][mode]['fields'][key]['chunks'] if c['start']<=index<c['start']+c['frames'])
  if chunk['id'] not in cache:
   cache[chunk['id']]=load_chunk(chunk,manifest['grid'])
   while len(cache)>9:del cache[next(iter(cache))]
  fields.append(cache[chunk['id']][index-chunk['start']])
 return fields
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--settings',type=Path,default=ROOT/'export_settings.json');p.add_argument('--output',type=Path);p.add_argument('--preview',type=Path);p.add_argument('--frame',type=int);p.add_argument('--crf',type=int,default=16);args=p.parse_args()
 settings=json.loads(args.settings.read_text());manifest=json.loads((ROOT/'manifest.json').read_text());mode,start,end,selected,limits,fps=validate_settings(settings,manifest);s=load_spec();m=manifest['modes'][mode]
 if args.frame is not None:
  if not 0<=args.frame<len(m['frames']):raise ValueError('Snímek mimo dostupné období.')
  start=end=args.frame
 cache={};records=[]
 def generate():
  for i in range(start,end+1):
   fields=frame_fields(manifest,mode,i,selected,cache)
   hashes=[hashlib.sha256(map_rgb(f,L,s).tobytes()).hexdigest() for f,L in zip(fields,limits)]
   records.append(dict(video_frame=i-start,pts_seconds=(i-start)/fps,map_rgb_sha256=hashes,**m['frames'][i]))
   yield i,render_scene(fields,limits,selected,mode,m['frames'][i],i,len(m['frames']),s,manifest['fields'])
 if args.preview:
  args.preview.parent.mkdir(parents=True,exist_ok=True);_,im=next(generate());im.save(args.preview);return
 output=(args.output or ROOT/'exports'/f'ceres_evropa_{mode}_{start:03d}-{end:03d}_{fps:g}fps.mp4').resolve();output.parent.mkdir(parents=True,exist_ok=True)
 if output.exists():raise FileExistsError('Výstup již existuje; zvolte jiné jméno: '+str(output))
 if not 0<=args.crf<=40:raise ValueError('CRF musí být 0 až 40.')
 cmd=[ffmpeg_path(),'-hide_banner','-loglevel','warning','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf',str(args.crf),'-pix_fmt','yuv420p','-movflags','+faststart','-metadata',f'comment=CERES Evropa | {mode} | reference 2001-2025 | adjacent frame manifest',str(output)]
 with tempfile.TemporaryFile() as log:
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
  try:
   for i,im in generate():
    proc.stdin.write(im.tobytes())
    if i==start or (i-start+1)%12==0 or i==end:print(f'Export {i-start+1}/{end-start+1}: {m["frames"][i]["label"]}',flush=True)
   proc.stdin.close();code=proc.wait()
  except BaseException:proc.kill();proc.wait();raise
  if code:log.seek(0);raise RuntimeError(log.read().decode(errors='replace'))
 output.with_suffix('.frames.json').write_text(json.dumps(dict(schema=2,video=output.name,codec='H.264',width=1920,height=1080,fps=fps,frame_count=len(records),settings=settings,frames=records,source_sha256=manifest['source_sha256'],rendering='Same float32 fields, projection LUT, palette and opaque coast/boundary pixels as HTML; H.264 compression is lossy.'),ensure_ascii=False,indent=2))
 print('HOTOVO:',output,flush=True)
if __name__=='__main__':main()
