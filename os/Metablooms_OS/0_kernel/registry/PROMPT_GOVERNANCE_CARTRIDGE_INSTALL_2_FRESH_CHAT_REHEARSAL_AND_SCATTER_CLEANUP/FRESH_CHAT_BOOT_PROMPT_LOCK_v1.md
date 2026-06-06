# FRESH_CHAT_BOOT_PROMPT_LOCK_v1

Boot from the attached MetaBlooms OS full authority ZIP and checksum sidecar. Verify checksum first. Extract to `/mnt/data/Metablooms_OS`. Load `0_kernel/registry/BOOT_REQUIRED_GATES_v1.json`, run the boot-critical governance loader, anti-scatter validator, prompt-governance cartridge validator, and fresh-chat rehearsal gate. Treat any DENY as fail-closed. Render tracker, write receipt and handoff, and do not start feature work until these gates allow.
