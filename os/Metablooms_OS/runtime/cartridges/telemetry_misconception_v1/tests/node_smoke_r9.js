
const { MisconceptionTelemetryEngine } = require('/mnt/data/Metablooms_OS/2_engines/telemetry/MISCONCEPTION_TELEMETRY_ENGINE_v1.js');
const { toMetaBloomsTelemetryEvent } = require('/mnt/data/Metablooms_OS/2_engines/telemetry/telemetry_event_adapter_v1.js');
const engine = new MisconceptionTelemetryEngine({studentId:'anon-001', sessionId:'sess-r9', artifactId:'fractions_number_line_telemetry_v1'});
const raw = engine.recordAttempt({questionId:'Q1', questionType:'fraction_number_line', fractionTarget:'3/4', studentResponse:'3/8', correct:false, responseTimeMs:900});
const canonical = toMetaBloomsTelemetryEvent(raw, {artifactId:'fractions_number_line_telemetry_v1'});
console.log(JSON.stringify({raw, canonical}, null, 2));
