/**
 * MISCONCEPTION_TELEMETRY_ENGINE_v1.js
 * 
 * Drop-in browser-side telemetry layer for MetaBlooms learning HTML activities.
 * Classifies student interactions as behavioral_misuse or conceptual_misconception,
 * then emits teacher-actionable signals.
 * 
 * Usage:
 *   const engine = new MisconceptionTelemetryEngine({ studentId: 'anon-001', sessionId: 'sess-abc' });
 *   engine.recordAttempt({ questionId: 'Q1', fractionTarget: '1/4', studentResponse: 0.7, correct: false, responseTimeMs: 800 });
 *   const summary = engine.getSessionSummary();
 *   engine.onTeacherFlag(signal => updateTeacherDashboard(signal));
 * 
 * No external dependencies. Works on iPad/mobile/Google Sites iframe.
 * No PII stored — studentId must be anonymized by caller.
 * 
 * SEE evidence baked into classifier thresholds:
 *   - PMC: whole number bias, denominator-size confusion, SDBF-OR error (Stafylidou & Vosniadou 2004)
 *   - EdWeek 2024: 3/8 > 3/4 because 8>4 is most common classroom number line error
 *   - PMC intervention: larger denominator = closer to zero (Catch the Monster study)
 *   - Riccomini 2025: error analysis as cornerstone of intervention (NCII)
 */

'use strict';

class MisconceptionTelemetryEngine {
  constructor(config = {}) {
    this.studentId  = config.studentId  || 'anon';
    this.sessionId  = config.sessionId  || this._uuid();
    this.artifactId = config.artifactId || 'unknown';
    this.events     = [];
    this.attempts   = {};      // questionId -> array of attempts
    this.signalCounts = {};    // signalId -> count
    this._flagCallbacks = [];
    this._debugMode = config.debug || false;
  }

  // ── PUBLIC API ────────────────────────────────────────────────────────────

  /**
   * Record one student attempt on one question.
   * @param {Object} attempt
   *   questionId      {string}  — unique question identifier
   *   questionType    {string}  — 'place_on_line'|'compare_fractions'|'identify_fraction'
   *   fractionTarget  {string}  — e.g. '1/4'
   *   studentResponse {*}       — number (0-1 for placement), string for compare
   *   correct         {boolean}
   *   responseTimeMs  {number}
   *   hintUsed        {boolean}
   *   positionCorrect {number}  — for place_on_line: correct decimal position (0-1)
   *   denominator     {number}  — denominator of target fraction
   *   numerator       {number}  — numerator of target fraction
   */
  recordAttempt(attempt) {
    const qid = attempt.questionId;
    if (!this.attempts[qid]) this.attempts[qid] = [];
    const attemptNum = this.attempts[qid].length + 1;
    this.attempts[qid].push({ ...attempt, attemptNum, ts: Date.now() });

    const signal = this._classify(attempt, this.attempts[qid]);
    const event  = this._buildEvent(attempt, attemptNum, signal);
    this.events.push(event);

    if (signal.signalId) {
      this.signalCounts[signal.signalId] = (this.signalCounts[signal.signalId] || 0) + 1;
    }
    if (event.teacherFlag) {
      this._flagCallbacks.forEach(cb => cb(event));
    }
    if (this._debugMode) console.log('[MTEv1]', event);
    return event;
  }

  /** Register a callback fired whenever a teacher-flag event is emitted. */
  onTeacherFlag(callback) {
    this._flagCallbacks.push(callback);
  }

  /** Get full session summary for teacher dashboard. */
  getSessionSummary() {
    const attempted  = Object.keys(this.attempts).length;
    const allAttempts = this.events;
    const firstAttempts = allAttempts.filter(e => e.attemptNumber === 1);
    const correct    = firstAttempts.filter(e => e.correct).length;
    const accuracy   = attempted > 0 ? Math.round(correct / attempted * 100) : 0;

    const behavioralFlags = [...new Set(
      this.events.filter(e => e.signalType === 'behavioral' && e.signalId).map(e => e.signalId)
    )];
    const conceptualFlags = [...new Set(
      this.events.filter(e => e.signalType === 'conceptual' && e.signalId).map(e => e.signalId)
    )];

    // Top misconception = highest count conceptual signal
    let topMisconception = null;
    let topCount = 0;
    for (const [id, count] of Object.entries(this.signalCounts)) {
      if (this._CONCEPTUAL_SIGNAL_IDS.includes(id) && count > topCount) {
        topMisconception = id;
        topCount = count;
      }
    }

    const needsIntervention = conceptualFlags.length > 0 || 
      behavioralFlags.includes('ABANDONMENT') || 
      behavioralFlags.includes('HINT_DEPENDENCY');

    return {
      studentId:          this.studentId,
      sessionId:          this.sessionId,
      questionsAttempted: attempted,
      questionsCorrect:   correct,
      accuracyPct:        accuracy,
      behavioralFlags,
      conceptualFlags,
      topMisconception,
      needsIntervention,
      teacherNote:        this._generateTeacherNote(topMisconception, behavioralFlags, accuracy),
      signalCounts:       { ...this.signalCounts },
      totalEvents:        this.events.length,
    };
  }

  /** Get all raw events (for export/logging). */
  getAllEvents() { return [...this.events]; }

  /** Reset session state. */
  reset(newSessionId) {
    this.sessionId    = newSessionId || this._uuid();
    this.events       = [];
    this.attempts     = {};
    this.signalCounts = {};
  }

  // ── CLASSIFIER ────────────────────────────────────────────────────────────

  _classify(attempt, priorAttempts) {
    // 1. Behavioral checks first (faster, no math needed)
    const behavioral = this._classifyBehavioral(attempt, priorAttempts);
    if (behavioral.signalId) return behavioral;

    // 2. Conceptual checks (only on incorrect answers)
    if (!attempt.correct) {
      const conceptual = this._classifyConceptual(attempt);
      if (conceptual.signalId) return conceptual;
    }

    return { signalType: 'none', signalId: null, confidence: 1.0 };
  }

  _classifyBehavioral(attempt, priorAttempts) {
    // BRUTE_FORCE_TAP: 3+ attempts within 4 seconds
    if (priorAttempts.length >= 3) {
      const recent = priorAttempts.slice(-3);
      const span = recent[recent.length-1].ts - recent[0].ts;
      if (span < 4000) {
        return { signalType:'behavioral', signalId:'BRUTE_FORCE_TAP', confidence:0.9,
                 teacherAction:'Check in — student may be frustrated or guessing' };
      }
    }

    // RAPID_SEQUENTIAL: under 1.5s
    if (attempt.responseTimeMs < 1500 && attempt.responseTimeMs > 0) {
      return { signalType:'behavioral', signalId:'RAPID_SEQUENTIAL', confidence:0.75,
               teacherAction:'Remind student to read the question carefully' };
    }

    // HINT_DEPENDENCY: 3+ consecutive hint uses
    const hintRun = priorAttempts.slice(-2).every(a => a.hintUsed) && attempt.hintUsed;
    if (hintRun) {
      return { signalType:'behavioral', signalId:'HINT_DEPENDENCY', confidence:0.85,
               teacherAction:'Student may need small-group pull for this concept' };
    }

    return { signalType:'none', signalId:null, confidence:1.0 };
  }

  _classifyConceptual(attempt) {
    const { questionType, fractionTarget, studentResponse, positionCorrect,
            numerator, denominator } = attempt;

    if (questionType === 'place_on_line' && typeof studentResponse === 'number') {
      const expected = positionCorrect !== undefined
        ? positionCorrect
        : (numerator && denominator ? numerator / denominator : null);

      if (expected === null) return { signalType:'none', signalId:null, confidence:1.0 };

      const error = studentResponse - expected;
      const absError = Math.abs(error);

      // UNIT_FRACTION_INVERSION: placed further right than expected (inversion pattern)
      // e.g. placed 1/8 at 0.75 instead of 0.125
      if (numerator === 1 && denominator && studentResponse > expected + 0.2) {
        return { signalType:'conceptual', signalId:'UNIT_FRACTION_INVERSION', confidence:0.85,
                 teacherAction:'Fold paper in half vs eighths — which piece is bigger?' };
      }

      // DENOMINATOR_SIZE_CONFUSION: response approximates 1-(expected)
      // e.g. for 1/4 (0.25), student places at 0.75 (= 3/4 position, confused by 4)
      if (denominator && absError > 0.15) {
        const invertedPos = denominator > 0 ? 1 - expected : null;
        if (invertedPos && Math.abs(studentResponse - invertedPos) < 0.15) {
          return { signalType:'conceptual', signalId:'DENOMINATOR_SIZE_CONFUSION', confidence:0.8,
                   teacherAction:'Pizza model: 8 slices vs 4 slices — which slice is bigger?' };
        }
      }

      // TICK_MARK_COUNTING: off by exactly one interval
      if (denominator && denominator > 0) {
        const intervalSize = 1 / denominator;
        const offByOne = Math.abs(absError - intervalSize) < 0.05;
        if (offByOne) {
          return { signalType:'conceptual', signalId:'TICK_MARK_COUNTING', confidence:0.75,
                   teacherAction:'Teach: count the spaces, not the lines. Use colored blocks.' };
        }
      }

      // ZERO_ANCHOR_CONFUSION: placed outside 0-1 range significantly
      if (studentResponse > 1.1 || studentResponse < -0.1) {
        return { signalType:'conceptual', signalId:'ZERO_ANCHOR_CONFUSION', confidence:0.9,
                 teacherAction:'Establish 0 and 1 as anchors. Ask: can this fraction be more than a whole?' };
      }

      // WHOLE_NUMBER_BIAS: placed at numerator/denominator position (e.g., 1/4 at 0.4 = numerator.denominator)
      if (numerator && denominator) {
        const wholeNumPos = parseFloat(`${numerator}.${denominator}`) / 10;
        if (!isNaN(wholeNumPos) && Math.abs(studentResponse - wholeNumPos) < 0.08) {
          return { signalType:'conceptual', signalId:'WHOLE_NUMBER_BIAS', confidence:0.8,
                   teacherAction:'Use unit fraction anchor: show 1/2 vs 1/6 with equal-length segments' };
        }
      }
    }

    if (questionType === 'compare_fractions') {
      // DENOMINATOR_SIZE_CONFUSION on comparison: larger denominator chosen as larger
      const res = String(studentResponse);
      if (res.includes('wrong_larger_denom')) {
        return { signalType:'conceptual', signalId:'DENOMINATOR_SIZE_CONFUSION', confidence:0.85,
                 teacherAction:'3/8 vs 3/4: draw both on number line. Which is further from 0?' };
      }
    }

    return { signalType:'none', signalId:null, confidence:1.0 };
  }

  // ── HELPERS ───────────────────────────────────────────────────────────────

  _buildEvent(attempt, attemptNum, signal) {
    const teacherFlag = signal.signalId !== null &&
      (signal.signalType === 'conceptual' ||
       ['ABANDONMENT','HINT_DEPENDENCY'].includes(signal.signalId));

    return {
      eventId:         this._uuid(),
      sessionId:       this.sessionId,
      studentId:       this.studentId,
      timestampMs:     Date.now(),
      questionId:      attempt.questionId,
      questionType:    attempt.questionType || 'unknown',
      fractionTarget:  attempt.fractionTarget || '',
      studentResponse: attempt.studentResponse,
      correct:         !!attempt.correct,
      responseTimeMs:  attempt.responseTimeMs || 0,
      attemptNumber:   attemptNum,
      hintUsed:        !!attempt.hintUsed,
      signalType:      signal.signalType,
      signalId:        signal.signalId || null,
      signalConfidence:signal.confidence || 1.0,
      teacherAction:   signal.teacherAction || null,
      teacherFlag,
    };
  }

  _generateTeacherNote(topMisconception, behavioralFlags, accuracy) {
    const NOTES = {
      UNIT_FRACTION_INVERSION:   'Needs work on unit fraction size — try folding paper activity',
      DENOMINATOR_SIZE_CONFUSION:'Confuses larger denominator with larger fraction — use pizza/candy bar model',
      TICK_MARK_COUNTING:        'Counts tick marks instead of intervals — use colored interval blocks',
      ZERO_ANCHOR_CONFUSION:     'Does not anchor fractions between 0 and 1 — establish anchors first',
      WHOLE_NUMBER_BIAS:         'Treats fraction as two separate numbers — use unit fraction anchor on number line',
      EQUIVALENT_FRACTION_GAP:   'Does not recognize equivalent fractions — overlay two number lines',
    };
    if (topMisconception && NOTES[topMisconception]) {
      return NOTES[topMisconception];
    }
    if (behavioralFlags.includes('HINT_DEPENDENCY')) {
      return 'Relied on hints frequently — consider small-group pull';
    }
    if (accuracy < 50) {
      return 'Low accuracy — review prerequisite concepts before next session';
    }
    if (accuracy >= 80) {
      return 'Strong performance — ready for next level';
    }
    return 'Monitor progress — review errors before next session';
  }

  _uuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  get _CONCEPTUAL_SIGNAL_IDS() {
    return ['WHOLE_NUMBER_BIAS','DENOMINATOR_SIZE_CONFUSION','TICK_MARK_COUNTING',
            'UNIT_FRACTION_INVERSION','ZERO_ANCHOR_CONFUSION','EQUIVALENT_FRACTION_GAP'];
  }
}

// Export for both browser (global) and node (module)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MisconceptionTelemetryEngine };
} else if (typeof window !== 'undefined') {
  window.MisconceptionTelemetryEngine = MisconceptionTelemetryEngine;
}
