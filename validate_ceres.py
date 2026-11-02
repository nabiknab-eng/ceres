#!/usr/bin/env python3
"""Independent scientific identities, preservation, JS/Python pixels and MP4 checks."""
from __future__ import annotations
import argparse,hashlib,json,math,re,subprocess,tempfile
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
from PIL import Image
import imageio_ffmpeg
from build_ceres import aggregate
from export_mp4 import ROOT,ffmpeg_path,frame_fields,load_chunk,validate_settings
from render_core import load_spec,map_rgb,color_indices

def main():
 p=argparse.ArgumentParser();p.add_argument('--node',required=True);p.add_argument('--skip-asr-preservation',action='store_true',help='For standalone clones without the complete historical ASR snapshot');args=p.parse_args()
 m=json.loads((ROOT/'manifest.json').read_text());s=load_spec();report={}
 # NetCDF identity and fixed reference, independent of exported raster chunks.
 with Dataset(ROOT/'asr/original/raw/CERES_EBAF-TOA_Edition4.2.1_200003-202608.nc') as raw:
  balance=sum(sign*np.asarray(raw[key][:],dtype='float64') for key,sign in [('solar_mon',1),('toa_sw_all_mon',-1),('toa_lw_all_mon',-1),('toa_net_all_mon',-1)])
  monthly_residual=float(np.nanmax(np.abs(balance)))
  # Separately stored fluxes have limited significant-digit precision. Preserve the
  # source NET instead of silently replacing it by a difference of rounded fields.
  assert monthly_residual<.201
 report['source_monthly_net_identity_residual_W_m2']=monthly_residual
 with Dataset(ROOT/'data/ceres_anomalies.nc') as nc:
  errors={}
  for mode in m['modes']:
   g=nc[mode];delta=np.asarray(g['asr_anomaly'][:])-np.asarray(g['olr_anomaly'][:])-np.asarray(g['net_anomaly'][:]);errors[mode]=float(np.nanmax(np.abs(delta)));assert errors[mode]<=2*monthly_residual+1e-8
   for key in m['fields']:
    if mode=='annual':assert np.nanmax(np.abs(np.mean(np.asarray(g[key+'_anomaly'][:]),axis=0)))<1e-10
    for chunk in m['modes'][mode]['fields'][key]['chunks']:
     displayed=load_chunk(chunk);expected=np.asarray(g[key+'_anomaly'][chunk['start']:chunk['start']+chunk['frames']]).astype('float32');np.testing.assert_array_equal(displayed,expected)
  report['net_equals_asr_minus_olr_max_error']=errors
 # A constant physical albedo remains defined when six months have no sunlight.
 days=np.array([31,28,31,30,31,30,31,31,30,31,30,31],dtype=float)
 incoming=np.array([0]*6+[100,200,300,400,500,600],dtype=float)[:,None,None];reflected=incoming*.3
 np.testing.assert_allclose(aggregate(reflected,days,0,12,incoming),30,atol=1e-12)
 reflected[2]=np.nan;assert np.isnan(aggregate(reflected,days,0,12,incoming)).all()
 assert np.isnan(aggregate(np.zeros((12,1,1)),days,0,12,np.zeros((12,1,1)))).all()
 report['albedo_polar_night_and_missing_policy']='PASS'
 # Verify both preserved copies against the pre-edit lock.
 if args.skip_asr_preservation:
  report['asr_preservation_checked_in_this_run']=False
 else:
  lock=json.loads((ROOT/'asr_version_lock.json').read_text())['files_sha256']
  for root in [ROOT/'asr',ROOT.parent/'ceres_animace']:
   for name,digest in lock.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
  report['asr_preserved_files_per_copy']=len(lock)
 limits=sorted({float(info[k]) for info in m['fields'].values() for k in ['minimum','maximum','default']});cases=[]
 for L in limits:
  for t in np.linspace(-L,L,21):
   for v in [np.nextafter(t,-np.inf),t,np.nextafter(t,np.inf)]:cases.append(dict(value=float(v),limit=L))
  cases.extend([dict(value=None,limit=L),dict(value=-10*L,limit=L),dict(value=10*L,limit=L)])
 with tempfile.TemporaryDirectory() as tmp:
  tmp=Path(tmp);overlay=np.asarray(s['overlay']);assert set(np.unique(overlay[:,:,3])).issubset({0,255});(tmp/'overlay.rgba').write_bytes(overlay.tobytes());(tmp/'cases.json').write_text(json.dumps(cases))
  result=json.loads(subprocess.check_output([args.node,str(ROOT/'validate_render.js'),str(tmp/'overlay.rgba'),str(tmp/'cases.json')]))
  expected=[int(color_indices([np.nan if c['value'] is None else c['value']],c['limit'])[0]) for c in cases];assert expected==result['boundaries']
  for mode,modeinfo in m['modes'].items():
   for key,info in modeinfo['fields'].items():
    for chunk in info['chunks']:
     data=load_chunk(chunk)
     for j,field in enumerate(data):
      digest=hashlib.sha256(map_rgb(field,m['fields'][key]['default'],s).tobytes()).hexdigest();assert digest==result['hashes'][f'{mode}/{key}/{chunk["start"]+j}']
  report['js_python_identical_map_rasters']=len(result['hashes']);report['color_boundary_cases']=len(cases)
 videos=[]
 for video in sorted((ROOT/'exports').glob('*.mp4')):
  side=json.loads(video.with_suffix('.frames.json').read_text());settings=side['settings'];mode,start,end,selected,L,fps=validate_settings(settings,m);expected_frames=m['modes'][mode]['frames'][start:end+1]
  assert side['frame_count']==end-start+1==len(side['frames'])
  for i,(actual,expected) in enumerate(zip(side['frames'],expected_frames)):
   assert actual['video_frame']==i and actual['pts_seconds']==i/fps
   for k,v in expected.items():assert actual[k]==v
  reader=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24');meta=next(reader);assert tuple(meta['size'])==(1920,1080) and abs(meta['fps']-fps)<1e-8 and meta['codec']=='h264'
  cache={};count=0;worst_mae=0.;minimum_psnr=float('inf')
  for i,raw in enumerate(reader):
   frame=np.frombuffer(raw,dtype='uint8').reshape(1080,1920,3);fields=frame_fields(m,mode,start+i,selected,cache)
   for j,(field,limit,x) in enumerate(zip(fields,L,s['map_x'])):
    expected=map_rgb(field,limit,s);assert hashlib.sha256(expected.tobytes()).hexdigest()==side['frames'][i]['map_rgb_sha256'][j]
    actual=frame[s['map_y']:s['map_y']+s['map_height'],x:x+s['map_width']];difference=actual.astype(float)-expected;worst_mae=max(worst_mae,float(np.mean(np.abs(difference))));mse=float(np.mean(difference**2));minimum_psnr=min(minimum_psnr,10*math.log10(255**2/mse) if mse else 100)
   count+=1
  # yuv420p averages chroma over 2×2 pixels. Extremely saturated neighbouring
  # cells in the narrow-scale stress export therefore have a lower RGB PSNR.
  # Map hashes above check exact pre-compression colors independently.
  assert count==len(expected_frames) and worst_mae<8 and minimum_psnr>24
  if selected==['asr','net','temperature'] and L==[20,20,4]:assert minimum_psnr>30
  info=subprocess.run([ffmpeg_path(),'-hide_banner','-i',str(video),'-vf','showinfo','-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,check=True).stderr
  pts=[(int(a),float(b)) for a,b in re.findall(r'\bn:\s*(\d+)\s+pts:\s*\d+\s+pts_time:([\d.eE+-]+)',info)]
  assert len(pts)==count and all(i==j and abs(t-i/fps)<1e-4 for j,(i,t) in enumerate(pts))
  videos.append(dict(video=video.name,frames=count,fps=fps,all_months_and_pts_verified=True,min_map_psnr_db=minimum_psnr,max_map_mean_absolute_error=worst_mae,fields=selected,limits=L))
 report['videos']=videos;report['status']='PASS';(ROOT/'validation_media.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
