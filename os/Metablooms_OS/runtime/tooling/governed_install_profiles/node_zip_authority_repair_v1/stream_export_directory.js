'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const yazl = require('yazl');
const sourceDir = process.argv[2];
const outZip = process.argv[3];
const rootName = process.argv[4] || path.basename(sourceDir);
if (!sourceDir || !outZip) { console.error('usage: node stream_export_directory.js <sourceDir> <out.zip> [rootName]'); process.exit(2); }
function unsafeName(name) { return name.startsWith('/') || name.includes('..') || name.includes('\\') || /^[A-Za-z]:/.test(name) || name.includes('\0'); }
function sha256File(file) { return new Promise((resolve, reject) => { const h = crypto.createHash('sha256'); fs.createReadStream(file).on('data', d => h.update(d)).on('error', reject).on('end', () => resolve(h.digest('hex'))); }); }
async function walk(dir) {
  const entries = await fs.promises.readdir(dir, {withFileTypes: true});
  let out = [];
  for (const ent of entries.sort((a,b)=>a.name.localeCompare(b.name))) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) out = out.concat(await walk(p));
    else if (ent.isFile()) out.push(p);
  }
  return out;
}
(async () => {
  const start = Date.now();
  const absSource = path.resolve(sourceDir);
  const files = await walk(absSource);
  const zip = new yazl.ZipFile();
  const output = fs.createWriteStream(outZip);
  const summary = {source_dir: absSource, output_zip: outZip, root_name: rootName, files_added: 0, bytes_added: 0, unsafe_paths: [], output_sha256: null, duration_ms: null, status: 'running'};
  zip.outputStream.pipe(output);
  for (const file of files) {
    const rel = path.relative(absSource, file).split(path.sep).join('/');
    const name = `${rootName}/${rel}`;
    if (unsafeName(name)) throw new Error('unsafe archive path: ' + name);
    const st = await fs.promises.stat(file);
    zip.addFile(file, name, {mtime: st.mtime, mode: st.mode});
    summary.files_added++;
    summary.bytes_added += st.size;
  }
  zip.end();
  await new Promise((resolve, reject) => output.on('close', resolve).on('error', reject));
  summary.output_sha256 = await sha256File(outZip);
  summary.duration_ms = Date.now() - start;
  summary.status = 'PASS';
  console.log(JSON.stringify(summary, null, 2));
})().catch(err => { console.error(JSON.stringify({status:'FAIL', error:String(err && err.stack || err)}, null, 2)); process.exit(1); });
