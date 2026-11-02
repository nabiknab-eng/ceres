#!/usr/bin/env python3
"""Reproduce CERES: complete day-weighted windows, fixed 2001–2025 references."""
from __future__ import annotations
import base64, calendar, datetime as dt, gzip, hashlib, importlib.util, json, math
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
from PIL import Image, ImageDraw, ImageChops

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('asr_builder',ROOT/'asr/build_animation.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
old=base.old
FIELDS={
 'asr':dict(label='ASR',title='Anomálie ASR',unit='W/m²',nc_unit='W m-2',minimum=5,maximum=40,step=1,default=20),
 'olr':dict(label='OLR',title='Anomálie OLR',unit='W/m²',nc_unit='W m-2',minimum=5,maximum=40,step=1,default=20),
 'net':dict(label='NET / EEI',title='Anomálie NET / EEI',unit='W/m²',nc_unit='W m-2',minimum=5,maximum=40,step=1,default=20),
 'albedo':dict(label='Planetární albedo',title='Anomálie albeda',unit='p. b.',nc_unit='percentage_points',minimum=.5,maximum=10,step=.1,default=2),
 'cloud':dict(label='Cloud Fraction',title='Anomálie oblačnosti',unit='p. b.',nc_unit='percentage_points',minimum=1,maximum=30,step=.5,default=10),
 'temperature':dict(label='Povrchová teplota',title='Anomálie povrchové teploty',unit='°C',nc_unit='degree_Celsius',minimum=1,maximum=7,step=.2,default=4),
}

def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def read(ds,name,wanted,temperature=False):
 names=('latitude','longitude') if temperature else ('lat','lon')
 ki=base.keys(ds,temperature);ids=[ki.index(k) for k in wanted]
 assert [ki[i] for i in ids]==wanted
 v=ds[name];a=old.plain(v[ids,:,:]);a=np.transpose(a,[v.dimensions.index(n) for n in ('time',*names)])
 for attr,op in [('valid_min',np.less),('valid_max',np.greater)]:
  if hasattr(v,attr):a[op(a,float(v.getncattr(attr)))]=np.nan
 a[~np.isfinite(a)]=np.nan
 lat,lon=[old.plain(ds[n][:]) for n in names];iy=np.argsort(lat);lon=(lon+180)%360-180;ix=np.argsort(lon)
 np.testing.assert_allclose(lat[iy],old.LAT,atol=1e-9,rtol=0);np.testing.assert_allclose(lon[ix],old.LON,atol=1e-9,rtol=0)
 return a[:,iy,:][:,:,ix]

def weighted(a,days):
 w=np.asarray(days)[:,None,None]
 return np.sum(a*w,axis=0)/w.sum()

def aggregate(a,days,start,length,denominator=None):
 b=a[start:start+length];w=days[start:start+length]
 if denominator is None:return weighted(b,w)
 d=denominator[start:start+length];num=np.sum(b*w[:,None,None],axis=0);den=np.sum(d*w[:,None,None],axis=0)
 # Physical albedo of a period = reflected energy / incoming energy.
 # Monthly polar night contributes zero energy; it is never treated as a measured albedo of zero.
 return np.divide(num*100,den,out=np.full_like(num,np.nan),where=den>1e-8)

def write_chunk(mode,key,start,data):
 name=f'{mode}-{key}-{start//12:03d}';raw=np.asarray(data,dtype='<f4').tobytes(order='C')
 packed=gzip.compress(raw,compresslevel=6,mtime=0)
 (ROOT/'viewer'/f'{name}.js').write_text('CeresData.register('+json.dumps(name)+','+json.dumps(base64.b64encode(packed).decode())+');\n')
 return dict(id=name,script=f'viewer/{name}.js',start=start,frames=len(data),sha256=hashlib.sha256(raw).hexdigest())

def projection():
 w,h=600,300;s=math.sqrt(2)
 xx,yy=np.meshgrid((np.arange(w)+.5)/w*4*s-2*s,s-(np.arange(h)+.5)/h*2*s)
 inside=(xx/(2*s))**2+(yy/s)**2<=1;theta=np.arcsin(yy/s)
 phi=np.arcsin(np.clip((2*theta+np.sin(2*theta))/np.pi,-1,1));lam=np.pi*xx/(2*s*np.cos(theta))
 iy=np.clip(np.floor(np.rad2deg(phi)+90).astype(int),0,179);ix=np.clip(np.floor(np.rad2deg(lam)+180).astype(int),0,359)
 lut=np.where(inside,iy*360+ix,-1).astype('<i4')
 assert lut[h//2,0]%360==0 and lut[h//2,-1]%360==359
 # The top pixel centre is 88.7687° at this raster size, not the exact pole.
 assert lut[0,w//2]//360==178 and lut[-1,w//2]//360==1
 # Analytical boundary limits reach the poles exactly.
 assert np.isclose(np.arcsin((2*(np.pi/2)+np.sin(np.pi))/np.pi),np.pi/2)
 packed=gzip.compress(lut.tobytes(),mtime=0);(ROOT/'data/projection.bin.gz').write_bytes(packed)
 overlay=Image.new('RGBA',(w,h));draw=ImageDraw.Draw(overlay)
 for line in old.projected_coast():
  points=[((float(x)+2*s)/(4*s)*w-.5,(s-float(y))/(2*s)*h-.5) for x,y in line]
  draw.line(points,fill=(0,0,0,255),width=1)
 overlay.putalpha(ImageChops.multiply(overlay.getchannel('A'),Image.fromarray((inside*255).astype('uint8'))))
 ImageDraw.Draw(overlay).ellipse((0,0,w-1,h-1),outline=(0,0,0,255),width=1);overlay.save(ROOT/'viewer/coast.png')
 return dict(width=1920,height=1080,map_width=w,map_height=h,map_x=[36,660,1284],map_y=302,
  palette=old.PALETTE.tolist(),missing=[210,214,220],projection_sha256=hashlib.sha256(lut.tobytes()).hexdigest(),
  projection_gzip=base64.b64encode(packed).decode(),coast_png=base64.b64encode((ROOT/'viewer/coast.png').read_bytes()).decode())

def metadata(common,days):
 rolling=[]
 for i in range(len(common)-11):
  start=base.monthdate(common[i]);end=base.monthdate(base.nextmonth(common[i+11]));middle=start+(end-start)/2
  rolling.append(dict(index=i,label=middle.strftime('%d.%m.%Y %H:%M UTC'),center=middle.isoformat(),start=start.isoformat(),end_exclusive=end.isoformat(),window=f'{common[i][1]:02d}/{common[i][0]} – {common[i+11][1]:02d}/{common[i+11][0]}',days=int(days[i:i+12].sum())))
 def meta(start,end,index,label):
  a=base.monthdate((start,1));b=base.monthdate((end+1,1))
  return dict(index=index,label=label,window=f'01/{start} – 12/{end}',start=a.isoformat(),end_exclusive=b.isoformat(),center=(a+(b-a)/2).isoformat(),days=(b-a).days)
 return {'rolling':rolling,'annual':[meta(y,y,i,str(y)) for i,y in enumerate(range(2001,2026))],'fiveyear':[meta(y,y+4,i,f'{y}–{y+4}') for i,y in enumerate(range(2001,2026,5))]}

def main():
 paths={'toa':ROOT/'asr/original/raw'/old.CERES,'temperature':ROOT/'asr/original/raw'/old.BERKELEY}
 for path in paths.values():
  if not path.exists():raise FileNotFoundError('Chybí skutečný vstupní soubor: '+str(path))
 sources={k:Dataset(p) for k,p in paths.items()}
 common=sorted(set(base.keys(sources['toa']))&set(base.keys(sources['temperature'],True)))
 assert len(common)>=300 and all(base.nextmonth(a)==b for a,b in zip(common,common[1:]))
 for y in range(2001,2026):assert all((y,m) in common for m in range(1,13))
 days=np.array([calendar.monthrange(*k)[1] for k in common],dtype='float64');metas=metadata(common,days)
 source_hashes={k:base.sha(p) for k,p in paths.items()}
 modes={mode:{'frames':f,'fields':{}} for mode,f in metas.items()};report={'status':'PASS','source_sha256':source_hashes,'common_months':len(common),'rolling_frames':len(metas['rolling']),'first_window':metas['rolling'][0],'last_window':metas['rolling'][-1],'reference_period':'2001-2025','metrics':{}}
 report['dataset']='Existing CERES EBAF-TOA Ed4.2.1 only; no new downloads'
 nc=Dataset(ROOT/'data/ceres_anomalies.nc','w');nc.Conventions='CF-1.10';nc.reference_period='2001-2025'
 nc.reference_aggregation='Equal mean of 25 complete day-weighted calendar years; unchanged ASR/temperature reference.'
 nc.albedo_aggregation='100 * sum(reflected_SW * days) / sum(incoming_SW * days); reference is equal mean of 25 calendar-year ratios.'
 nc.missing_policy='Any missing monthly input or missing fixed reference propagates. No zero imputation.'
 nc.source_sha256=json.dumps(source_hashes);nc.createDimension('lat',180);nc.createDimension('lon',360);nc.createDimension('bounds',2)
 for name,values,units in [('lat',old.LAT,'degrees_north'),('lon',old.LON,'degrees_east')]:
  v=nc.createVariable(name,'f8',(name,));v[:]=values;v.units=units
 epoch=dt.datetime(1970,1,1,tzinfo=dt.timezone.utc)
 for mode,frames in metas.items():
  group=nc.createGroup(mode);group.createDimension('time',len(frames));v=group.createVariable('time','f8',('time',));v.units='days since 1970-01-01 00:00:00';v.calendar='proleptic_gregorian';v.bounds='time_bounds'
  v[:]=[(dt.datetime.fromisoformat(f['center'])-epoch).total_seconds()/86400 for f in frames]
  group.createVariable('time_bounds','f8',('time','bounds'))[:]=[[(dt.datetime.fromisoformat(f[k])-epoch).total_seconds()/86400 for k in ['start','end_exclusive']] for f in frames]
 legacy_ref=Dataset(ROOT/'asr/original/data/reference_fields_2001-2025.nc');legacy_ann=Dataset(ROOT/'asr/original/data/annual_anomalies_2001-2025.nc');legacy_five=Dataset(ROOT/'asr/original/data/five_year_anomalies_2001-2025.nc')
 for key,info in FIELDS.items():
  print('Build',key,flush=True);den=None;toa=sources['toa']
  if key=='asr':a=read(toa,'solar_mon',common)-read(toa,'toa_sw_all_mon',common)
  elif key=='olr':a=read(toa,'toa_lw_all_mon',common)
  elif key=='net':a=read(toa,'toa_net_all_mon',common)
  elif key=='albedo':a=read(toa,'toa_sw_all_mon',common);den=read(toa,'solar_mon',common)
  elif key=='cloud':a=read(toa,'cldarea_total_daynight_mon',common)
  elif key=='temperature':a=read(sources['temperature'],'temperature',common,True)
  else:raise ValueError('Unsupported field: '+key)
  ann=np.array([aggregate(a,days,common.index((y,1)),12,den) for y in range(2001,2026)])
  ref=np.mean(ann,axis=0)
  if key in ['asr','temperature']:
   original=old.plain(legacy_ref[key+'_reference'][:]);np.testing.assert_allclose(ref,original,atol=1e-10,rtol=0,equal_nan=True);ref=original
  ann=ann-ref;rolling=np.array([aggregate(a,days,i,12,den)-ref for i in range(len(metas['rolling']))]);five=np.array([np.mean(ann[i:i+5],axis=0) for i in range(0,25,5)])
  if key in ['asr','temperature']:
   np.testing.assert_allclose(ann,old.plain(legacy_ann[key+'_anomaly'][:]),atol=1e-10,rtol=0,equal_nan=True);np.testing.assert_allclose(five,old.plain(legacy_five[key+'_anomaly'][:]),atol=1e-10,rtol=0,equal_nan=True)
   with Dataset(ROOT/'asr/data/rolling_anomalies.nc') as previous:np.testing.assert_allclose(rolling,old.plain(previous[key+'_anomaly'][:len(rolling)]),atol=1e-10,rtol=0,equal_nan=True)
  for y in range(2001,2026):np.testing.assert_allclose(rolling[common.index((y,1))],ann[y-2001],atol=1e-10,rtol=0,equal_nan=True)
  scalar_error=0.
  for i in [0,1,9,60,120,240,len(rolling)-1]:
   for iy,ix in [(0,0),(179,359),(90,180),(100,120),(150,300)]:
    numerator=sum(float(a[j,iy,ix])*days[j] for j in range(i,i+12))
    divisor=sum((float(den[j,iy,ix]) if den is not None else 1)*days[j] for j in range(i,i+12))
    expected=numerator/divisor*(100 if den is not None else 1)-ref[iy,ix] if divisor>1e-8 else np.nan
    actual=rolling[i,iy,ix];assert np.isnan(expected)==np.isnan(actual)
    if np.isfinite(expected):scalar_error=max(scalar_error,abs(expected-actual))
  assert scalar_error<1e-10
  variable=nc.createVariable(key+'_reference','f8',('lat','lon'),zlib=True,fill_value=np.nan);variable[:]=ref;variable.units=info['nc_unit']
  stats={'scalar_max_error':scalar_error,'missing_reference_cells':int(np.isnan(ref).sum()),'max_display_float32_error':0,'legacy_values_unchanged':key in ['asr','temperature']}
  for mode,data in [('annual',ann),('fiveyear',five),('rolling',rolling)]:
   v=nc[mode].createVariable(key+'_anomaly','f8',('time','lat','lon'),zlib=True,complevel=5,fill_value=np.nan);v[:]=data;v.units=info['nc_unit'];v.coordinates='lat lon';v.cell_methods='time: mean (actual Gregorian day weights)' if key!='albedo' else 'time: sum (ratio of reflected to incoming energy)'
   maximum=float(np.nanmax(np.abs(data)));auto=max(info['minimum'],min(info['maximum'],math.ceil(maximum/info['step'])*info['step']));chunks=[write_chunk(mode,key,i,data[i:i+12]) for i in range(0,len(data),12)]
   modes[mode]['fields'][key]={'chunks':chunks,'max_abs':maximum,'auto_limit':round(auto,8)}
   finite=np.isfinite(data);err=float(np.max(np.abs(data.astype('float32').astype('float64')[finite]-data[finite])))
   stats['max_display_float32_error']=max(stats['max_display_float32_error'],err)
  report['metrics'][key]=stats
  del a,ann,rolling,five,den
 nc.close()
 for source in list(sources.values())+[legacy_ref,legacy_ann,legacy_five]:source.close()
 render=projection();dump(ROOT/'render_spec.json',render)
 payload=dict(schema=2,name='CERES',reference='2001–2025',grid={'lat':180,'lon':360},common_start=f'{common[0][0]}-{common[0][1]:02d}',common_end=f'{common[-1][0]}-{common[-1][1]:02d}',fields=FIELDS,modes=modes,render=render,source_sha256=source_hashes)
 dump(ROOT/'manifest.json',{k:v for k,v in payload.items() if k!='render'})
 (ROOT/'viewer/manifest.js').write_text('window.CERES_MANIFEST='+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';\n')
 report['projection']=old.projection_checks();report['all_modes_use_identical_common_windows']=True;report['albedo_polar_night_policy']='ratio of whole-window energy sums';dump(ROOT/'validation_computation.json',report)
 print('BUILD PASS',len(metas['rolling']),'rolling frames',flush=True)
if __name__=='__main__':main()
