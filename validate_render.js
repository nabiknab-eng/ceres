/* Numeric validation only; no browser automation. */
const fs=require('fs'),zlib=require('zlib'),crypto=require('crypto'),path=require('path');
const root=__dirname,M=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'))),S=JSON.parse(fs.readFileSync(path.join(root,'render_spec.json')));
require('./viewer/color_logic.js');
const lutBytes=zlib.gunzipSync(fs.readFileSync(path.join(root,'data/projection.bin.gz'))),lut=new Int32Array(lutBytes.buffer,lutBytes.byteOffset,lutBytes.byteLength/4),overlay=fs.readFileSync(process.argv[2]);
const colors=S.palette.concat([S.missing]),rgba32=new Uint32Array(colors.map(c=>(255<<24)|(c[2]<<16)|(c[1]<<8)|c[0]));
const hashes={};
for(const [mode,m] of Object.entries(M.modes))for(const [key,info] of Object.entries(m.fields))for(const chunk of info.chunks){
 let decoded;global.CeresData={register:(id,b64)=>{if(id!==chunk.id)throw Error('Wrong chunk');decoded=zlib.gunzipSync(Buffer.from(b64,'base64'));}};
 require(path.join(root,chunk.script));
 if(crypto.createHash('sha256').update(decoded).digest('hex')!==chunk.sha256)throw Error('Chunk integrity failure');
 const values=new Float32Array(decoded.buffer,decoded.byteOffset,decoded.byteLength/4);
 for(let j=0;j<chunk.frames;j++){
  const field=values.subarray(j*64800,(j+1)*64800),pixels=AtlasColor.rasterRGBA(field,M.fields[key].default,lut,rgba32),rgb=Buffer.alloc(lut.length*3);
  for(let i=0;i<lut.length;i++){const from=overlay[i*4+3]===255?overlay:pixels;rgb[i*3]=from[i*4];rgb[i*3+1]=from[i*4+1];rgb[i*3+2]=from[i*4+2];}
  hashes[`${mode}/${key}/${chunk.start+j}`]=crypto.createHash('sha256').update(rgb).digest('hex');
 }
}
const cases=JSON.parse(fs.readFileSync(process.argv[3]));const boundaries=cases.map(c=>AtlasColor.index(c.value===null?NaN:c.value,c.limit));
process.stdout.write(JSON.stringify({hashes,boundaries}));
