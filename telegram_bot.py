#!/usr/bin/env python3
"""
Hungarian Cultural Knowledge Exam - Telegram Study Bot
"""

import json, os, sys, random, hashlib, difflib, datetime
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    PicklePersistence, ContextTypes, filters,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.path.join(BASE_DIR, "questions.json")
PERSISTENCE_FILE = os.path.join(BASE_DIR, "bot_persistence.pkl")

TOPIC_NAMES: dict[int, str] = {
    1: "Nemzeti jelképek és ünnepek",
    2: "Magyar történelem",
    3: "Irodalom és zene",
    4: "Alaptörvény és intézmények",
    5: "Állampolgári jogok",
    6: "Mindennapi Magyarország",
}

TOPIC_EMOJI: dict[int, str] = {
    1: "🏛", 2: "📜", 3: "🎵",
    4: "⚖", 5: "🗳", 6: "🇭🇺",
}

EXAM_PASS_THRESHOLD = 16.0
EXAM_MAX_POINTS = 30.0
WEAK_THRESHOLD = 0.60
ACCENT_MAP = str.maketrans({
    "\u00e1": "a", "\u00c1": "A",
    "\u00e9": "e", "\u00c9": "E",
    "\u00ed": "i", "\u00cd": "I",
    "\u00f3": "o", "\u00d3": "O",
    "\u00f6": "o", "\u00d6": "O",
    "\u0151": "o", "\u0150": "O",
    "\u00fa": "u", "\u00da": "U",
    "\u00fc": "u", "\u00dc": "U",
    "\u0171": "u", "\u0170": "U",
})


def normalize_text(text):
    """Remove accents and lowercase text for comparison purposes."""
    return text.translate(ACCENT_MAP).lower().strip()


def question_id(question_hu):
    """Generate a stable ID for a question using MD5 hash of the Hungarian text."""
    return hashlib.md5(question_hu.encode("utf-8")).hexdigest()


def fuzzy_match(user_input, keyword, threshold=0.75):
    """
    Check whether *keyword* appears in *user_input* using fuzzy matching.

    Strategy:
    1. Exact substring match (after accent-normalisation) -- instant pass.
    2. Sliding-window fuzzy match using difflib.SequenceMatcher.
       The window slides over the user input in word-sized chunks and also
       in character-sized chunks equal to the keyword length +/- 3.

    Returns True if a sufficiently close match is found.
    """
    norm_input = normalize_text(user_input)
    norm_kw = normalize_text(keyword)

    # Exact substring
    if norm_kw in norm_input:
        return True

    # Word-level check
    input_words = norm_input.split()
    kw_words = norm_kw.split()

    # Single-word keyword: check against each input word
    if len(kw_words) == 1:
        for word in input_words:
            ratio = difflib.SequenceMatcher(None, word, norm_kw).ratio()
            if ratio >= threshold:
                return True

    # Multi-word keyword: sliding window of same word count
    if len(kw_words) > 1:
        for i in range(len(input_words) - len(kw_words) + 1):
            window = " ".join(input_words[i : i + len(kw_words)])
            ratio = difflib.SequenceMatcher(None, window, norm_kw).ratio()
            if ratio >= threshold:
                return True

    # Character-level sliding window
    kw_len = len(norm_kw)
    for window_size in range(max(1, kw_len - 3), kw_len + 4):
        for i in range(len(norm_input) - window_size + 1):
            chunk = norm_input[i : i + window_size]
            ratio = difflib.SequenceMatcher(None, chunk, norm_kw).ratio()
            if ratio >= threshold:
                return True

    return False


def score_answer(user_input, keywords):
    """
    Score the user's answer against the list of expected keywords.

    Returns:
        (score, matched_list, missed_list)
        where score is a float between 0.0 and 1.0
    """
    if not keywords:
        return (1.0, [], [])

    matched = []
    missed = []

    for kw in keywords:
        if fuzzy_match(user_input, kw):
            matched.append(kw)
        else:
            missed.append(kw)

    score = len(matched) / len(keywords)
    return (score, matched, missed)


# --- SRS helpers (SM-2 algorithm) ---

def srs_quality(score: float) -> int:
    """Convert 0-1 score to SM-2 quality rating (0-5)."""
    if score >= 0.9: return 5
    elif score >= 0.75: return 4
    elif score >= 0.6: return 3
    elif score >= 0.4: return 2
    elif score >= 0.2: return 1
    return 0


def update_srs(progress: dict, qid: str, quality: int) -> None:
    """Update SRS scheduling using the SM-2 algorithm."""
    srs = progress.setdefault("srs", {})
    card = srs.setdefault(qid, {"interval": 1, "repetitions": 0, "easiness": 2.5, "due": None})
    ef = card["easiness"] + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    card["easiness"] = max(1.3, ef)
    if quality < 3:
        card["repetitions"] = 0
        card["interval"] = 1
    else:
        reps = card["repetitions"]
        if reps == 0: card["interval"] = 1
        elif reps == 1: card["interval"] = 6
        else: card["interval"] = round(card["interval"] * card["easiness"])
        card["repetitions"] += 1
    due = datetime.date.today() + datetime.timedelta(days=card["interval"])
    card["due"] = due.isoformat()


def get_due_questions(progress: dict, questions: list) -> list:
    """Return questions due for SRS review today, including unseen cards."""
    srs = progress.get("srs", {})
    today = datetime.date.today().isoformat()
    due_ids = {qid for qid, card in srs.items() if card.get("due", "0000-00-00") <= today}
    seen_ids = set(srs.keys())
    result = []
    for q in questions:
        qid = question_id(q["question_hu"])
        if qid in due_ids or qid not in seen_ids:
            result.append(q)
    return result


# --- Progress helpers ---

def init_progress() -> dict:
    return {"questions": {}, "sessions": [], "srs": {}, "vocab": {}}


def init_user_data() -> dict:
    return {
        "state": "home", "selected_topic": None,
        "session": {
            "mode": None, "questions": [], "idx": 0,
            "score": 0.0, "options": [], "hint_used": False, "revealed": False,
        },
        "progress": init_progress(),
    }


def record_attempt(progress: dict, q: dict, score: float) -> None:
    qid = question_id(q["question_hu"])
    entry = progress["questions"].setdefault(qid, {
        "attempts": 0, "correct": 0, "last_seen": None,
        "accuracy": 0.0, "question_hu": q["question_hu"], "topic": q["topic"],
    })
    entry["attempts"] += 1
    if score >= 0.6: entry["correct"] += 1
    entry["last_seen"] = datetime.datetime.now().isoformat()
    entry["accuracy"] = entry["correct"] / entry["attempts"]


def record_session(progress: dict, mode: str, score: float, total: int, topic=None) -> None:
    sess: dict = {"date": datetime.datetime.now().isoformat(), "mode": mode, "score": score, "total": total}
    if topic is not None: sess["topic"] = topic
    progress["sessions"].append(sess)


def get_questions_for_topic(questions: list, topic: int) -> list:
    return [q for q in questions if q.get("topic") == topic]


def get_weak_questions(progress: dict, questions: list) -> list:
    pq = progress.get("questions", {})
    return [
        q for q in questions
        if (lambda e: e is None or e.get("accuracy", 0.0) < WEAK_THRESHOLD)(pq.get(question_id(q["question_hu"])))
    ]

# --- Keyboard builders ---

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Learn", callback_data="mode:learn"),
         InlineKeyboardButton("🔢 M-Choice", callback_data="mode:mc")],
        [InlineKeyboardButton("❓ Quiz", callback_data="mode:quiz"),
         InlineKeyboardButton("⚠ Weak Spots", callback_data="mode:weak")],
        [InlineKeyboardButton("⏰ SRS Review", callback_data="mode:srs"),
         InlineKeyboardButton("📝 Mock Exam", callback_data="mode:exam")],
        [InlineKeyboardButton("📊 Statistics", callback_data="mode:stats")],
    ])


def topic_keyboard(mode: str) -> InlineKeyboardMarkup:
    rows = []
    topics = list(TOPIC_NAMES.items())
    for i in range(0, len(topics), 2):
        row = []
        for tid, _ in topics[i:i+2]:
            row.append(InlineKeyboardButton(
                f"{TOPIC_EMOJI[tid]} T{tid}", callback_data=f"topic:{mode}:{tid}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("« Back", callback_data="back:home")])
    return InlineKeyboardMarkup(rows)


def reveal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👁 Reveal Answer", callback_data="learn:reveal")
    ]])


def rating_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("1 ✗ Didn’t know", callback_data="learn:rate:1"),
        InlineKeyboardButton("2 ~ Almost", callback_data="learn:rate:2"),
        InlineKeyboardButton("3 ✓ Got it!", callback_data="learn:rate:3"),
    ]])


def next_keyboard(cb: str = "next") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Next →", callback_data=cb)]])


def hint_next_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💡 Hint (-20%)", callback_data="quiz:hint"),
        InlineKeyboardButton("⏭ Skip", callback_data="quiz:skip"),
    ]])


# --- Message formatters ---

def format_question_text(q: dict, idx: int, total: int, mode_label: str = "") -> str:
    label = f" | {mode_label}" if mode_label else ""
    tn = q["topic"]
    return (
        f"<b>Question {idx + 1}/{total}{label}</b>\n"
        f"<i>Topic {tn}: {TOPIC_NAMES[tn]}</i>\n\n"
        f"<b>{q['question_hu']}</b>\n"
        f"<i>{q['question_en']}</i>"
    )


def format_answer_text(q: dict) -> str:
    kws = q.get("keywords_hu", [])
    kw_str = " | ".join(f"<code>{k}</code>" for k in kws) if kws else "<i>none</i>"
    ans_hu = q.get("answer_hu", "")
    ans_en = q.get("answer_en", "")
    return (
        f"\n\n<b>Answer:</b> {ans_hu}\n"
        f"<i>{ans_en}</i>\n\n"
        f"<b>Keywords:</b> {kw_str}"
    )


def format_score_bar(ratio: float, width: int = 10) -> str:
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


WELCOME_TEXT = (
    "<b>Magyar Kultúrális Ismereti Vizsga</b>\n"
    "<i>Hungarian Cultural Knowledge Exam Study Bot</i>\n\n"
    "Choose a study mode below:"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data: context.user_data.update(init_user_data())
    elif "progress" not in context.user_data: context.user_data["progress"] = init_progress()
    context.user_data["state"] = "home"
    await update.message.reply_text(WELCOME_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data: context.user_data.update(init_user_data())
    await send_statistics(update.message.reply_text, context)


async def send_statistics(reply_fn, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud = context.user_data
    progress = ud.get("progress", init_progress())
    sessions = progress.get("sessions", [])
    pq = progress.get("questions", {})
    dates = sorted({s["date"][:10] for s in sessions}, reverse=True)
    streak, today = 0, datetime.date.today()
    for i, d in enumerate(dates):
        if d == (today - datetime.timedelta(days=i)).isoformat(): streak += 1
        else: break
    topic_lines = []
    for tid in range(1, 7):
        entries = [e for e in pq.values() if e.get("topic") == tid]
        if entries:
            avg_acc = sum(e["accuracy"] for e in entries) / len(entries)
            topic_lines.append(f"T{tid} {TOPIC_EMOJI[tid]} {format_score_bar(avg_acc)} {avg_acc:.0%}")
        else:
            topic_lines.append(f"T{tid} {TOPIC_EMOJI[tid]} ░░░░░░░░░░ no data")
    all_q: list = context.bot_data.get("questions", [])
    srs_due = len(get_due_questions(progress, all_q))
    out = [
        "<b>📊 Your Statistics</b>\n",
        f"Sessions: <b>{len(sessions)}</b>",
        f"Streak: <b>{streak} day(s)</b>",
        f"Questions tracked: <b>{len(pq)}</b>",
        f"SRS due today: <b>{srs_due}</b>\n",
        "<b>Topic Accuracy:</b>",
    ] + topic_lines
    await reply_fn("\n".join(out), parse_mode="HTML", reply_markup=main_menu_keyboard())


def start_session(ud: dict, mode: str, questions: list) -> None:
    random.shuffle(questions)
    ud["session"] = {"mode": mode, "questions": questions, "idx": 0,
                     "score": 0.0, "options": [], "hint_used": False, "revealed": False}
    ud["state"] = mode


async def send_learn_card(reply_fn, ud: dict) -> None:
    sess = ud["session"]
    q = sess["questions"][sess["idx"]]
    sess["revealed"] = False
    await reply_fn(format_question_text(q, sess["idx"], len(sess["questions"]), "Learn"),
                   reply_markup=reveal_keyboard(), parse_mode="HTML")


async def send_mc_question(reply_fn, ud: dict, all_questions: list) -> None:
    sess = ud["session"]
    idx = sess["idx"]
    q = sess["questions"][idx]
    correct_ans = q["answer_hu"]
    wrong_pool = [x["answer_hu"] for x in all_questions if x["answer_hu"] != correct_ans]
    opts = random.sample(wrong_pool, min(3, len(wrong_pool))) + [correct_ans]
    random.shuffle(opts)
    sess["options"] = opts
    text = format_question_text(q, idx, len(sess["questions"]), "Multiple Choice")
    labels = ["A", "B", "C", "D"]
    buttons = [[InlineKeyboardButton(
        f"{labels[i]}) {opt[:50] + (chr(8230) if len(opt) > 50 else chr(8203))}",
        callback_data=f"mc:answer:{i}")] for i, opt in enumerate(opts)]
    await reply_fn(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


async def send_quiz_question(reply_fn, ud: dict) -> None:
    sess = ud["session"]
    idx = sess["idx"]
    q = sess["questions"][idx]
    sess["hint_used"] = False
    text = format_question_text(q, idx, len(sess["questions"]), "Quiz") + "\n\n<i>Type your answer below...</i>"
    await reply_fn(text, reply_markup=hint_next_keyboard(), parse_mode="HTML")


async def finish_quiz(reply_fn, ud: dict, context: ContextTypes.DEFAULT_TYPE) -> None:
    sess = ud["session"]
    total = len(sess["questions"])
    avg = sess["score"] / total if total > 0 else 0.0
    record_session(ud["progress"], "quiz", avg, total, ud.get("selected_topic"))
    ud["state"] = "home"
    await reply_fn(f"<b>🎯 Quiz Complete!</b>\n\nQuestions: <b>{total}</b>\nScore: <b>{avg:.0%}</b>",
                   reply_markup=main_menu_keyboard(), parse_mode="HTML")


async def finish_exam(reply_fn, ud: dict) -> None:
    sess = ud["session"]
    total = len(sess["questions"])
    points = (sess["score"] / total * EXAM_MAX_POINTS) if total > 0 else 0.0
    passed = points >= EXAM_PASS_THRESHOLD
    record_session(ud["progress"], "exam", points, int(EXAM_MAX_POINTS))
    ud["state"] = "home"
    verdict = "✅ <b>PASSED — MEGFELELT</b>" if passed else "❌ <b>FAILED — NEM FELELT MEG</b>"
    msg = (f"<b>📝 Mock Exam Results</b>\n\n"
           f"Score: <b>{points:.1f} / {EXAM_MAX_POINTS:.0f} points</b>\n"
           f"Questions: {total} (2 per topic)\n"
           f"Pass: {EXAM_PASS_THRESHOLD:.0f} pts needed\n\n{verdict}")
    if not passed:
        msg += f"\n<i>You needed {EXAM_PASS_THRESHOLD:.0f} pts, got {points:.1f}. Keep studying!</i>"
    await reply_fn(msg, reply_markup=main_menu_keyboard(), parse_mode="HTML")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not context.user_data: context.user_data.update(init_user_data())
    elif "progress" not in context.user_data: context.user_data["progress"] = init_progress()
    ud = context.user_data
    all_q: list = context.bot_data.get("questions", [])
    data = query.data

    if data.startswith("mode:"):
        mode = data.split(":")[1]
        if mode in ("learn", "quiz", "mc"):
            label = {"learn": "Learn", "quiz": "Quiz", "mc": "Multiple Choice"}[mode]
            await query.edit_message_text(f"Select a topic for <b>{label}</b> mode:",
                                           reply_markup=topic_keyboard(mode), parse_mode="HTML")
        elif mode == "weak":
            qs = get_weak_questions(ud["progress"], all_q)
            if not qs:
                await query.edit_message_text("🎉 No weak spots! You are doing great!",
                                               reply_markup=main_menu_keyboard())
                return
            start_session(ud, "quiz", qs)
            await send_quiz_question(query.edit_message_text, ud)
        elif mode == "srs":
            qs = get_due_questions(ud["progress"], all_q)
            if not qs:
                await query.edit_message_text("⏰ No SRS cards due today! Check back tomorrow.",
                                               reply_markup=main_menu_keyboard())
                return
            random.shuffle(qs)
            start_session(ud, "learn", qs[:50])
            await send_learn_card(query.edit_message_text, ud)
        elif mode == "exam":
            exam_qs = []
            for t in range(1, 7):
                tqs = get_questions_for_topic(all_q, t)
                exam_qs.extend(random.sample(tqs, 2) if len(tqs) >= 2 else tqs)
            random.shuffle(exam_qs)
            start_session(ud, "exam", exam_qs)
            await send_quiz_question(query.edit_message_text, ud)
        elif mode == "stats":
            await send_statistics(query.edit_message_text, context)

    elif data.startswith("topic:"):
        _, mode, tid_str = data.split(":")
        tid = int(tid_str)
        ud["selected_topic"] = tid
        qs = get_questions_for_topic(all_q, tid)
        if not qs:
            await query.edit_message_text("No questions for that topic.", reply_markup=main_menu_keyboard())
            return
        start_session(ud, mode, list(qs))
        if mode == "learn": await send_learn_card(query.edit_message_text, ud)
        elif mode == "mc": await send_mc_question(query.edit_message_text, ud, all_q)
        elif mode == "quiz": await send_quiz_question(query.edit_message_text, ud)

    elif data.startswith("back:"):
        ud["state"] = "home"
        await query.edit_message_text(WELCOME_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")

    elif data == "learn:reveal":
        sess = ud["session"]
        idx = sess["idx"]
        q = sess["questions"][idx]
        sess["revealed"] = True
        await query.edit_message_text(
            format_question_text(q, idx, len(sess["questions"]), "Learn") + format_answer_text(q),
            reply_markup=rating_keyboard(), parse_mode="HTML")

    elif data.startswith("learn:rate:"):
        rating = int(data.split(":")[2])
        sess = ud["session"]
        idx = sess["idx"]
        q = sess["questions"][idx]
        score = (rating - 1) / 2.0
        update_srs(ud["progress"], question_id(q["question_hu"]), srs_quality(score))
        record_attempt(ud["progress"], q, score)
        sess["score"] += score
        sess["idx"] += 1
        if sess["idx"] >= len(sess["questions"]):
            total = len(sess["questions"])
            avg = sess["score"] / total if total > 0 else 0.0
            record_session(ud["progress"], "learn", avg, total, ud.get("selected_topic"))
            ud["state"] = "home"
            await query.edit_message_text(
                f"<b>🎉 Session Complete!</b>\n\nCards: <b>{total}</b>  Avg: <b>{avg:.0%}</b>",
                reply_markup=main_menu_keyboard(), parse_mode="HTML")
        else:
            await send_learn_card(query.edit_message_text, ud)

    elif data.startswith("mc:answer:"):
        choice = int(data.split(":")[2])
        sess = ud["session"]
        idx = sess["idx"]
        q = sess["questions"][idx]
        opts = sess["options"]
        correct_ans = q["answer_hu"]
        is_correct = opts[choice] == correct_ans
        correct_idx = opts.index(correct_ans)
        labels = ["A", "B", "C", "D"]
        score = 1.0 if is_correct else 0.0
        sess["score"] += score
        record_attempt(ud["progress"], q, score)
        update_srs(ud["progress"], question_id(q["question_hu"]), srs_quality(score))
        icon = "✅" if is_correct else "❌"
        verdict = "Correct!" if is_correct else "Wrong!"
        feedback = f"{icon} <b>{verdict}</b>"
        if not is_correct: feedback += f"\nCorrect: <b>{labels[correct_idx]}) {correct_ans}</b>"
        text = format_question_text(q, idx, len(sess["questions"]), "Multiple Choice") + f"\n\n{feedback}"
        await query.edit_message_text(text, reply_markup=next_keyboard("mc:next"), parse_mode="HTML")

    elif data == "mc:next":
        sess = ud["session"]
        sess["idx"] += 1
        if sess["idx"] >= len(sess["questions"]):
            total = len(sess["questions"])
            sc = sess["score"]
            pct = int(sc / total * 100) if total > 0 else 0
            record_session(ud["progress"], "mc", sc, total, ud.get("selected_topic"))
            ud["state"] = "home"
            await query.edit_message_text(
                f"<b>🎯 Multiple Choice Complete!</b>\n\nScore: <b>{round(sc)}/{total}</b> ({pct}%)",
                reply_markup=main_menu_keyboard(), parse_mode="HTML")
        else:
            await send_mc_question(query.edit_message_text, ud, all_q)

    elif data == "quiz:hint":
        sess = ud["session"]
        idx = sess["idx"]
        q = sess["questions"][idx]
        kws = q.get("keywords_hu", [])
        masked = " | ".join(k[0] + "_" * (len(k) - 1) for k in kws) if kws else "<i>no keywords</i>"
        sess["hint_used"] = True
        text = format_question_text(q, idx, len(sess["questions"]), "Quiz")
        text += f"\n\n<b>💡 Hint (-20%):</b> {masked}\n<i>Type your answer below...</i>"
        await query.edit_message_text(text, reply_markup=hint_next_keyboard(), parse_mode="HTML")

    elif data == "quiz:skip":
        sess = ud["session"]
        q = sess["questions"][sess["idx"]]
        record_attempt(ud["progress"], q, 0.0)
        update_srs(ud["progress"], question_id(q["question_hu"]), 0)
        sess["idx"] += 1
        if sess["idx"] >= len(sess["questions"]): await finish_quiz(query.edit_message_text, ud, context)
        else: await send_quiz_question(query.edit_message_text, ud)

    elif data == "quiz:next":
        sess = ud["session"]
        if sess["idx"] >= len(sess["questions"]): await finish_quiz(query.edit_message_text, ud, context)
        else: await send_quiz_question(query.edit_message_text, ud)

    elif data == "exam:next":
        sess = ud["session"]
        if sess["idx"] >= len(sess["questions"]): await finish_exam(query.edit_message_text, ud)
        else: await send_quiz_question(query.edit_message_text, ud)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data: context.user_data.update(init_user_data())
    ud = context.user_data
    state = ud.get("state", "home")
    if state not in ("quiz", "exam"):
        await update.message.reply_text("Use /start to open the study menu.", reply_markup=main_menu_keyboard())
        return
    sess = ud["session"]
    q = sess["questions"][sess["idx"]]
    user_input = update.message.text.strip()
    score, matched, missed = score_answer(user_input, q.get("keywords_hu", []))
    if sess.get("hint_used"): score = max(0.0, score - 0.2)
    sess["score"] += score
    record_attempt(ud["progress"], q, score)
    update_srs(ud["progress"], question_id(q["question_hu"]), srs_quality(score))
    pct = int(score * 100)
    icon = "✅" if score >= 0.6 else ("🔶" if score >= 0.3 else "❌")
    ans_hu = q.get("answer_hu", "")
    out = [f"{icon} <b>Score: {pct}%</b>", f"<b>Answer:</b> {ans_hu}"]
    if matched: out.append("✅ " + " | ".join(f"<code>{k}</code>" for k in matched))
    if missed: out.append("❌ " + " | ".join(f"<code>{k}</code>" for k in missed))
    if sess.get("hint_used"): out.append("<i>(-20% hint penalty applied)</i>")
    sess["idx"] += 1
    next_cb = "exam:next" if state == "exam" else "quiz:next"
    await update.message.reply_text("\n".join(out), reply_markup=next_keyboard(next_cb), parse_mode="HTML")


def load_questions() -> list:
    if not os.path.exists(QUESTIONS_FILE):
        print(f"ERROR: questions.json not found at {QUESTIONS_FILE}")
        sys.exit(1)
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("ERROR: questions.json must be a JSON array.")
        sys.exit(1)
    return data


def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("ERROR: TELEGRAM_TOKEN environment variable is not set.")
        print("Set it: export TELEGRAM_TOKEN=your-token  (Linux/macOS)")
        print("    or: set TELEGRAM_TOKEN=your-token      (Windows CMD)")
        sys.exit(1)
    questions = load_questions()
    print(f"Loaded {len(questions)} questions.")
    persistence = PicklePersistence(filepath=PERSISTENCE_FILE)
    app = Application.builder().token(token).persistence(persistence).build()
    app.bot_data["questions"] = questions
    app.add_handler(CommandHandler(["start", "menu"], cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

