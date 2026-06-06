#!/usr/bin/env python3
"""Sandbox-first browser/render capability resolver for MetaBlooms visual artifacts.

Bounded method order:
1. Playwright managed browser
2. System Chromium headless
3. Chromium under Xvfb
4. Other installed browser
5. wkhtmltoimage-equivalent
6. WeasyPrint PDF/PNG proxy
7. Static VPQ/accessibility checks
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "0_kernel/registry/browser_render_capability/BROWSER_RENDER_CAPABILITY_RESOLVER_POLICY_v1.json"
DEFAULT_TIMEOUT = 8

TRUE_BROWSER_METHODS = {"playwright_managed_browser", "system_chromium_headless", "xvfb_chromium", "firefox_or_other_installed_browser"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def now_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def run_cmd(cmd: List[str], timeout: int = DEFAULT_TIMEOUT, cwd: Optional[Path] = None) -> Dict[str, Any]:
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return {
            "command": cmd,
            "exit_code": proc.returncode,
            "timed_out": False,
            "duration_seconds": round(time.time() - start, 3),
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as e:
        return {
            "command": cmd,
            "exit_code": None,
            "timed_out": True,
            "duration_seconds": round(time.time() - start, 3),
            "stdout_tail": (e.stdout or "")[-2000:] if isinstance(e.stdout, str) else "",
            "stderr_tail": (e.stderr or "")[-4000:] if isinstance(e.stderr, str) else "",
        }
    except Exception as e:
        return {
            "command": cmd,
            "exit_code": None,
            "timed_out": False,
            "duration_seconds": round(time.time() - start, 3),
            "stdout_tail": "",
            "stderr_tail": f"{type(e).__name__}: {e}",
        }



def load_skip_cache_from_ledger(ledger_path: Optional[Path]) -> Dict[str, Any]:
    """Load known hard-fail methods from the reliability ledger.

    This prevents export-prep and visual-gate binding stages from repeatedly
    burning turn time on methods already classified as unavailable/hanging in
    the same sandbox substrate. Conditions-changing methods can be retried by
    omitting this flag or by supplying a fresh ledger.
    """
    if not ledger_path or not ledger_path.exists():
        return {}
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    cache: Dict[str, Any] = {}
    for row in data.get("method_results", []):
        mid = row.get("method_id")
        if not mid or row.get("success"):
            continue
        recommendation = row.get("retry_recommendation", "")
        failure_class = row.get("failure_class", "UNKNOWN")
        if recommendation in {"skip_same_stage_after_timeout", "retry_only_if_conditions_change"}:
            cache[mid] = {
                "failure_class": failure_class,
                "retry_recommendation": recommendation,
                "source_ledger": str(ledger_path),
            }
    return cache


def image_nonblank(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"exists": False, "nonblank": False, "reason": "missing"}
    try:
        from PIL import Image, ImageStat  # type: ignore
        with Image.open(path) as im:
            stat = ImageStat.Stat(im.convert("RGB"))
            extrema = im.convert("RGB").getextrema()
            varying = any(lo != hi for lo, hi in extrema)
            return {
                "exists": True,
                "nonblank": bool(varying and path.stat().st_size > 1000),
                "size_bytes": path.stat().st_size,
                "width": im.width,
                "height": im.height,
                "mean_rgb": [round(x, 2) for x in stat.mean],
                "extrema": extrema,
            }
    except Exception as e:
        return {"exists": True, "nonblank": path.stat().st_size > 1000, "size_bytes": path.stat().st_size, "reason": f"pil_unavailable_or_failed:{type(e).__name__}:{e}"}


def write_html_sample(path: Path) -> None:
    path.write_text("""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Render Probe</title><style>body{margin:0;font-family:system-ui;background:linear-gradient(135deg,#111827,#1d4ed8);color:white}.card{margin:40px auto;padding:28px;max-width:720px;border-radius:24px;background:rgba(255,255,255,.14);box-shadow:0 20px 60px rgba(0,0,0,.35)}button{font:inherit;padding:12px 18px;border-radius:14px;border:0}button:focus-visible{outline:4px solid #facc15}@media(max-width:640px){.card{margin:16px;padding:18px}}@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}</style></head><body><main class='card' data-vpq-binding='visual_presentation_quality_gate'><h1>Browser Render Probe</h1><p>Teacher-professional visual presentation quality evidence card.</p><button>Focusable control</button></main></body></html>""", encoding="utf-8")


def method_attempt(method_id: str, html: Path, out_dir: Path, timeout: int, hard_fail_cache: Dict[str, Any]) -> Dict[str, Any]:
    artifact_paths: List[str] = []
    base = {"method_id": method_id, "started_utc": now_stamp(), "success": False, "artifacts": artifact_paths, "failure_class": "NOT_RUN"}
    if hard_fail_cache.get(method_id):
        base.update({"skipped": True, "failure_class": "SKIPPED_PRIOR_SAME_STAGE_HARD_FAIL", "prior_failure": hard_fail_cache[method_id]})
        return base

    file_url = html.resolve().as_uri()
    if method_id == "playwright_managed_browser":
        if shutil.which("playwright") is None:
            base.update({"skipped": True, "failure_class": "PLAYWRIGHT_CLI_ABSENT"}); return base
        script = out_dir / "playwright_probe.py"
        png = out_dir / "playwright_probe.png"
        script.write_text(f"""from playwright.sync_api import sync_playwright\nwith sync_playwright() as p:\n    b=p.chromium.launch()\n    page=b.new_page(viewport={{'width':390,'height':844}})\n    page.goto({file_url!r})\n    page.screenshot(path={str(png)!r}, full_page=True)\n    b.close()\n""", encoding="utf-8")
        res = run_cmd([sys.executable, str(script)], timeout=timeout)
        check = image_nonblank(png)
        artifact_paths.extend([str(script), str(png)] if png.exists() else [str(script)])
        base.update({"command_result": res, "image_check": check})
        if res["exit_code"] == 0 and check.get("nonblank"):
            base.update({"success": True, "failure_class": "NONE"})
        else:
            fail = "PLAYWRIGHT_BROWSER_BUNDLE_ABSENT" if "Executable doesn't exist" in res.get("stderr_tail","") or "playwright install" in res.get("stderr_tail","") else ("PLAYWRIGHT_TIMEOUT" if res.get("timed_out") else "PLAYWRIGHT_RENDER_FAILED")
            base.update({"failure_class": fail})
        return base

    if method_id == "system_chromium_headless":
        chromium = shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")
        if not chromium:
            base.update({"skipped": True, "failure_class": "CHROMIUM_BINARY_ABSENT"}); return base
        png = out_dir / "chromium_headless.png"
        cmd = [chromium, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--disable-crash-reporter", "--disable-extensions", "--window-size=390,844", f"--screenshot={png}", file_url]
        res = run_cmd(cmd, timeout=timeout)
        check = image_nonblank(png)
        if png.exists(): artifact_paths.append(str(png))
        base.update({"command_result": res, "image_check": check})
        if res["exit_code"] == 0 and check.get("nonblank"):
            base.update({"success": True, "failure_class": "NONE"})
        else:
            fail = "CHROMIUM_SANDBOX_HANG" if res.get("timed_out") else "CHROMIUM_HEADLESS_FAILED"
            base.update({"failure_class": fail})
            if res.get("timed_out"):
                hard_fail_cache[method_id] = fail
        return base

    if method_id == "xvfb_chromium":
        xvfb = shutil.which("xvfb-run")
        chromium = shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")
        if not xvfb or not chromium:
            base.update({"skipped": True, "failure_class": "XVFB_OR_CHROMIUM_ABSENT"}); return base
        png = out_dir / "xvfb_chromium.png"
        cmd = [xvfb, "-a", chromium, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--disable-crash-reporter", "--disable-extensions", "--window-size=390,844", f"--screenshot={png}", file_url]
        res = run_cmd(cmd, timeout=timeout)
        check = image_nonblank(png)
        if png.exists(): artifact_paths.append(str(png))
        base.update({"command_result": res, "image_check": check})
        if res["exit_code"] == 0 and check.get("nonblank"):
            base.update({"success": True, "failure_class": "NONE"})
        else:
            fail = "XVFB_CHROMIUM_HANG" if res.get("timed_out") else "XVFB_CHROMIUM_FAILED"
            base.update({"failure_class": fail})
            if res.get("timed_out"):
                hard_fail_cache[method_id] = fail
        return base

    if method_id == "firefox_or_other_installed_browser":
        if not (shutil.which("firefox") or shutil.which("google-chrome") or shutil.which("chrome")):
            base.update({"skipped": True, "failure_class": "OTHER_BROWSER_ABSENT"}); return base
        base.update({"skipped": True, "failure_class": "OTHER_BROWSER_PRESENT_BUT_NO_SAFE_CAPTURE_ADAPTER"}); return base

    if method_id == "wkhtmltoimage_or_equivalent":
        wk = shutil.which("wkhtmltoimage")
        if not wk:
            base.update({"skipped": True, "failure_class": "WKHTMLTOIMAGE_ABSENT"}); return base
        png = out_dir / "wkhtmltoimage.png"
        res = run_cmd([wk, str(html), str(png)], timeout=timeout)
        check = image_nonblank(png)
        if png.exists(): artifact_paths.append(str(png))
        base.update({"command_result": res, "image_check": check})
        if res["exit_code"] == 0 and check.get("nonblank"):
            base.update({"success": True, "failure_class": "NONE"})
        else:
            base.update({"failure_class": "WKHTMLTOIMAGE_FAILED"})
        return base

    if method_id == "weasyprint_pdf_png_proxy":
        weasy = shutil.which("weasyprint")
        pdftoppm = shutil.which("pdftoppm")
        if not weasy or not pdftoppm:
            base.update({"skipped": True, "failure_class": "WEASYPRINT_OR_PDFTOPPM_ABSENT"}); return base
        pdf = out_dir / "weasyprint_proxy.pdf"
        png_prefix = out_dir / "weasyprint_proxy"
        res1 = run_cmd([weasy, str(html), str(pdf)], timeout=timeout)
        res2 = run_cmd([pdftoppm, "-png", "-singlefile", str(pdf), str(png_prefix)], timeout=timeout) if pdf.exists() else {"exit_code": None, "timed_out": False, "stderr_tail": "pdf_missing"}
        png = out_dir / "weasyprint_proxy.png"
        check = image_nonblank(png)
        for p in [pdf, png]:
            if p.exists(): artifact_paths.append(str(p))
        base.update({"command_result": {"weasyprint": res1, "pdftoppm": res2}, "image_check": check})
        if res1.get("exit_code") == 0 and res2.get("exit_code") == 0 and check.get("nonblank"):
            base.update({"success": True, "failure_class": "NONE"})
        elif res1.get("timed_out") and res2.get("exit_code") == 0 and check.get("nonblank"):
            # In the ChatGPT sandbox, WeasyPrint can leave the wrapper waiting even after
            # a valid PDF is flushed. Treat this as usable proxy evidence only when the
            # downstream PNG exists and passes the nonblank check; preserve the warning.
            base.update({"success": True, "failure_class": "NONE", "warning_class": "WEASYPRINT_PROCESS_TIMEOUT_WITH_VALID_PROXY_ARTIFACT"})
        else:
            base.update({"failure_class": "WEASYPRINT_PROXY_FAILED"})
        return base

    if method_id == "static_vpq_accessibility_checks":
        txt = html.read_text(encoding="utf-8", errors="replace")
        checks = {
            "viewport": "name='viewport'" in txt or 'name="viewport"' in txt,
            "focus_visible": ":focus-visible" in txt,
            "reduced_motion": "prefers-reduced-motion" in txt,
            "vpq_binding": "vpq" in txt.lower() or "visual presentation" in txt.lower(),
            "teacher_professional": "teacher" in txt.lower() or "professional" in txt.lower(),
        }
        base.update({"static_checks": checks})
        if all(checks.values()):
            base.update({"success": True, "failure_class": "NONE"})
        else:
            base.update({"failure_class": "STATIC_CHECK_FAILED"})
        return base

    base.update({"skipped": True, "failure_class": "UNKNOWN_METHOD"})
    return base


def decide(attempts: List[Dict[str, Any]], requested_proof_tier: str, artifact_type: str) -> Dict[str, str]:
    true_success = next((a for a in attempts if a.get("success") and a.get("method_id") in TRUE_BROWSER_METHODS), None)
    weasy_success = next((a for a in attempts if a.get("success") and a.get("method_id") == "weasyprint_pdf_png_proxy"), None)
    static_success = next((a for a in attempts if a.get("success") and a.get("method_id") == "static_vpq_accessibility_checks"), None)
    if true_success:
        return {"selected_method": true_success["method_id"], "decision": "ALLOW_BROWSER_SCREENSHOT", "honesty_label": "full_browser_replay"}
    if requested_proof_tier == "browser_screenshot_required":
        return {"selected_method": "none", "decision": "DENY_PRODUCTION_PROMOTION", "honesty_label": "blocked"}
    if weasy_success and requested_proof_tier in {"browser_screenshot_preferred", "render_proxy_allowed"}:
        return {"selected_method": "weasyprint_pdf_png_proxy", "decision": "ALLOW_RENDER_PROXY_WITH_LIMITATION", "honesty_label": "sandbox_render_proxy"}
    if static_success and requested_proof_tier == "static_only_allowed":
        return {"selected_method": "static_vpq_accessibility_checks", "decision": "ALLOW_STATIC_ONLY_WITH_LIMITATION", "honesty_label": "static_only_limited"}
    if static_success and artifact_type in {"visual_policy_spec", "preimplementation_review"}:
        return {"selected_method": "static_vpq_accessibility_checks", "decision": "ALLOW_STATIC_ONLY_WITH_LIMITATION", "honesty_label": "static_only_limited"}
    return {"selected_method": "none", "decision": "DENY_PRODUCTION_PROMOTION", "honesty_label": "blocked"}


def build_schema_attempts(attempts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    policy_map = {
        "playwright_managed_browser": "try_if_bundle_present",
        "system_chromium_headless": "try_if_binary_present",
        "xvfb_chromium": "try_if_binary_present",
        "firefox_or_other_installed_browser": "try_if_binary_present",
        "wkhtmltoimage_or_equivalent": "try_if_binary_present",
        "weasyprint_pdf_png_proxy": "try_if_binary_present",
        "static_vpq_accessibility_checks": "always_available_static",
    }
    return [{
        "method_id": a["method_id"],
        "priority": i + 1,
        "attempt_policy": policy_map.get(a["method_id"], "try_if_binary_present"),
        "success_criteria": ["bounded_timeout", "artifact_or_explicit_skip", "failure_class_recorded"],
        "failure_class_if_failed": a.get("failure_class", "UNKNOWN"),
    } for i, a in enumerate(attempts)]


def resolve(html: Path, out_dir: Path, requested_proof_tier: str, artifact_type: str, timeout: int, full_probe: bool = True, skip_known_hard_fails: bool = False, reliability_ledger: Optional[Path] = None) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    hard_fail_cache: Dict[str, Any] = load_skip_cache_from_ledger(reliability_ledger) if skip_known_hard_fails else {}
    method_ids = [
        "playwright_managed_browser",
        "system_chromium_headless",
        "xvfb_chromium",
        "firefox_or_other_installed_browser",
        "wkhtmltoimage_or_equivalent",
        "weasyprint_pdf_png_proxy",
        "static_vpq_accessibility_checks",
    ]
    attempts: List[Dict[str, Any]] = []
    for mid in method_ids:
        a = method_attempt(mid, html, out_dir, timeout, hard_fail_cache)
        attempts.append(a)
        # sandbox-first but bounded: keep probing all classes to maintain reliability ledger; caller can pass full_probe=False later if needed.
    d = decide(attempts, requested_proof_tier, artifact_type)
    decision = {
        "artifact_type": artifact_type,
        "environment": "android_chatgpt_sandbox",
        "android_sandbox_primary": True,
        "requested_proof_tier": requested_proof_tier,
        "method_attempts": build_schema_attempts(attempts),
        "selected_method": d["selected_method"],
        "decision": d["decision"],
        "honesty_label": d["honesty_label"],
        "pc_addendum_available": True,
        "resolver_version": "browser_render_capability_resolver_v1",
        "timestamp_utc": now_stamp(),
        "html_path": str(html),
        "html_sha256": sha256_file(html),
        "attempt_evidence": attempts,
    }
    return decision


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="HTML file to render/check")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--requested-proof-tier", default="browser_screenshot_preferred", choices=["browser_screenshot_required", "browser_screenshot_preferred", "render_proxy_allowed", "static_only_allowed"])
    ap.add_argument("--artifact-type", default="operator_tracker")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--write-decision", default="decision.json")
    ap.add_argument("--skip-known-hard-fails", action="store_true", help="Skip methods marked unavailable/hanging in the reliability ledger")
    ap.add_argument("--reliability-ledger", default=str(ROOT / "runtime/state/BROWSER_RENDER_METHOD_RELIABILITY_LEDGER_LATEST.json"))
    args = ap.parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    html = Path(args.html) if args.html else out_dir / "resolver_sample.html"
    if not html.exists():
        write_html_sample(html)
    decision = resolve(html, out_dir, args.requested_proof_tier, args.artifact_type, args.timeout, skip_known_hard_fails=args.skip_known_hard_fails, reliability_ledger=Path(args.reliability_ledger) if args.reliability_ledger else None)
    decision_path = out_dir / args.write_decision
    decision_path.write_text(json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8")
    (decision_path.with_suffix(decision_path.suffix + ".sha256")).write_text(f"{sha256_file(decision_path)}  {decision_path.name}\n", encoding="utf-8")
    print(json.dumps({"decision_path": str(decision_path), "decision": decision["decision"], "selected_method": decision["selected_method"], "honesty_label": decision["honesty_label"]}, indent=2))
    return 0 if decision["decision"] != "DENY_PRODUCTION_PROMOTION" or args.requested_proof_tier == "browser_screenshot_required" else 2

if __name__ == "__main__":
    raise SystemExit(main())
