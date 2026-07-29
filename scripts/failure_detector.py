#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Failure Detector - 10 failure pattern detection engine.
Based on empirical research: 14 cases x 2 rounds x 4 dimensions.
Usage: python failure_detector.py <file> | --text "text" | --stdin
"""

import sys, json, re, os


def load_failure_patterns():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, '..', 'reference', 'failure_patterns.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_context(text, keyword, ctx=80):
    idx = text.find(keyword)
    if idx == -1:
        return 'Contains: ' + keyword
    s = max(0, idx - ctx // 2)
    e = min(len(text), idx + len(keyword) + ctx // 2)
    c = text[s:e].strip()
    return ('...' if s > 0 else '') + c + ('...' if e < len(text) else '')


def detect_f1(text, pat):
    kw = pat['detection_keywords']
    suspects = kw['suspect_laws']
    indicators = kw['suspect_indicators']
    dets = []
    for law in suspects:
        if law in text:
            dets.append({'type': 'repealed_law', 'law_name': law,
                         'evidence_text': extract_context(text, law),
                         'recommendation': law + ' was replaced by Civil Code on 2021-01-01'})
    for ind in indicators:
        if ind in text:
            dets.append({'type': 'possible_fictional', 'law_name': ind,
                         'evidence_text': extract_context(text, ind),
                         'recommendation': 'Verify if ' + ind + ' actually exists'})
    cp = re.compile(r'(?:According to|under|pursuant to|per)\s*[《]([^》]+)[》]')
    cites = cp.findall(text)
    for c in cites:
        if c not in suspects and c not in indicators:
            has_v = any(v in text for v in kw['validity_signals'])
            if not has_v and c not in [d.get('law_name', '') for d in dets]:
                dets.append({'type': 'missing_validity', 'law_name': c,
                             'recommendation': 'Mark effective date when citing ' + c})
    return {'fired': len(dets) > 0, 'probability': min(len(dets) * 0.3, 1.0),
            'severity': 'critical', 'detections': dets if dets else None}


def detect_f2(text, pat):
    kw = pat['detection_keywords']
    charges = kw['charge_indicators']
    found = [c for c in charges if c in text]
    has_alt = any(p in text for p in ['alternative', 'also', 'might constitute', 'prosecution perspective', 'defense perspective'])
    dets = []
    if len(found) == 1 and not has_alt:
        rel = {'intentional injury': 'attempted murder', 'affray': 'intentional injury',
               'snatch': 'robbery', 'theft': 'robbery'}
        sc = found[0]
        if sc in rel:
            dets.append({'type': 'single_charge', 'found_charge': sc,
                         'missing_alternative': rel[sc],
                         'recommendation': 'Also analyze ' + rel[sc] + ' from prosecution perspective'})
    return {'fired': len(dets) > 0, 'probability': min(len(found) * 0.15 + len(dets) * 0.3, 1.0) if found else 0.1,
            'severity': 'high', 'detections': dets if dets else None}


def detect_f3(text, pat):
    kw = pat['detection_keywords']
    ss = kw['sentencing_signals']
    sent_matches = [s for s in ss if s in text]
    dets = []
    if sent_matches:
        has_conf = any(p in text for p in ['for reference only', 'uncertainty', 'actual sentence may', 'error margin', 'confidence'])
        if not has_conf:
            dets.append({'type': 'no_confidence', 'recommendation': 'Disclose uncertainty; empirical error can reach 71% (Xu case: predicted 3.5y vs actual 6y)'})
    return {'fired': len(dets) > 0, 'probability': min(len(sent_matches) * 0.25, 1.0),
            'severity': 'high', 'detections': dets if dets else None}


def detect_f4(text, pat):
    kw = pat['detection_keywords']
    shallow = kw['shallow_signals']
    depth_inds = ['alternative theory', 'exception', 'legal dispute', 'academic view', 'different opinion',
                  'might also be', 'comparative law', 'extraterritorial']
    has_shallow = any(s in text for s in shallow)
    has_depth = any(d in text for d in depth_inds)
    dets = []
    if has_shallow and not has_depth and len(text) > 500:
        dets.append({'type': 'shallow_conclusion', 'recommendation': 'Add depth: alternative theories, exceptions, academic disputes'})
    return {'fired': len(dets) > 0, 'probability': 0.5 if dets else 0.2,
            'severity': 'critical', 'detections': dets if dets else None}


def detect_f5(text, pat):
    kw = pat['detection_keywords']
    traps = kw['user_input_traps']
    if isinstance(traps, dict):
        trap_items = []
        for g in traps.values():
            trap_items.extend(g if isinstance(g, list) else [str(g)])
    else:
        trap_items = traps if isinstance(traps, list) else []
    dets = []
    for trap in trap_items:
        if trap in text:
            has_corr = any(p in text for p in ['repealed', 'replaced', 'does not exist', 'not found', 'please verify', 'needs verification'])
            if not has_corr:
                dets.append({'type': 'trap_accepted', 'evidence_text': 'AI accepted potentially problematic premise: ' + trap,
                             'recommendation': 'First verify if ' + trap + ' is real and valid'})
    return {'fired': len(dets) > 0, 'probability': min(len(dets) * 0.4, 1.0),
            'severity': 'critical', 'detections': dets if dets else None}


def detect_f6(text, pat):
    kw = pat['detection_keywords']
    missing = kw['missing_guidance_elements']
    elem_pats = {
        'evidence list': ['evidence', 'collect', 'proof', 'evidence list', 'prepare', 'notarize'],
        'procedure steps': ['step', 'procedure', 'process', 'first', 'then', 'action'],
        'timeline': ['limitation', 'deadline', 'timeline', 'days', 'within', 'from the date'],
        'risk warning': ['risk', 'caution', 'warning', 'disclaimer', 'does not constitute', 'for reference only'],
        'alternatives': ['negotiate', 'mediation', 'arbitration', 'alternative', 'settlement']
    }
    found = [e for e, pats in elem_pats.items() if any(p in text for p in pats)]
    dets = []
    if len(found) < 3 and len(text) > 300:
        dets.append({'type': 'insufficient_guidance', 'found_elements': found,
                     'recommendation': 'Add: evidence checklist + procedure steps + timeline + risk warnings + alternatives. Baseline: DS guidance avg 2.96/5, Qwen 1.70/5. T5 template recommended.'})
    return {'fired': len(dets) > 0, 'probability': 1 - (len(found) / 5),
            'severity': 'high', 'detections': dets if dets else None}


def detect_f7(text, pat):
    kw = pat['detection_keywords']
    calc_sigs = kw['calculation_signals']
    has_calc = any(s in text for s in calc_sigs)
    dets = []
    if has_calc:
        pcts = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        lprs = re.findall(r'LPR[^\d]*(\d+(?:\.\d+)?)', text)
        if len(pcts) >= 2:
            pv = [float(p) for p in pcts]
            if max(pv) - min(pv) > 5:
                dets.append({'type': 'percentage_discrepancy', 'recommendation': 'Verify calculation logic and consistency'})
        if len(lprs) >= 2:
            lv = [float(l) for l in lprs]
            if max(lv) - min(lv) > 2:
                dets.append({'type': 'lpr_benchmark_inconsistency',
                             'recommendation': 'LPR benchmark choice (contract date vs filing date) can cause 30%+ difference. DS uses filing date (~13%), Qwen uses contract date (~17%).'})
    return {'fired': len(dets) > 0, 'probability': min(len(dets) * 0.35, 1.0),
            'severity': 'medium_high', 'detections': dets if dets else None}


def detect_f8(text, pat):
    kw = pat['detection_keywords']
    simpl = kw['causal_simplification_signals']
    missing_f = kw['missing_factors']
    has_simpl = any(s in text for s in simpl)
    has_complex = any(f in text for f in missing_f)
    dets = []
    if has_simpl and not has_complex:
        dets.append({'type': 'causal_simplification', 'recommendation': 'Consider multi-cause analysis, omission liability, prior-act obligations'})
    return {'fired': len(dets) > 0, 'probability': 0.4 if dets else 0.1,
            'severity': 'high', 'detections': dets if dets else None}


def detect_f9(text, pat):
    kw = pat['detection_keywords']
    missing_intl = kw['missing_international']
    hr_kw = ['personal rights', 'personality rights', 'women', 'children', 'domestic violence', 'abuse', 'fundamental rights', 'human rights']
    has_hr = any(h in text for h in hr_kw)
    has_intl = any(i in text for i in missing_intl)
    dets = []
    if has_hr and not has_intl:
        dets.append({'type': 'intl_law_gap', 'recommendation': 'Consider referencing relevant international conventions (e.g. CEDAW, ICCPR) for fundamental rights cases'})
    return {'fired': len(dets) > 0, 'probability': 0.5 if dets else 0.1,
            'severity': 'medium', 'detections': dets if dets else None}


def detect_f10(text, pat):
    kw = pat['detection_keywords']
    user_inds = kw['user_type_indicators']
    has_user_ctx = any(ind in text for ind in user_inds)
    has_diff = any(p in text for p in ['as a law student', 'as a lawyer', 'for non-professionals', 'if you are', 'for general readers'])
    dets = []
    if not has_user_ctx and not has_diff and len(text) > 300:
        dets.append({'type': 'no_user_differentiation', 'recommendation': 'Differentiate output by user background: law students get deep analysis; non-professionals get plain language + prominent risk warnings + lawyer referral'})
    return {'fired': len(dets) > 0, 'probability': 0.7 if dets else 0.2,
            'severity': 'critical', 'detections': dets if dets else None}


DETECTORS = {
    'F1': detect_f1, 'F2': detect_f2, 'F3': detect_f3, 'F4': detect_f4, 'F5': detect_f5,
    'F6': detect_f6, 'F7': detect_f7, 'F8': detect_f8, 'F9': detect_f9, 'F10': detect_f10,
}


def detect_all(text):
    pd = load_failure_patterns()
    patterns = pd['patterns']
    results = {}
    for p in patterns:
        pid = p['id']
        detector = DETECTORS.get(pid)
        results[pid] = detector(text, p) if detector else {'fired': False, 'probability': 0, 'severity': 'unknown', 'detections': None}
    fired = sum(1 for r in results.values() if r['fired'])
    critical = sum(1 for r in results.values() if r['fired'] and r['severity'] == 'critical')
    high = sum(1 for r in results.values() if r['fired'] and r['severity'] == 'high')
    dm = pd['dimension_mapping']
    dim_scores = {}
    for dim, related in dm.items():
        rf = [pid for pid in related if results.get(pid, {}).get('fired')]
        dim_scores[dim] = round(5 * (1 - len(rf) / len(related)), 1) if related else 5.0
    return {'meta': {'text_length': len(text), 'total_patterns': 10, 'fired_patterns': fired,
                     'critical_fired': critical, 'high_fired': high,
                     'overall_risk': 'high' if critical > 0 else 'medium' if high > 0 else 'low'},
            'dimension_scores': dim_scores,
            'detections': {pid: r for pid, r in results.items() if r['fired']},
            'all_detections': results}


def main():
    text = None
    if len(sys.argv) >= 2:
        if sys.argv[1] == '--stdin':
            text = sys.stdin.read()
        elif sys.argv[1] == '--text' and len(sys.argv) >= 3:
            text = sys.argv[2]
        else:
            fp = sys.argv[1]
            if os.path.exists(fp):
                with open(fp, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                print(json.dumps({'error': 'File not found: ' + fp}, ensure_ascii=False))
                sys.exit(1)
    if not text:
        print(json.dumps({'error': 'No input. Usage: failure_detector.py <file> | --text "text" | --stdin'}, ensure_ascii=False))
        sys.exit(1)
    results = detect_all(text)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            