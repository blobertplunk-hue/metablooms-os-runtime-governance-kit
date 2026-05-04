#!/usr/bin/env node
import fs from 'fs'; import path from 'path';
const root = process.env.METABLOOMS_ROOT || '/mnt/data/Metablooms_OS';
const task = process.argv[2] || 'boot_probe';
const method = process.argv[3] || 'auto';
const candidates = [
  path.join(root,'0_kernel/registry/sandbox_capability_router/SANDBOX_CAPABILITY_ROUTER_CARTRIDGE_LATEST.json'),
  path.join(root,'0_kernel/registry/sandbox_capability_router/SANDBOX_ROUTER_ENFORCEMENT_WIRING_LATEST.json')
];
function load(){ for (const p of candidates){ if(fs.existsSync(p)) return {p, j:JSON.parse(fs.readFileSync(p,'utf8'))}; } throw new Error('router_not_found'); }
function decide(router){
  const route = router.routes?.[task];
  if(!route) return {allowed:false, decision:'DENY', reason:'unknown_task', task, method};
  const hay = `${task} ${method}`.toLowerCase();
  const hits=[];
  for(const r of router.global_denylist || []){
    const applies=(r.applies_to||[]).includes(task) || (r.applies_to||[]).some(x=>hay.includes(String(x).toLowerCase()));
    const hit=(r.patterns||[]).some(p=>hay.includes(String(p).toLowerCase()));
    if(applies && hit) hits.push(r.id);
  }
  if(hits.length) return {allowed:false, decision:'DENY', reason:'denylist_hit', deny_hits:hits, task, method};
  const allowed = method==='auto' || method==='policy_deny' || (route.preferred||[]).includes(method) || (route.fallback||[]).includes(method);
  return {allowed, decision:allowed?'ALLOW':'DENY', reason:allowed?'route_allowed':'method_not_in_route', task, method, required_gates:route.required_gates||[]};
}
try{ const {p,j}=load(); const out=decide(j); out.router_path=p; console.log(JSON.stringify(out,null,2)); process.exit(out.allowed?0:7); }
catch(e){ console.log(JSON.stringify({allowed:false,decision:'DENY',reason:String(e.message||e),task,method},null,2)); process.exit(9); }
