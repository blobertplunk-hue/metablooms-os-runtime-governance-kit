### GOVERNANCE HEADER
# purpose: Provide safe code patching helpers that prevent silent regex/string patch failures.
# mutation_scope: code files only, not registry state
# invariants_enforced: no_regex_only_structural_code_patching, inspect_target_code_before_patch, deterministic_insertion_point_required, post_write_verification_required, no_success_message_unless_post_write_verification_passes
# risk_level: mutation-safe
###

from pathlib import Path
from typing import Callable, Tuple

class PatchFailure(RuntimeError):
    pass

def read_text(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise PatchFailure(f"Target file missing: {p}")
    return p.read_text(encoding="utf-8", errors="ignore")

def write_text_verified(path: str | Path, new_text: str, required_markers: list[str]) -> None:
    p = Path(path)
    p.write_text(new_text, encoding="utf-8")
    reread = p.read_text(encoding="utf-8", errors="ignore")
    missing = [m for m in required_markers if m not in reread]
    if missing:
        raise PatchFailure(f"Post-write verification failed; missing markers: {missing}")

def insert_before_first_line(
    path: str | Path,
    predicate: Callable[[str], bool],
    insertion: str,
    required_marker: str,
) -> Tuple[int, int]:
    """
    Deterministic line-aware insertion.
    Fails closed if zero or multiple structural targets are found.
    Returns (line_index, target_count).
    """
    text = read_text(path)
    lines = text.splitlines()
    matches = [idx for idx, line in enumerate(lines) if predicate(line)]
    if len(matches) != 1:
        raise PatchFailure(f"Expected exactly one insertion target; found {len(matches)}")
    idx = matches[0]
    if required_marker in text:
        return idx, 1
    new_lines = lines[:idx] + [insertion.rstrip("\n")] + lines[idx:]
    write_text_verified(path, "\n".join(new_lines) + "\n", [required_marker])
    return idx, 1

def assert_marker(path: str | Path, marker: str) -> None:
    text = read_text(path)
    if marker not in text:
        raise PatchFailure(f"Required marker not found: {marker}")
