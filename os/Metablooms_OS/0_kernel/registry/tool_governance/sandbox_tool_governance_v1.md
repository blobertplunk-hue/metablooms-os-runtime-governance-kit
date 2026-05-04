# Sandbox Tool Governance v1

## Purpose
Prevent useful sandbox tools from being ignored. Route work by capability, not model habit.

## Invariant
Before claiming a task cannot be done, probe the sandbox tool surface and route through the best available safe capability.

## Routing loop
1. Classify task capability need.
2. Check artifact-specific constraints first.
3. Consult `sandbox_tool_capability_registry_v1.json`.
4. Probe selected tool when capability is uncertain.
5. Execute smallest safe validation or transformation.
6. Write receipt with command, path, result, and artifact hash where applicable.

## Prohibitions
- Do not use regex for structural parsing of JSON, XML, HTML, DOCX, PPTX, or manifests when a parser/schema tool is available.
- Do not use LibreOffice for spreadsheets unless explicitly requested; use spreadsheet-specific libraries.
- Do not claim a tool is unavailable without a direct probe.
- Do not route by familiarity when a better specialized tool is available.

## Immediate integration
This file and the registry should be loaded during MetaBlooms BOOT before planning, audit, promotion, export, or repair stages.
