'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const yauzl = require('yauzl');
const yazl = require('yazl');

const srcZip = process.argv[2];
const outZip = process.argv[3];
const osRoot = process.argv[4];
const overlayManifestPath = process.argv[5];
if (!srcZip || !outZip || !osRoot || !overlayManifestPath) {
  console.error('usage: node stream_rebuild_authority.js <source.zip> <out.zip> <osRoot> <overlayManifest.json>');
  process.exit(2);
}

function unsafeName(name) {
  return name.startsWith('/') || name.includes('..') || name.includes('\\') || /^[A-Za-z]:/.test(name) || name.includes('\0');
}
function sha256File(file) {
  return new Promise((resolve, reject) => {
    const h = crypto.createHash('sha256');
    fs.createReadStream(file).on('data', d => h.update(d)).on('error', reject).on('end', () => resolve(h.digest('hex')));
  });
}
function openZip(file) {
  return new Promise((resolve, reject) => yauzl.open(file, {lazyEntries: true, decodeStrings: true, validateEntrySizes: true, autoClose: false}, (err, z) => err ? reject(err) : resolve(z)));
}
function getReadStream(zip, entry) {
  return new Promise((resolve, reject) => zip.openReadStream(entry, (err, stream) => err ? reject(err) : resolve(stream)));
}
function stat(file) { return fs.promises.stat(file); }

(async () => {
  const overlay = JSON.parse(fs.readFileSync(overlayManifestPath, 'utf8'));
  const overlayFiles = overlay.files || [];
  const overlayNames = new Set(overlayFiles.map(f => f.archive_path));
  const zipOut = new yazl.ZipFile();
  const output = fs.createWriteStream(outZip);
  const summary = {
    source_zip: srcZip,
    output_zip: outZip,
    os_root: osRoot,
    overlay_manifest: overlayManifestPath,
    entries_read: 0,
    files_added_from_source: 0,
    dirs_added_from_source: 0,
    source_entries_replaced_by_overlay: 0,
    overlay_files_added: 0,
    unsafe_paths: [],
    duplicate_source_names: [],
    output_sha256: null,
    status: 'running'
  };
  const seen = new Set();
  zipOut.outputStream.pipe(output);
  const zip = await openZip(srcZip);
  await new Promise((resolve, reject) => {
    zip.on('entry', (entry) => {
      summary.entries_read++;
      const name = entry.fileName;
      if (unsafeName(name)) {
        summary.unsafe_paths.push(name);
        zip.close();
        reject(new Error('unsafe path: ' + name));
        return;
      }
      if (seen.has(name)) summary.duplicate_source_names.push(name);
      seen.add(name);
      if (overlayNames.has(name)) {
        summary.source_entries_replaced_by_overlay++;
        zip.readEntry();
        return;
      }
      const isDir = /\/$/.test(name);
      const mtime = entry.getLastModDate ? entry.getLastModDate() : new Date();
      const mode = (entry.externalFileAttributes >>> 16) || (isDir ? 0o40775 : 0o100664);
      if (isDir) {
        zipOut.addEmptyDirectory(name.replace(/\/$/, ''), {mtime, mode});
        summary.dirs_added_from_source++;
        zip.readEntry();
      } else {
        zipOut.addReadStreamLazy(name, {mtime, mode}, cb => {
          getReadStream(zip, entry).then(stream => cb(null, stream)).catch(err => cb(err));
        });
        summary.files_added_from_source++;
        zip.readEntry();
      }
    });
    zip.on('end', resolve);
    zip.on('error', reject);
    zip.readEntry();
  });
  if (summary.duplicate_source_names.length) throw new Error('duplicate source names: ' + summary.duplicate_source_names.slice(0, 10).join(','));
  for (const item of overlayFiles) {
    if (unsafeName(item.archive_path)) throw new Error('unsafe overlay path: ' + item.archive_path);
    const abs = path.join(osRoot, item.local_path || item.archive_path.replace(/^Metablooms_OS\//, ""));
    const st = await stat(abs);
    if (!st.isFile()) throw new Error('overlay not file: ' + abs);
    zipOut.addFile(abs, item.archive_path, {mtime: st.mtime, mode: st.mode});
    summary.overlay_files_added++;
  }
  zipOut.end();
  await new Promise((resolve, reject) => output.on('close', resolve).on('error', reject));
  zip.close();
  summary.output_sha256 = await sha256File(outZip);
  summary.status = 'PASS';
  console.log(JSON.stringify(summary, null, 2));
})().catch(err => {
  console.error(JSON.stringify({status: 'FAIL', error: String(err && err.stack || err)}, null, 2));
  process.exit(1);
});
