# Governed install profile: Node ZIP Authority Repair v1

This profile is the promoted OS route for ZIP authority repair, boot archive replay proof, and stream rebuild stages.

Required packages are installed outside the OS root in a bounded `/mnt/data` workspace and must be pinned, lockfile-backed, resolver-tested, and task-smoke-tested before use.

Default chain:

`yauzl -> crc-32 -> yazl -> sha256sum -> yauzl CRC proof -> targeted boot extract -> boot executor smoke`

Do not embed `node_modules` in OS authority exports. Embed only this policy, scripts, receipts, and lockfile/hash evidence.

## Stage6F addition

`stream_export_directory.js` is the BTS-wrapped full-directory export route. It uses `yazl` to create a stream-built ZIP from a verified OS root, then `stream_crc_proof.js` uses `yauzl` + `crc-32` for full streamed CRC proof. This is the preferred full authority export backend after Stage6F; Python `zipfile` export remains a compatibility fallback only.
