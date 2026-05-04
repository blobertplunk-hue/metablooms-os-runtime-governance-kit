'use strict';
const fs = require('fs');
const crypto = require('crypto');
const yauzl = require('yauzl');
const CRC32 = require('crc-32');
const zipPath = process.argv[2];
if (!zipPath) { console.error('usage: node stream_crc_proof.js <zip>'); process.exit(2); }
function unsafeName(name) { return name.startsWith('/') || name.includes('..') || name.includes('\\') || /^[A-Za-z]:/.test(name) || name.includes('\0'); }
function sha256File(file) { return new Promise((resolve, reject) => { const h = crypto.createHash('sha256'); fs.createReadStream(file).on('data', d => h.update(d)).on('error', reject).on('end', () => resolve(h.digest('hex'))); }); }
function openZip(file) { return new Promise((resolve, reject) => yauzl.open(file, {lazyEntries: true, decodeStrings: true, validateEntrySizes: true}, (err, z) => err ? reject(err) : resolve(z))); }
function readStream(zip, entry) { return new Promise((resolve, reject) => zip.openReadStream(entry, (err, stream) => err ? reject(err) : resolve(stream))); }
(async () => {
  const start = Date.now();
  const zip = await openZip(zipPath);
  const proof = {zip: zipPath, sha256: await sha256File(zipPath), entries: 0, files: 0, directories: 0, bytes: 0, unsafe_paths: [], duplicates: [], crc_failures: [], stream_errors: [], verdict: 'RUNNING'};
  const seen = new Set();
  await new Promise((resolve, reject) => {
    zip.on('entry', async (entry) => {
      zip.pause && zip.pause();
      try {
        proof.entries++;
        const name = entry.fileName;
        if (unsafeName(name)) proof.unsafe_paths.push(name);
        if (seen.has(name)) proof.duplicates.push(name);
        seen.add(name);
        if (/\/$/.test(name)) {
          proof.directories++;
        } else {
          proof.files++;
          let crc = 0;
          let size = 0;
          const s = await readStream(zip, entry);
          await new Promise((res, rej) => {
            s.on('data', chunk => { crc = CRC32.buf(chunk, crc); size += chunk.length; });
            s.on('error', rej);
            s.on('end', res);
          });
          proof.bytes += size;
          const unsigned = crc >>> 0;
          if (unsigned !== entry.crc32) proof.crc_failures.push({name, expected: entry.crc32 >>> 0, actual: unsigned, size});
        }
        zip.readEntry();
      } catch (err) {
        proof.stream_errors.push(String(err && err.stack || err));
        zip.readEntry();
      }
    });
    zip.on('end', resolve);
    zip.on('error', reject);
    zip.readEntry();
  });
  proof.duration_ms = Date.now() - start;
  proof.verdict = (!proof.unsafe_paths.length && !proof.duplicates.length && !proof.crc_failures.length && !proof.stream_errors.length) ? 'PASS' : 'FAIL';
  console.log(JSON.stringify(proof, null, 2));
  if (proof.verdict !== 'PASS') process.exit(1);
})().catch(err => { console.error(JSON.stringify({verdict:'FAIL', error: String(err && err.stack || err)}, null, 2)); process.exit(1); });
