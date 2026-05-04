#!/usr/bin/env python3
"""Purpose: Enforce CDR static-analysis and complexity quality gates.
Inputs: CDRStaticAnalysisComplexityPacket_v1 JSON with risk tier, target files, static metrics, test binding, and recursive-improvement state.
Outputs: ALLOW/DENY verdict with exact threshold and zero-tolerance violations.
Failure modes: Missing analysis/test evidence, over-threshold complexity, zero-tolerance static issues, or unhandled high-value repair candidates deny acceptance.
Debuggability: Returns risk tier, thresholds, file-level metrics, violations, and waiver problems for direct repair.
"""
import json, sys
THRESHOLDS={
 'LOW':{'max_function_lines':80,'max_cyclomatic_complexity':15,'max_cognitive_complexity_proxy':20,'max_nesting_depth':5,'max_broad_exception_handlers':3,'max_todo_count':5},
 'MEDIUM':{'max_function_lines':60,'max_cyclomatic_complexity':12,'max_cognitive_complexity_proxy':16,'max_nesting_depth':4,'max_broad_exception_handlers':2,'max_todo_count':3},
 'HIGH':{'max_function_lines':45,'max_cyclomatic_complexity':10,'max_cognitive_complexity_proxy':12,'max_nesting_depth':3,'max_broad_exception_handlers':1,'max_todo_count':1},
 'CRITICAL':{'max_function_lines':35,'max_cyclomatic_complexity':8,'max_cognitive_complexity_proxy':10,'max_nesting_depth':3,'max_broad_exception_handlers':0,'max_todo_count':0},
}
ZERO_TOLERANCE=['syntax_errors','dynamic_exec_count','secret_literal_count','unsafe_path_pattern_count']
REQ_STATIC=['ast_parse','complexity_scan','security_grep','style_scan']
REQ_TEST=['positive_fixture','negative_fixture','eval_test','regression_binding']

def _has_waiver(pkt, file_path, metric):
    for waiver in pkt.get('waivers',[]):
        if waiver.get('file')==file_path and waiver.get('metric')==metric:
            return bool(waiver.get('risk_acceptance') and waiver.get('repair_handoff') and waiver.get('expires_after_stage'))
    return False

def evaluate(pkt):
    reasons=[]; violations=[]
    tier=pkt.get('risk_tier','HIGH')
    thresholds=THRESHOLDS.get(tier)
    if thresholds is None:
        reasons.append('invalid_risk_tier')
        thresholds=THRESHOLDS['HIGH']
    if not pkt.get('target_files'):
        reasons.append('missing_target_files')
    static=pkt.get('static_analysis',{})
    for req in REQ_STATIC:
        if not static.get(req):
            reasons.append(f'missing_static_analysis:{req}')
    test=pkt.get('test_binding',{})
    for req in REQ_TEST:
        if not test.get(req):
            reasons.append(f'missing_test_binding:{req}')
    reports=static.get('file_reports',[])
    if not reports:
        reasons.append('missing_file_reports')
    for report in reports:
        f=report.get('file','<unknown>')
        for metric in ZERO_TOLERANCE:
            if report.get(metric,0):
                violations.append({'file':f,'metric':metric,'actual':report.get(metric),'limit':0,'waivable':False})
        checks=[
            ('max_function_lines','max_function_lines'),
            ('max_cyclomatic_complexity','max_cyclomatic_complexity'),
            ('max_cognitive_complexity_proxy','max_cognitive_complexity_proxy'),
            ('max_nesting_depth','max_nesting_depth'),
            ('broad_exception_handlers','max_broad_exception_handlers'),
            ('todo_count','max_todo_count'),
        ]
        for field,limkey in checks:
            actual=report.get(field,0); limit=thresholds[limkey]
            if actual>limit:
                if not _has_waiver(pkt,f,field):
                    violations.append({'file':f,'metric':field,'actual':actual,'limit':limit,'waivable':True})
    rec=pkt.get('recursive_improvement',{})
    for c in rec.get('candidates',[]):
        high=c.get('benefit_score',0)>=3 and c.get('risk_score',9)<=2 and c.get('scope_cost',9)<=2 and c.get('stage_fit') is True
        if high and c.get('decision') in ('ignored','rejected') and not c.get('handoff'):
            reasons.append('high_value_static_quality_candidate_without_handoff')
    return {'verdict':'DENY' if reasons or violations else 'ALLOW','risk_tier':tier,'thresholds':thresholds,'reasons':reasons,'violations':violations,'metrics_by_file':reports}

if __name__=='__main__':
    with open(sys.argv[1],encoding='utf-8') as f:
        pkt=json.load(f)
    print(json.dumps(evaluate(pkt),indent=2,sort_keys=True))
