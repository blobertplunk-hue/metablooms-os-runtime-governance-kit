#!/usr/bin/env node
/* MetaBlooms pre_tool_action_gate_v1
 * Thin local gate for ChatGPT-sandbox-governed actions. It does not intercept platform tools itself;
 * it makes governed execution contingent on a ToolCallEnvelope_v1 -> PolicyDecision_v1 receipt.
 */
const fs = require('fs');
const crypto = require('crypto');
const path = require('path');
function now(){ return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'); }
function sha256(s){ return crypto.createHash('sha256').update(s).digest('hex'); }
function die(msg){ console.error(msg); process.exit(2); }
const file = process.argv[2];
if(!file) die('usage: pre_tool_action_gate_v1.js <ToolCallEnvelope_v1.json>');
const raw = fs.readFileSync(file, 'utf8');
let e; try { e = JSON.parse(raw); } catch(err){ die('invalid_json:'+err.message); }
const req = ['schema_version','envelope_id','stage_id','action_type','tool_name','intent','risk_tier','requested_at_utc','limits','artifacts'];
const missing = req.filter(k => !(k in e));
function decision(decision, code, rationale, matched, next){
  const out = {
    schema_version: 'PolicyDecision_v1',
    decision_id: `decision_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`,
    envelope_id: e.envelope_id || 'UNKNOWN_ENVELOPE',
    stage_id: e.stage_id || 'UNKNOWN_STAGE',
    decision,
    reason_code: code,
    rationale,
    decided_at_utc: now(),
    enforced_by: 'pre_tool_action_gate_v1',
    receipt_path: (e.artifacts && e.artifacts.receipt_path) || '',
    safe_to_execute: decision === 'ALLOW',
    required_next_action: next || (decision === 'ALLOW' ? 'execute_action_and_write_action_receipt' : 'do_not_execute_action'),
    matched_rules: matched || [],
    envelope_sha256: sha256(raw)
  };
  const rp = out.receipt_path || path.join(path.dirname(file), out.decision_id + '.json');
  fs.mkdirSync(path.dirname(rp), {recursive:true});
  fs.writeFileSync(rp, JSON.stringify(out, null, 2) + '\n');
  console.log(JSON.stringify(out, null, 2));
  process.exit(decision === 'DENY' ? 10 : 0);
}
if(missing.length) decision('DENY','SCHEMA_REQUIRED_FIELD_MISSING',`Missing required fields: ${missing.join(', ')}`,['schema.required'], 'repair_envelope_then_retry');
if(e.schema_version !== 'ToolCallEnvelope_v1') decision('DENY','UNSUPPORTED_ENVELOPE_SCHEMA','Only ToolCallEnvelope_v1 is accepted.',['schema.version'], 'repair_envelope_then_retry');
const writes = (e.artifacts.write_paths || []).join('\n');
const reads = (e.artifacts.read_paths || []).join('\n');
const allPaths = writes + '\n' + reads;
if(/(^|\/|\\)\.\.($|\/|\\)/.test(allPaths) || /\x00/.test(allPaths)) decision('DENY','UNSAFE_PATH','Envelope includes unsafe path traversal or NUL byte.',['path.safety'], 'repair_path_binding');
if(e.action_type === 'python') decision('DENY','PYTHON_ROUTE_NOT_AUTHORIZED_FOR_STAGE6B','Stage6B wrapper is shell/node-first; Python actions require a separate approved profile.',['method.reliability','python.policy'], 'use_shell_or_node_profile_or_request_approval');
if(e.tool_name && /unzip\s+-tqq|unzip-tqq|unzip_tqq/i.test(e.tool_name + ' ' + (e.command_summary||''))) decision('DENY','FORBIDDEN_VALIDATION_METHOD','Known timeout-prone validation method is denied; use zipinfo -t or Node/yauzl CRC proof.',['method.denylist'], 'select_replacement_validation_method');
if(e.risk_tier === 'critical' || e.action_type === 'pointer_promotion') {
  if(!e.approval_token) decision('REQUIRE_APPROVAL','APPROVAL_TOKEN_REQUIRED','Critical/pointer-promotion action requires an explicit approval token before execution.',['hitl.approval'], 'obtain_signed_or_stage_scoped_approval_token');
}
if(e.action_type === 'export' && !e.approval_token) decision('REQUIRE_APPROVAL','EXPORT_APPROVAL_REQUIRED','Full authority export is high-impact and requires explicit scoped approval before execution.',['hitl.approval','export.guard'], 'obtain_export_approval_token');
if(e.requires_see && (!Array.isArray(e.see_evidence_refs) || e.see_evidence_refs.length === 0)) decision('DEFER','SEE_EVIDENCE_REQUIRED','Envelope declares SEE is required but has no evidence refs.',['see.required'], 'run_web_research_and_bind_evidence_refs');
const lim = e.limits || {};
const explicitBudgetApproval = e.action_type === 'export' && typeof e.approval_token === 'string' && /STAGE6G.*BUDGET_APPROVED|BUDGET_APPROVED.*STAGE6G|EXPLICIT_BUDGET_APPROVAL/i.test(e.approval_token);
if (explicitBudgetApproval) {
  if ((lim.timeout_seconds||0) > 180 || (lim.max_files||0) > 10000 || (lim.max_steps||0) > 100 || (lim.max_bytes||0) > 200000000) {
    decision('DEFER','EXPLICIT_BUDGET_APPROVAL_HARD_CAP_EXCEEDED','Explicit Stage6G budget approval was present, but requested export exceeds hard safety caps.',['runaway.breaker','hitl.approval'], 'chunk_action_or_request_narrower_budget');
  }
} else if((lim.timeout_seconds||0) > 90 || (lim.max_files||0) > 2500 || (lim.max_steps||0) > 60) decision('DEFER','RUNAWAY_BUDGET_REVIEW_REQUIRED','Requested action exceeds Stage6B default bounded budget and requires chunking or approval.',['runaway.breaker'], 'chunk_action_or_request_budget_approval');
if((lim.max_bytes||0) > 100000000 && e.action_type !== 'zip') decision('DEFER','BYTE_BUDGET_REVIEW_REQUIRED','Non-ZIP action requested a high byte budget; requires explicit chunking rationale.',['runaway.breaker'], 'chunk_action_or_request_budget_approval');
decision('ALLOW','LOW_RISK_BOUNDED_ACTION','Envelope passed schema, method, path, SEE, approval, and bounded-budget checks.',['schema.required','path.safety','runaway.breaker','method.reliability'], 'execute_action_and_write_action_receipt');
