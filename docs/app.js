'use strict';

/* ── Constants ── */
const PROGRESS_KEY = 'magyar_exam_progress';
const BASE_PATH    = location.pathname.replace(/\/[^/]*$/, '') || '';

/* ── State ── */
let QUESTIONS = [];
let progress  = { questions: {}, sessions: [], srs: {} };

let session = {
  mode: null,          // 'learn'|'quiz'|'mc'|'weak'|'srs'|'exam'
  topic: null,         // null = all topics
  cards: [],           // ordered question list for session
  idx: 0,
  score: 0,
  total: 0,
  hintUsed: false,
  revealed: false,     // learn mode reveal state
  examEnd: null,       // Date for exam timer
  timerHandle: null,
};

/* ══════════════════════════════════════════
   TEXT / SCORING HELPERS
══════════════════════════════════════════ */

function normalizeText(t) {
  if (!t) return '';
  return t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
}

function levenshtein(a, b) {
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, (_, i) => [i]);
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = a[i-1] === b[j-1]
        ? dp[i-1][j-1]
        : 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
    }
  }
  return dp[m][n];
}

function fuzzyMatch(input, keyword, threshold = 0.75) {
  const normIn  = normalizeText(input);
  const normKw  = normalizeText(keyword);
  if (normIn.includes(normKw)) return true;
  const words = normIn.split(/\s+/);
  const kwLen = normKw.split(/\s+/).length;
  for (let i = 0; i <= words.length - kwLen; i++) {
    const window = words.slice(i, i + kwLen).join(' ');
    const maxLen = Math.max(window.length, normKw.length);
    if (maxLen === 0) continue;
    const dist = levenshtein(window, normKw);
    if (1 - dist / maxLen >= threshold) return true;
  }
  return false;
}

function scoreAnswer(userInput, question) {
  const keywords = question.keywords_hu || [];
  if (keywords.length === 0) {
    // fall back to direct answer check
    const ok = fuzzyMatch(userInput, question.answer_hu, 0.65);
    return { score: ok ? 1 : 0, matched: ok ? [question.answer_hu] : [], missed: [] };
  }
  const matched = [], missed = [];
  for (const kw of keywords) {
    if (fuzzyMatch(userInput, kw)) matched.push(kw);
    else missed.push(kw);
  }
  const score = keywords.length ? matched.length / keywords.length : 0;
  return { score, matched, missed };
}

function maskKeyword(kw) {
  return kw.split(/\s+/).map(w => w[0] + '_'.repeat(Math.max(1, w.length - 1))).join(' ');
}

/* ── Question ID (stable hash) ── */
function questionId(q) {
  const s = (q.question_hu || '') + '|' + (q.topic || '');
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h) ^ s.charCodeAt(i);
  return 'q' + (h >>> 0).toString(16);
}

/* ══════════════════════════════════════════
   SRS — SM-2 ALGORITHM
══════════════════════════════════════════ */

function updateSRS(qid, quality) {
  // quality: 1=bad, 3=ok, 5=good  (maps to SM-2 q 0-5)
  const q2 = { 1: 1, 3: 3, 5: 5 }[quality] ?? quality;
  const entry = progress.srs[qid] ?? { interval: 1, ease: 2.5, due: null };

  if (q2 < 3) {
    entry.interval = 1;
  } else {
    if (!entry.due) entry.interval = 1;
    else if (entry.interval === 1) entry.interval = 4;
    else entry.interval = Math.round(entry.interval * entry.ease);
    entry.ease = Math.max(1.3, entry.ease + 0.1 - (5 - q2) * (0.08 + (5 - q2) * 0.02));
  }
  const due = new Date();
  due.setDate(due.getDate() + entry.interval);
  entry.due = due.toISOString().slice(0, 10);
  progress.srs[qid] = entry;
  saveProgress();
}

function getDueQuestions() {
  const today = new Date().toISOString().slice(0, 10);
  return QUESTIONS.filter(q => {
    const qid = questionId(q);
    const entry = progress.srs[qid];
    if (!entry || !entry.due) return false;
    return entry.due <= today;
  });
}

function srsQuality(score) {
  if (score >= 0.8) return 5;
  if (score >= 0.5) return 3;
  return 1;
}

function srsForDays(n) {
  const counts = Array(n).fill(0);
  const today  = new Date();
  for (const qid in progress.srs) {
    const entry = progress.srs[qid];
    if (!entry.due) continue;
    const due  = new Date(entry.due);
    const diff = Math.round((due - today) / 86400000);
    if (diff >= 0 && diff < n) counts[diff]++;
  }
  return counts;
}

/* ══════════════════════════════════════════
   PROGRESS — localStorage
══════════════════════════════════════════ */

function loadProgress() {
  try {
    const raw = localStorage.getItem(PROGRESS_KEY);
    if (raw) progress = JSON.parse(raw);
  } catch (_) {}
  progress.questions = progress.questions || {};
  progress.sessions  = progress.sessions  || [];
  progress.srs       = progress.srs       || {};
}

function saveProgress() {
  try { localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress)); } catch (_) {}
}

function recordAttempt(q, correct) {
  const qid = questionId(q);
  const rec = progress.questions[qid] ?? {
    attempts: 0, correct: 0, accuracy: 0,
    topic: q.topic, question_hu: q.question_hu
  };
  rec.attempts++;
  if (correct) rec.correct++;
  rec.accuracy = rec.correct / rec.attempts;
  rec.last_seen = new Date().toISOString().slice(0, 10);
  progress.questions[qid] = rec;
  saveProgress();
}

/* ══════════════════════════════════════════
   SCREEN MANAGEMENT
══════════════════════════════════════════ */

function showScreen(name) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const el = document.getElementById('screen-' + name);
  if (el) el.classList.add('active');
}

/* ══════════════════════════════════════════
   HOME
══════════════════════════════════════════ */

let selectedTopic = null;

function renderHome() {
  showScreen('home');

  // ── Banner ──
  const banner = document.getElementById('home-banner');
  const due    = getDueQuestions().length;
  if (due > 0) {
    banner.className = 'banner due';
    banner.textContent = `⏰ ${due} card${due !== 1 ? 's' : ''} due for SRS review`;
  } else if (Object.keys(progress.questions).length > 0) {
    banner.className = 'banner clear';
    banner.textContent = '✅ All SRS reviews done — great work!';
  } else {
    banner.className = 'banner';
    banner.textContent = '';
  }

  // ── Meta row ──
  const total    = Object.keys(progress.questions).length;
  const sessions = progress.sessions.length;
  document.getElementById('home-meta').innerHTML =
    `<span>Studied: <b>${total}</b> cards</span>
     <span>Sessions: <b>${sessions}</b></span>`;

  // ── Topic grid ──
  const topics = [...new Set(QUESTIONS.map(q => q.topic))].sort();
  const grid   = document.getElementById('topic-grid');
  grid.innerHTML = '';
  for (const t of topics) {
    const count = QUESTIONS.filter(q => q.topic === t).length;
    const chip  = document.createElement('button');
    chip.className = 'topic-chip' + (selectedTopic === t ? ' selected' : '');
    chip.innerHTML = `<div class="chip-num">${count} questions</div>
                      <div class="chip-name">${t}</div>`;
    chip.onclick = () => toggleTopic(t);
    grid.appendChild(chip);
  }

  // ── Selected label ──
  const lbl = document.getElementById('selected-topic-label');
  if (selectedTopic) {
    lbl.classList.remove('hidden');
    lbl.textContent = `Topic: ${selectedTopic}`;
  } else {
    lbl.classList.add('hidden');
  }

  // ── Forecast ──
  renderForecast();
}

function toggleTopic(t) {
  selectedTopic = (selectedTopic === t) ? null : t;
  renderHome();
}

function renderForecast() {
  const days   = srsForDays(7);
  const maxVal = Math.max(...days, 1);
  const labels = ['Today','Day 2','Day 3','Day 4','Day 5','Day 6','Day 7'];
  const colors = ['#58a6ff','#79b8ff','#85c1e9','#9fd3e9','#aee0f0','#b8e6f0','#c2ebf0'];
  const chart  = document.getElementById('forecast-chart');
  chart.innerHTML = days.map((n, i) => `
    <div class="forecast-row">
      <span class="forecast-label">${labels[i]}</span>
      <div class="forecast-bar-wrap">
        <div class="forecast-bar" style="width:${(n/maxVal*100).toFixed(1)}%;background:${colors[i]}"></div>
      </div>
      <span class="forecast-count">${n}</span>
    </div>`).join('');
}

/* ══════════════════════════════════════════
   LAUNCH MODE
══════════════════════════════════════════ */

function launchMode(mode) {
  // SRS and exam ignore topic filter
  if (mode === 'srs') { startSRS(); return; }
  if (mode === 'exam') { startExam(); return; }
  if (mode === 'weak') { startWeak(); return; }
  if (mode === 'learn') { startLearn(); return; }
  if (mode === 'mc')   { startMC();    return; }
  if (mode === 'quiz') { startQuiz();  return; }
}

function getPool() {
  if (selectedTopic) return QUESTIONS.filter(q => q.topic === selectedTopic);
  return [...QUESTIONS];
}

function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/* ══════════════════════════════════════════
   LEARN MODE
══════════════════════════════════════════ */

function startLearn() {
  const pool = shuffle(getPool());
  if (pool.length === 0) { alert('No questions for selected topic.'); return; }
  session = { mode: 'learn', topic: selectedTopic, cards: pool, idx: 0, score: 0, total: pool.length,
              hintUsed: false, revealed: false, examEnd: null, timerHandle: null };
  showScreen('learn');
  document.getElementById('learn-title').textContent =
    selectedTopic ? `Learn — ${selectedTopic}` : 'Learn — All Topics';
  showLearnCard();
}

function showLearnCard() {
  const q = session.cards[session.idx];
  session.revealed = false;

  document.getElementById('learn-counter').textContent =
    `${session.idx + 1} / ${session.total}`;
  document.getElementById('learn-diff').textContent =
    q.difficulty ? '★'.repeat(q.difficulty) + '☆'.repeat(3 - Math.min(q.difficulty, 3)) : '';

  document.getElementById('learn-question').innerHTML =
    `<span class="hu">${q.question_hu}</span>
     <span class="en">${q.question_en || ''}</span>`;

  document.getElementById('learn-divider').classList.add('hidden');
  document.getElementById('learn-answer').classList.add('hidden');
  document.getElementById('learn-keywords').classList.add('hidden');
  document.getElementById('learn-rating').classList.add('hidden');
  document.getElementById('learn-srs-note').classList.add('hidden');
  document.getElementById('learn-reveal-btn').classList.remove('hidden');
}

function revealLearnCard() {
  const q = session.cards[session.idx];
  session.revealed = true;

  document.getElementById('learn-divider').classList.remove('hidden');

  const ansEl = document.getElementById('learn-answer');
  ansEl.classList.remove('hidden');
  ansEl.innerHTML = `<span class="hu">${q.answer_hu}</span>
                     <span class="en">${q.answer_en || ''}</span>`;

  if (q.keywords_hu && q.keywords_hu.length) {
    const kwEl = document.getElementById('learn-keywords');
    kwEl.classList.remove('hidden');
    kwEl.innerHTML = 'Keywords: ' + q.keywords_hu.map(k => `<b>${k}</b>`).join(', ');
  }

  document.getElementById('learn-reveal-btn').classList.add('hidden');
  document.getElementById('learn-rating').classList.remove('hidden');
}

function rateLearnCard(quality) {
  // quality: 1=bad, 3=ok, 5=good
  const q   = session.cards[session.idx];
  const qid = questionId(q);
  updateSRS(qid, quality);
  recordAttempt(q, quality >= 4);

  const noteEl = document.getElementById('learn-srs-note');
  noteEl.classList.remove('hidden');
  const entry = progress.srs[qid];
  noteEl.textContent = `SRS: next review in ${entry.interval} day${entry.interval !== 1 ? 's' : ''}`;

  document.getElementById('learn-rating').classList.add('hidden');

  // advance after short delay
  setTimeout(() => {
    session.idx++;
    if (session.idx >= session.total) {
      finishSession();
    } else {
      showLearnCard();
    }
  }, 900);
}

/* ══════════════════════════════════════════
   QUIZ MODE
══════════════════════════════════════════ */

function startQuiz() {
  const pool = shuffle(getPool());
  if (pool.length === 0) { alert('No questions for selected topic.'); return; }
  session = { mode: 'quiz', topic: selectedTopic, cards: pool, idx: 0, score: 0, total: pool.length,
              hintUsed: false, revealed: false, examEnd: null, timerHandle: null };
  showScreen('quiz');
  document.getElementById('quiz-title').textContent =
    selectedTopic ? `Quiz — ${selectedTopic}` : 'Quiz — All Topics';
  document.getElementById('quiz-exam-timer').classList.add('hidden');
  showQuizQuestion();
}

function startExam() {
  const pool = shuffle([...QUESTIONS]).slice(0, 30);
  const end  = new Date(Date.now() + 45 * 60 * 1000); // 45 min
  session = { mode: 'exam', topic: null, cards: pool, idx: 0, score: 0, total: pool.length,
              hintUsed: false, revealed: false, examEnd: end, timerHandle: null };
  showScreen('quiz');
  document.getElementById('quiz-title').textContent = 'Exam Simulation';
  document.getElementById('quiz-exam-timer').classList.remove('hidden');
  startExamTimer();
  showQuizQuestion();
}

function startExamTimer() {
  if (session.timerHandle) clearInterval(session.timerHandle);
  session.timerHandle = setInterval(() => {
    const rem  = Math.max(0, session.examEnd - Date.now());
    const mins = Math.floor(rem / 60000);
    const secs = Math.floor((rem % 60000) / 1000);
    const el   = document.getElementById('quiz-exam-timer');
    el.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
    if (rem <= 0) {
      clearInterval(session.timerHandle);
      finishSession();
    } else if (rem < 5 * 60000) el.className = 'exam-timer urgent';
    else if (rem < 15 * 60000) el.className = 'exam-timer warn';
    else el.className = 'exam-timer ok';
  }, 500);
}

function showQuizQuestion() {
  const q = session.cards[session.idx];
  session.hintUsed = false;

  document.getElementById('quiz-counter').textContent =
    `${session.idx + 1} / ${session.total}`;
  document.getElementById('quiz-diff').textContent =
    q.difficulty ? '★'.repeat(q.difficulty) + '☆'.repeat(3 - Math.min(q.difficulty, 3)) : '';
  document.getElementById('quiz-question').innerHTML =
    `<span class="hu">${q.question_hu}</span>
     <span class="en">${q.question_en || ''}</span>`;

  const input = document.getElementById('quiz-input');
  input.value = '';
  input.disabled = false;
  input.focus();

  document.getElementById('quiz-submit-btn').classList.remove('hidden');
  document.getElementById('quiz-hint-btn').classList.remove('hidden');
  document.getElementById('quiz-feedback').classList.add('hidden');
  document.getElementById('quiz-next-btn').classList.add('hidden');
}

function showQuizHint() {
  const q = session.cards[session.idx];
  session.hintUsed = true;
  document.getElementById('quiz-hint-btn').classList.add('hidden');
  const fb = document.getElementById('quiz-feedback');
  fb.classList.remove('hidden');
  const hints = (q.keywords_hu || []).map(maskKeyword).join(', ');
  fb.innerHTML = `<div class="hint-text">Hint: ${hints || maskKeyword(q.answer_hu)}</div>`;
}

function submitQuizAnswer() {
  const q     = session.cards[session.idx];
  const input = document.getElementById('quiz-input');
  const raw   = input.value.trim();
  if (!raw) { input.focus(); return; }

  input.disabled = true;
  document.getElementById('quiz-submit-btn').classList.add('hidden');
  document.getElementById('quiz-hint-btn').classList.add('hidden');

  const { score, matched, missed } = scoreAnswer(raw, q);
  const penalty  = session.hintUsed ? 0.8 : 1;
  const adjusted = score * penalty;
  session.score += adjusted;

  const correct = adjusted >= 0.5;
  recordAttempt(q, correct);
  if (session.mode !== 'exam') {
    updateSRS(questionId(q), srsQuality(adjusted));
  }

  const fb = document.getElementById('quiz-feedback');
  fb.classList.remove('hidden');
  let html = '';
  if (adjusted >= 0.8)      html += `<div class="result-line correct">✅ Correct! (${Math.round(adjusted*100)}%)</div>`;
  else if (adjusted >= 0.5) html += `<div class="result-line partial">🤔 Partial (${Math.round(adjusted*100)}%)</div>`;
  else                      html += `<div class="result-line wrong">❌ Incorrect (${Math.round(adjusted*100)}%)</div>`;

  html += `<div class="answer-hu">Answer: ${q.answer_hu}</div>`;
  if (q.answer_en) html += `<div class="answer-en">${q.answer_en}</div>`;

  if (matched.length) html += `<div class="matched">✓ ${matched.join(', ')}</div>`;
  if (missed.length)  html += `<div class="missed">✗ ${missed.join(', ')}</div>`;
  if (session.hintUsed) html += `<div class="srs-line">Hint used → ×0.8 penalty</div>`;
  fb.innerHTML = html;

  document.getElementById('quiz-next-btn').classList.remove('hidden');
}

function nextQuizQuestion() {
  session.idx++;
  if (session.idx >= session.total) finishSession();
  else showQuizQuestion();
}

/* ══════════════════════════════════════════
   MULTIPLE CHOICE
══════════════════════════════════════════ */

function startMC() {
  const pool = shuffle(getPool());
  if (pool.length < 4) { alert('Need at least 4 questions for Multiple Choice.'); return; }
  session = { mode: 'mc', topic: selectedTopic, cards: pool, idx: 0, score: 0, total: pool.length,
              hintUsed: false, revealed: false, examEnd: null, timerHandle: null };
  showScreen('mc');
  showMCQuestion();
}

function buildMCOptions(q) {
  const pool    = QUESTIONS.filter(x => questionId(x) !== questionId(q));
  const wrongs  = shuffle(pool).slice(0, 3).map(x => x.answer_hu);
  const options = shuffle([q.answer_hu, ...wrongs]);
  return options;
}

function showMCQuestion() {
  const q = session.cards[session.idx];

  document.getElementById('mc-counter').textContent =
    `${session.idx + 1} / ${session.total}`;
  document.getElementById('mc-diff').textContent =
    q.difficulty ? '★'.repeat(q.difficulty) + '☆'.repeat(3 - Math.min(q.difficulty, 3)) : '';
  document.getElementById('mc-question').innerHTML =
    `<span class="hu">${q.question_hu}</span>
     <span class="en">${q.question_en || ''}</span>`;

  const opts    = buildMCOptions(q);
  const optDiv  = document.getElementById('mc-options');
  const labels  = ['A', 'B', 'C', 'D'];
  optDiv.innerHTML = opts.map((o, i) => `
    <button class="mc-opt" onclick="pickMCOption(${i})">
      <span class="opt-label">${labels[i]}.</span>${o}
    </button>`).join('');

  // store correct index for later
  optDiv.dataset.correct = opts.indexOf(q.answer_hu);
  optDiv.dataset.answer  = q.answer_hu;

  document.getElementById('mc-feedback').classList.add('hidden');
  document.getElementById('mc-next-btn').classList.add('hidden');
}

function pickMCOption(idx) {
  const q       = session.cards[session.idx];
  const optDiv  = document.getElementById('mc-options');
  const correct = parseInt(optDiv.dataset.correct);
  const btns    = optDiv.querySelectorAll('.mc-opt');

  btns.forEach(b => b.disabled = true);
  btns[correct].classList.add('correct');
  if (idx !== correct) btns[idx].classList.add('wrong');

  const isCorrect = idx === correct;
  if (isCorrect) session.score++;
  recordAttempt(q, isCorrect);
  updateSRS(questionId(q), isCorrect ? 5 : 1);

  const fb = document.getElementById('mc-feedback');
  fb.classList.remove('hidden');
  fb.innerHTML = isCorrect
    ? `<span class="correct">✅ Correct!</span>`
    : `<span class="wrong">❌ The answer was: <b>${optDiv.dataset.answer}</b></span>`;

  document.getElementById('mc-next-btn').classList.remove('hidden');
}

function nextMCQuestion() {
  session.idx++;
  if (session.idx >= session.total) finishSession();
  else showMCQuestion();
}

/* ══════════════════════════════════════════
   WEAK SPOTS
══════════════════════════════════════════ */

function startWeak() {
  // Questions with accuracy < 60% or never tried (not in progress)
  const seen = progress.questions;
  let pool = QUESTIONS.filter(q => {
    const rec = seen[questionId(q)];
    if (!rec) return false; // not seen yet
    return rec.accuracy < 0.6;
  });
  if (pool.length === 0) {
    alert('No weak spots yet! Study some cards first, or you\'re doing great.');
    return;
  }
  pool = shuffle(pool);
  session = { mode: 'weak', topic: null, cards: pool, idx: 0, score: 0, total: pool.length,
              hintUsed: false, revealed: false, examEnd: null, timerHandle: null };
  showScreen('quiz');
  document.getElementById('quiz-title').textContent = 'Weak Spots';
  document.getElementById('quiz-exam-timer').classList.add('hidden');
  showQuizQuestion();
}

/* ══════════════════════════════════════════
   SRS REVIEW
══════════════════════════════════════════ */

function startSRS() {
  const pool = shuffle(getDueQuestions());
  if (pool.length === 0) {
    alert('No cards due for review! Check back later.');
    return;
  }
  session = { mode: 'srs', topic: null, cards: pool, idx: 0, score: 0, total: pool.length,
              hintUsed: false, revealed: false, examEnd: null, timerHandle: null };
  showScreen('learn');
  document.getElementById('learn-title').textContent = 'SRS Review';
  showLearnCard();
}

/* ══════════════════════════════════════════
   SESSION FINISH
══════════════════════════════════════════ */

function finishSession() {
  if (session.timerHandle) clearInterval(session.timerHandle);

  const pct    = session.total > 0 ? session.score / session.total : 0;
  const passed = pct >= 0.6;
  const grade  = Math.round(pct * 100);

  // record session
  progress.sessions.push({
    date:  new Date().toISOString().slice(0, 10),
    mode:  session.mode,
    topic: session.topic,
    score: grade,
    total: session.total,
  });
  saveProgress();

  const modeLabel = { learn:'Learn', quiz:'Quiz', mc:'Multiple Choice',
                      weak:'Weak Spots', srs:'SRS Review', exam:'Exam' }[session.mode] || session.mode;

  const content = document.getElementById('result-content');
  content.innerHTML = `
    <div style="font-size:14px;color:var(--muted)">${modeLabel}${session.topic ? ' — ' + session.topic : ''}</div>
    <div class="big-score" style="color:${passed ? 'var(--green)' : 'var(--red)'}">
      ${grade}%
    </div>
    <div class="verdict ${passed ? 'pass' : 'fail'}">${passed ? '🎉 Passed!' : '📚 Keep Studying'}</div>
    <div style="font-size:15px;color:var(--muted)">${session.total} questions</div>
  `;

  showScreen('result');
}

/* ══════════════════════════════════════════
   STATS
══════════════════════════════════════════ */

function showStats() {
  const content = document.getElementById('stats-content');
  content.innerHTML = '';

  // ── Overall ──
  const allRecs  = Object.values(progress.questions);
  const studied  = allRecs.length;
  const avgAcc   = studied ? allRecs.reduce((s, r) => s + r.accuracy, 0) / studied : 0;
  const sessions = progress.sessions.length;
  const dueCount = getDueQuestions().length;

  content.innerHTML += `
  <div class="stat-block">
    <h3>Overall</h3>
    <div class="stat-row"><span>Cards studied</span><span class="val">${studied} / ${QUESTIONS.length}</span></div>
    <div class="stat-row"><span>Average accuracy</span>
      <span class="val ${avgAcc >= 0.8 ? 'good' : avgAcc >= 0.5 ? 'warn' : 'bad'}">${Math.round(avgAcc*100)}%</span></div>
    <div class="stat-row"><span>Sessions</span><span class="val">${sessions}</span></div>
    <div class="stat-row"><span>SRS due</span><span class="val ${dueCount > 0 ? 'warn' : 'good'}">${dueCount}</span></div>
  </div>`;

  // ── Per-topic ──
  const topics = [...new Set(QUESTIONS.map(q => q.topic))].sort();
  let topicHtml = '<div class="stat-block"><h3>By Topic</h3>';
  for (const t of topics) {
    const qs    = QUESTIONS.filter(q => q.topic === t);
    const recs  = qs.map(q => progress.questions[questionId(q)]).filter(Boolean);
    const acc   = recs.length ? recs.reduce((s, r) => s + r.accuracy, 0) / recs.length : 0;
    const seen  = recs.length;
    const pct   = Math.round(acc * 100);
    const color = acc >= 0.8 ? 'var(--green)' : acc >= 0.5 ? 'var(--yellow)' : 'var(--red)';
    topicHtml += `
    <div class="acc-row">
      <span class="acc-label" style="width:auto;min-width:0;flex:1;font-size:12px">${t} (${seen}/${qs.length})</span>
      <div class="acc-bar-wrap" style="min-width:60px;max-width:120px">
        <div class="acc-bar" style="width:${pct}%;background:${color}"></div>
      </div>
      <span class="acc-pct" style="color:${color}">${pct}%</span>
    </div>`;
  }
  topicHtml += '</div>';
  content.innerHTML += topicHtml;

  // ── Recent sessions ──
  const recent = [...progress.sessions].reverse().slice(0, 10);
  if (recent.length) {
    let sesHtml = '<div class="stat-block"><h3>Recent Sessions</h3>';
    for (const s of recent) {
      const cl = s.score >= 80 ? 'good' : s.score >= 60 ? 'warn' : 'bad';
      sesHtml += `<div class="stat-row">
        <span>${s.date} ${s.mode}${s.topic ? ' — ' + s.topic : ''}</span>
        <span class="val ${cl}">${s.score}%</span>
      </div>`;
    }
    sesHtml += '</div>';
    content.innerHTML += sesHtml;
  }

  showScreen('stats');
}

/* ══════════════════════════════════════════
   GO HOME
══════════════════════════════════════════ */

function goHome() {
  if (session.timerHandle) clearInterval(session.timerHandle);
  renderHome();
}

/* ══════════════════════════════════════════
   INIT
══════════════════════════════════════════ */

async function init() {
  loadProgress();

  try {
    const resp = await fetch('questions.json');
    if (!resp.ok) throw new Error('Failed to load questions.json');
    const data = await resp.json();
    QUESTIONS  = Array.isArray(data) ? data : (data.questions || []);
  } catch (err) {
    console.error(err);
    document.querySelector('#screen-loading .splash p').textContent =
      'Error loading questions. Please refresh.';
    document.querySelector('#screen-loading .spinner').style.display = 'none';
    return;
  }

  renderHome();
}

document.addEventListener('DOMContentLoaded', init);

/* ── Service Worker ── */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  });
}
