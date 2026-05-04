const SPREADSHEET_ID = '1kw9eUPfmXVnjq38-J1Ci9ryqJVZxu0e8gUEzhzOG_gs';
const SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1kw9eUPfmXVnjq38-J1Ci9ryqJVZxu0e8gUEzhzOG_gs/edit?gid=0#gid=0';
const APP_VERSION = 'staar-gas-sync-v1';
const ATTEMPTS_SHEET = 'Attempts';
const LEADERBOARD_SHEET = 'Leaderboard';
const CACHE_SECONDS = 30;
const EVENT_DEDUPE_TTL_SECONDS = 600;
const EVENT_TAIL_SCAN_ROWS = 200;
const LEADERBOARD_SCAN_MAX_ROWS = 1000;
const LEADERBOARD_HEADERS = ['class_code', 'student_key', 'display_name', 'total_points', 'correct_count', 'attempt_events', 'last_seen_iso'];

function doGet(e) {
  e = e || { parameter: {} };
  const action = String((e.parameter && e.parameter.action) || 'ping').toLowerCase();
  if (action === 'log') return handleLog_(e);
  if (action === 'leaderboard') return handleLeaderboard_(e);
  return respond_({ ok: true, action: 'ping', version: APP_VERSION, spreadsheet_id: SPREADSHEET_ID }, e);
}


function normalizeLogParams_(p) {
  return {
    event_id: sanitizeId_(p.event_id) || Utilities.getUuid(),
    class_code: sanitizeClassCode_(p.class_code),
    student_key: sanitizeStudentKey_(p.student_key),
    display_name: sanitizeDisplayName_(p.display_name),
    question_id: sanitizeQuestionId_(p.question_id),
    teks: sanitizeEnumLike_(p.teks, 24),
    misconception: sanitizeEnumLike_(p.misconception, 24),
    correct: boolString_(p.correct),
    attempt_count: clampInt_(p.attempt_count, 0, 50),
    score_award: clampInt_(p.score_award, -1000, 1000),
    display_type: sanitizeEnumLike_(p.display_type, 24),
    scale_correct: boolString_(p.scale_correct),
    category_correct: boolString_(p.category_correct),
    operation_correct: boolString_(p.operation_correct),
    source: sanitizeSource_(p.source) || 'student_engine'
  };
}

function handleLog_(e) {
  const p = e.parameter || {};
  const n = normalizeLogParams_(p);
  const lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const attempts = getOrCreateSheet_(ss, ATTEMPTS_SHEET, [
      'timestamp_iso', 'event_id', 'class_code', 'student_key', 'display_name', 'question_id',
      'teks', 'misconception', 'correct', 'attempt_count', 'score_award', 'display_type',
      'scale_correct', 'category_correct', 'operation_correct', 'source'
    ]);
    const leaderboard = getOrCreateSheet_(ss, LEADERBOARD_SHEET, LEADERBOARD_HEADERS);

    const eventId = n.event_id;
    if (eventSeen_(attempts, eventId)) {
      return respond_({ ok: true, deduped: true, event_id: eventId }, e);
    }

    const row = [
      nowIso_(),
      eventId,
      n.class_code,
      n.student_key,
      n.display_name,
      n.question_id,
      n.teks,
      n.misconception,
      n.correct,
      n.attempt_count,
      n.score_award,
      n.display_type,
      n.scale_correct,
      n.category_correct,
      n.operation_correct,
      n.source
    ];
    attempts.appendRow(row);

    upsertLeaderboard_(leaderboard, {
      class_code: n.class_code,
      student_key: n.student_key,
      display_name: n.display_name,
      score_award: n.score_award,
      correct: truthy_(n.correct)
    });

    markEventSeen_(eventId);

    CacheService.getScriptCache().remove(cacheKey_(n.class_code, 5));
    CacheService.getScriptCache().remove(cacheKey_(n.class_code, 10));

    return respond_({ ok: true, event_id: eventId }, e);
  } finally {
    lock.releaseLock();
  }
}

function handleLeaderboard_(e) {
  const p = e.parameter || {};
  const classCode = sanitizeClassCode_(p.class_code);
  const limit = Math.min(Math.max(intOrZero_(p.limit) || 5, 1), 20);
  const cache = CacheService.getScriptCache();
  const key = cacheKey_(classCode, limit);
  const cached = cache.get(key);
  if (cached) {
    return respond_(JSON.parse(cached), e);
  }

  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const leaderboard = getOrCreateSheet_(ss, LEADERBOARD_SHEET, [
    'class_code', 'student_key', 'display_name', 'total_points', 'correct_count',
    'attempt_events', 'last_seen_iso'
  ]);

  const rows = leaderboardReadForClass_(leaderboard, classCode, limit);
  const payload = { ok: true, class_code: classCode, top: rows, generated_at: nowIso_() };
  cache.put(key, JSON.stringify(payload), CACHE_SECONDS);
  return respond_(payload, e);
}

function upsertLeaderboard_(sheet, data) {
  const lastRow = sheet.getLastRow();
  const values = lastRow > 1 ? sheet.getRange(2, 1, lastRow - 1, 7).getValues() : [];
  const key = data.class_code + '||' + data.student_key;
  const now = nowIso_();

  for (let i = 0; i < values.length; i++) {
    const rowKey = String(values[i][0] || '') + '||' + String(values[i][1] || '');
    if (rowKey === key) {
      const totalPoints = intOrZero_(values[i][3]) + data.score_award;
      const correctCount = intOrZero_(values[i][4]) + (data.correct ? 1 : 0);
      const attemptEvents = intOrZero_(values[i][5]) + 1;
      sheet.getRange(i + 2, 1, 1, 7).setValues([[
        data.class_code,
        data.student_key,
        data.display_name,
        totalPoints,
        correctCount,
        attemptEvents,
        now
      ]]);
      return;
    }
  }

  sheet.appendRow([
    data.class_code,
    data.student_key,
    data.display_name,
    data.score_award,
    data.correct ? 1 : 0,
    1,
    now
  ]);
}

function eventSeen_(sheet, eventId) {
  if (!eventId) return false;

  const cache = CacheService.getScriptCache();
  const hotKey = eventCacheKey_(eventId);
  if (cache.get(hotKey)) return true;

  const props = PropertiesService.getScriptProperties();
  const ledgerKey = 'recent_event_ids_v1';
  const maxRecent = 250;
  let recent = {};
  try {
    recent = JSON.parse(props.getProperty(ledgerKey) || '{}');
  } catch (err) {
    recent = {};
  }

  if (recent[eventId]) {
    cache.put(hotKey, '1', EVENT_DEDUPE_TTL_SECONDS);
    return true;
  }

  if (recentEventSeenByTail_(sheet, eventId, EVENT_TAIL_SCAN_ROWS)) {
    markEventSeen_(eventId, recent);
    return true;
  }

  return false;
}


function markEventSeen_(eventId, recentMapOpt) {
  if (!eventId) return;

  const cache = CacheService.getScriptCache();
  cache.put(eventCacheKey_(eventId), '1', EVENT_DEDUPE_TTL_SECONDS);

  const props = PropertiesService.getScriptProperties();
  const ledgerKey = 'recent_event_ids_v1';
  const maxRecent = 250;

  let recent = recentMapOpt;
  if (!recent) {
    try {
      recent = JSON.parse(props.getProperty(ledgerKey) || '{}');
    } catch (err) {
      recent = {};
    }
  }

  recent[eventId] = Date.now();

  const entries = Object.entries(recent)
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .slice(0, maxRecent);

  props.setProperty(ledgerKey, JSON.stringify(Object.fromEntries(entries)));
}

function recentEventSeenByTail_(sheet, eventId, tailSize) {
  const lastRow = sheet.getLastRow();
  if (lastRow <= 1) return false;

  const scanRows = Math.min(Math.max(tailSize, 1), lastRow - 1);
  const startRow = lastRow - scanRows + 1;
  const ids = sheet.getRange(startRow, 2, scanRows, 1).getValues();

  for (let i = 0; i < ids.length; i++) {
    if (String(ids[i][0] || '') === eventId) return true;
  }
  return false;
}

function eventCacheKey_(eventId) {
  return 'event_seen::' + eventId;
}



function leaderboardReadForClass_(sheet, classCode, limit) {
  const lastRow = sheet.getLastRow();
  if (lastRow <= 1) return [];

  const scanWindow = Math.min(lastRow - 1, LEADERBOARD_SCAN_MAX_ROWS);
  const startRow = Math.max(2, lastRow - scanWindow + 1);
  const values = sheet.getRange(startRow, 1, scanWindow, LEADERBOARD_HEADERS.length).getValues();

  const matched = [];
  for (let i = 0; i < values.length; i++) {
    const r = values[i];
    if (classCode && safe_(r[0]) !== classCode) continue;
    matched.push({
      class_code: safe_(r[0]),
      student_key: safe_(r[1]),
      display_name: safe_(r[2]),
      total_points: intOrZero_(r[3]),
      correct_count: intOrZero_(r[4]),
      attempt_events: intOrZero_(r[5]),
      last_seen_iso: safe_(r[6])
    });
  }

  matched.sort((a, b) =>
    b.total_points - a.total_points ||
    b.correct_count - a.correct_count ||
    a.display_name.localeCompare(b.display_name)
  );

  return matched.slice(0, limit);
}


function getOrCreateSheet_(ss, name, headers) {
  let sheet = ss.getSheetByName(name);
  if (!sheet) sheet = ss.insertSheet(name);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function respond_(payload, e) {
  const callback = safe_((e.parameter || {}).callback);
  if (callback) {
    return ContentService
      .createTextOutput(callback + '(' + JSON.stringify(payload) + ');')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}

function cacheKey_(classCode, limit) {
  return 'leaderboard::' + classCode + '::' + limit;
}

function nowIso_() {
  return new Date().toISOString();
}

function safe_(v) {
  return String(v == null ? '' : v).trim();
}

function sanitizeByPattern_(v, maxLen, pattern) {
  const raw = safe_(v).slice(0, maxLen);
  return raw.replace(pattern, '');
}

function sanitizeId_(v) {
  return sanitizeByPattern_(v, 80, /[^A-Za-z0-9._:-]/g);
}

function sanitizeClassCode_(v) {
  return sanitizeByPattern_(v, 40, /[^A-Za-z0-9 _.-]/g);
}

function sanitizeStudentKey_(v) {
  return sanitizeByPattern_(v, 60, /[^A-Za-z0-9._:-]/g);
}

function sanitizeDisplayName_(v) {
  return sanitizeByPattern_(v, 60, /[^A-Za-z0-9 _'.-]/g);
}

function sanitizeQuestionId_(v) {
  return sanitizeByPattern_(v, 40, /[^A-Za-z0-9._:-]/g);
}

function sanitizeEnumLike_(v, maxLen) {
  return sanitizeByPattern_(v, maxLen, /[^A-Za-z0-9_.:-]/g);
}

function sanitizeSource_(v) {
  return sanitizeByPattern_(v, 32, /[^A-Za-z0-9_.:-]/g);
}

function intOrZero_(v) {
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
}

function clampInt_(v, min, max) {
  const n = intOrZero_(v);
  return Math.min(Math.max(n, min), max);
}

function truthy_(v) {
  return String(v).toLowerCase() === 'true' || String(v) === '1';
}

function boolString_(v) {
  return truthy_(v) ? 'true' : 'false';
}
