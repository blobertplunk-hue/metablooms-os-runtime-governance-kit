'use strict';
function _hex(bytes){
  let out='';
  for(let i=0;i<bytes;i++) out += Math.floor(Math.random()*256).toString(16).padStart(2,'0');
  return out;
}
function toMetaBloomsTelemetryEvent(raw, opts={}){
  if(!raw || typeof raw !== 'object') throw new Error('raw event object required');
  const traceId = opts.traceId || _hex(16);
  const spanId = opts.spanId || _hex(8);
  const signalType = raw.signalType || 'none';
  const eventName = signalType === 'none' ? 'metablooms.learning.attempt' : 'metablooms.learning.signal';
  return {
    event_name: eventName,
    event_time_unix_ms: Number(raw.timestampMs || Date.now()),
    trace_id: traceId,
    span_id: spanId,
    parent_span_id: opts.parentSpanId || null,
    traceparent: `00-${traceId}-${spanId}-01`,
    severity_number: raw.teacherFlag ? 13 : 9,
    attributes: {
      'artifact.id': raw.artifactId || opts.artifactId || 'unknown',
      'session.id': String(raw.sessionId || opts.sessionId || 'unknown'),
      'student.pseudonymous_id': String(raw.studentId || opts.studentId || 'anon'),
      'question.id': String(raw.questionId || 'unknown'),
      'question.type': String(raw.questionType || 'unknown'),
      'fraction.target': String(raw.fractionTarget || ''),
      'student.response': raw.studentResponse === undefined ? null : raw.studentResponse,
      'answer.correct': !!raw.correct,
      'response.time_ms': Number(raw.responseTimeMs || 0),
      'attempt.number': Number(raw.attemptNumber || 1),
      'hint.used': !!raw.hintUsed,
      'signal.type': String(signalType),
      'signal.id': raw.signalId || null,
      'teacher.flag': !!raw.teacherFlag,
      'teacher.action': raw.teacherAction || null
    }
  };
}
if (typeof module !== 'undefined' && module.exports) module.exports = { toMetaBloomsTelemetryEvent };
else if (typeof window !== 'undefined') window.toMetaBloomsTelemetryEvent = toMetaBloomsTelemetryEvent;
