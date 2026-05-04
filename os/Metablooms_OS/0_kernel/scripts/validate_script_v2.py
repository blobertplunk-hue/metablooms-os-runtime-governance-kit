### GOVERNANCE HEADER
# purpose: Validate scripts against Script Quality Gate (SQG) v2 rules
# mutation_scope: none (read-only)
# invariants_enforced: governance_header_required, no_direct_registry_writes, risk_level_consistency, mutation_requires_engine, dry_run_and_receipt_presence_for_mutations
# risk_level: read-only
###

import sys, re, json

REQUIRED_HEADER_FIELDS = ["purpose", "mutation_scope", "invariants_enforced", "risk_level"]

FORBIDDEN_WRITE_PATTERNS = [
    r'open\([^)]*artifact_registry\.json[^)]*,\s*[\'"]w[\'"]',
    r'Path\([^)]*artifact_registry\.json[^)]*\)\.write_text',
    r'json\.dump\([^)]*artifact_registry',
]

DANGEROUS_CALLS = [
    r'\bos\.remove\(',
    r'\bos\.rmdir\(',
    r'\bshutil\.rmtree\(',
    r'\bsubprocess\.',
    r'\bos\.system\(',
    r'\beval\(',
    r'\bexec\(',
]

def read_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def extract_header(text):
    # Flexible: look for 'GOVERNANCE HEADER' and take next block until blank line
    m = re.search(r'GOVERNANCE HEADER', text, re.I)
    if not m:
        return None
    start = m.start()
    tail = text[start:]
    lines = tail.splitlines()
    block = []
    for ln in lines[1:]:
        if ln.strip() == "":
            break
        block.append(ln.strip())
    return "\n".join(block)

def parse_header_fields(header_text):
    fields = {}
    for ln in header_text.splitlines():
        m = re.match(r'#\s*([a-zA-Z_]+)\s*:\s*(.+)', ln)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields

def check_required_fields(fields):
    missing = [k for k in REQUIRED_HEADER_FIELDS if k not in fields]
    return missing

def detect_forbidden_writes(text):
    hits = []
    for pat in FORBIDDEN_WRITE_PATTERNS:
        if re.search(pat, text, re.I):
            hits.append(pat)
    return hits

def detect_dangerous_calls(text):
    hits = []
    for pat in DANGEROUS_CALLS:
        if re.search(pat, text):
            hits.append(pat)
    return hits

def risk_level(text, fields):
    declared = fields.get("risk_level","").lower()
    has_write = bool(detect_forbidden_writes(text))
    has_danger = bool(detect_dangerous_calls(text))
    if declared == "read-only" and (has_write or has_danger):
        return False, "read-only script contains write/dangerous operations"
    return True, ""

def mutation_requires_engine(text, fields):
    scope = fields.get("mutation_scope","").lower()
    if scope != "none":
        # must reference engine usage
        if not re.search(r'registry_mutation_engine', text):
            return False, "mutation script does not reference mutation engine"
    return True, ""

def dryrun_and_receipt(text, fields):
    scope = fields.get("mutation_scope","").lower()
    if scope != "none":
        if not re.search(r'--dry-run', text):
            return False, "mutation script missing --dry-run handling"
        if not re.search(r'receipt', text, re.I):
            return False, "mutation script missing receipt generation reference"
    return True, ""

def main():
    if len(sys.argv) < 2:
        print("usage: validate_script_v2.py <script.py>")
        sys.exit(1)

    path = sys.argv[1]
    text = read_file(path)

    header = extract_header(text)
    if not header:
        print("FAIL: missing governance header")
        sys.exit(1)

    fields = parse_header_fields(header)
    missing = check_required_fields(fields)
    if missing:
        print("FAIL: missing header fields:", missing)
        sys.exit(1)

    fw = detect_forbidden_writes(text)
    if fw:
        print("FAIL: forbidden registry write patterns detected:", fw)
        sys.exit(1)

    ok, msg = risk_level(text, fields)
    if not ok:
        print("FAIL:", msg)
        sys.exit(1)

    ok, msg = mutation_requires_engine(text, fields)
    if not ok:
        print("FAIL:", msg)
        sys.exit(1)

    ok, msg = dryrun_and_receipt(text, fields)
    if not ok:
        print("FAIL:", msg)
        sys.exit(1)

    print("PASS: script complies with SQG v2")
    sys.exit(0)

if __name__ == "__main__":
    main()
