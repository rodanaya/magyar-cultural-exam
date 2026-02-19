#!/usr/bin/env python3
"""
Hungarian Cultural Knowledge Exam - CLI Study Tool
===================================================
A comprehensive study tool for preparing for the Hungarian Cultural
Knowledge Exam (Magyar Kulturalis Ismereti Vizsga).

Reads questions from questions.json and tracks progress in progress.json.

Usage:
    python study.py --mode learn --topic 1
    python study.py --mode quiz --topic 1
    python study.py --mode weak
    python study.py --mode exam
    python study.py --mode vocab --topic 1
    python study.py --stats
"""

import json
import random
import datetime
import difflib
import argparse
import os
import time
import sys
import hashlib
import signal
import io

# Fix Windows console encoding for Hungarian characters and Unicode symbols
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QUESTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions.json")
PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress.json")

TOPIC_NAMES = {
    1: "Nemzeti jelkepek es unnepek",
    2: "Magyar tortenelem",
    3: "Irodalom es zene",
    4: "Alaptorveny es intezmenyek",
    5: "Allampolgari jogok",
    6: "Mindennapi Magyarorszag",
}

TOPIC_NAMES_HU = {
    1: "Nemzeti jelk\u00e9pek \u00e9s \u00fcnnepek",
    2: "Magyar t\u00f6rt\u00e9nelem",
    3: "Irodalom \u00e9s zene",
    4: "Alapt\u00f6rv\u00e9ny \u00e9s int\u00e9zm\u00e9nyek",
    5: "\u00c1llampolg\u00e1ri jogok",
    6: "Mindennapi Magyarorsz\u00e1g",
}

DIFFICULTY_STARS = {
    "easy": "\u2605",
    "medium": "\u2605\u2605",
    "hard": "\u2605\u2605\u2605",
}

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BG_GREEN = "\033[42m"
BG_RED = "\033[41m"
BG_YELLOW = "\033[43m"

# Accent map for normalization
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

# ---------------------------------------------------------------------------
# Global state for graceful shutdown
# ---------------------------------------------------------------------------

_current_progress = None
_progress_dirty = False


def _signal_handler(sig, frame):
    """Handle Ctrl+C gracefully -- save progress before exit."""
    print(f"\n\n{YELLOW}Saving progress before exit...{RESET}")
    if _current_progress is not None and _progress_dirty:
        save_progress(_current_progress, PROGRESS_FILE)
        print(f"{GREEN}Progress saved.{RESET}")
    print(f"{CYAN}Viszontl\u00e1t\u00e1sra! (Goodbye!){RESET}\n")
    sys.exit(0)


signal.signal(signal.SIGINT, _signal_handler)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def clear_screen():
    """Clear the terminal screen."""
    if sys.platform == "win32":
        os.system("cls")
    else:
        os.system("clear")


def normalize_text(text):
    """Remove accents and lowercase text for comparison purposes."""
    return text.translate(ACCENT_MAP).lower().strip()


def question_id(question_hu):
    """Generate a stable ID for a question using MD5 hash of the Hungarian text."""
    return hashlib.md5(question_hu.encode("utf-8")).hexdigest()


def fuzzy_match_keyword(user_input, keyword, threshold=0.75):
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
        if fuzzy_match_keyword(user_input, kw):
            matched.append(kw)
        else:
            missed.append(kw)

    score = len(matched) / len(keywords)
    return (score, matched, missed)


def load_questions(filepath):
    """Load and validate questions from a JSON file."""
    if not os.path.isfile(filepath):
        print(f"{RED}Error: Questions file not found at {filepath}{RESET}")
        print(f"{YELLOW}Please create questions.json with the required format.{RESET}")
        sys.exit(1)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"{RED}Error: Invalid JSON in {filepath}: {exc}{RESET}")
        sys.exit(1)

    if not isinstance(questions, list):
        print(f"{RED}Error: questions.json must contain a JSON array.{RESET}")
        sys.exit(1)

    required_fields = {"question_hu", "question_en", "answer_hu", "answer_en", "topic", "difficulty", "keywords_hu"}
    valid = []
    for idx, q in enumerate(questions):
        missing = required_fields - set(q.keys())
        if missing:
            print(f"{YELLOW}Warning: Question #{idx + 1} missing fields {missing} -- skipping.{RESET}")
            continue
        # Ensure keywords_hu is a list
        if isinstance(q["keywords_hu"], str):
            q["keywords_hu"] = [k.strip() for k in q["keywords_hu"].split(",") if k.strip()]
        valid.append(q)

    if not valid:
        print(f"{RED}Error: No valid questions found in {filepath}.{RESET}")
        sys.exit(1)

    return valid


def load_progress(filepath):
    """Load progress from JSON file, or return a fresh structure."""
    if os.path.isfile(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure expected keys
            data.setdefault("sessions", [])
            data.setdefault("questions", {})
            data.setdefault("vocab", {})
            return data
        except (json.JSONDecodeError, KeyError):
            print(f"{YELLOW}Warning: progress.json was corrupted -- starting fresh.{RESET}")

    return {"sessions": [], "questions": {}, "vocab": {}}


def save_progress(progress, filepath):
    """Save progress to JSON file."""
    global _progress_dirty
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
        _progress_dirty = False
    except OSError as exc:
        print(f"{RED}Error saving progress: {exc}{RESET}")


def record_attempt(progress, q, score):
    """Record an attempt on a question in progress data."""
    global _progress_dirty
    qid = question_id(q["question_hu"])
    entry = progress["questions"].setdefault(qid, {
        "attempts": 0,
        "correct": 0,
        "last_seen": None,
        "accuracy": 0.0,
        "question_hu": q["question_hu"],
        "topic": q["topic"],
    })
    entry["attempts"] += 1
    if score >= 0.6:
        entry["correct"] += 1
    entry["last_seen"] = datetime.datetime.now().isoformat()
    entry["accuracy"] = entry["correct"] / entry["attempts"]
    _progress_dirty = True


def record_session(progress, mode, score, total, topic=None):
    """Record a study session."""
    global _progress_dirty
    session = {
        "date": datetime.datetime.now().isoformat(),
        "mode": mode,
        "score": score,
        "total": total,
    }
    if topic is not None:
        session["topic"] = topic
    progress["sessions"].append(session)
    _progress_dirty = True


def record_vocab_attempt(progress, word, correct):
    """Record an attempt on a vocab word."""
    global _progress_dirty
    entry = progress["vocab"].setdefault(word, {"attempts": 0, "correct": 0})
    entry["attempts"] += 1
    if correct:
        entry["correct"] += 1
    _progress_dirty = True


def print_header(title):
    """Print a formatted section header."""
    width = 60
    print()
    print(f"{BOLD}{CYAN}{'=' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * width}{RESET}")
    print()


def print_divider():
    """Print a thin divider line."""
    print(f"{DIM}{'─' * 60}{RESET}")


def format_time(seconds):
    """Format seconds into MM:SS string."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def get_input(prompt=""):
    """Get user input, return None on EOF."""
    try:
        return input(prompt)
    except EOFError:
        return None


def get_questions_for_topic(questions, topic):
    """Filter questions by topic number."""
    return [q for q in questions if q["topic"] == topic]


# ---------------------------------------------------------------------------
# Mode: Learn
# ---------------------------------------------------------------------------


def mode_learn(questions, progress, topic):
    """Learn mode -- show questions and answers sequentially."""
    global _current_progress
    _current_progress = progress

    topic_qs = get_questions_for_topic(questions, topic)
    if not topic_qs:
        print(f"{RED}No questions found for topic {topic}.{RESET}")
        return

    topic_label = TOPIC_NAMES_HU.get(topic, f"Topic {topic}")
    total = len(topic_qs)

    clear_screen()
    print_header(f"Learn Mode -- Topic {topic}: {topic_label}")
    print(f"  {total} questions to review. Press {BOLD}Enter{RESET} to advance, {BOLD}'q'{RESET} to quit.\n")

    for idx, q in enumerate(topic_qs):
        print_divider()
        stars = DIFFICULTY_STARS.get(q.get("difficulty", "medium"), "\u2605")
        print(f"\n  {BOLD}[Q {idx + 1}/{total}]{RESET} Topic {topic} - {topic_label} {YELLOW}{stars}{RESET}")
        print(f"  {CYAN}\U0001f1ed\U0001f1fa {q['question_hu']}{RESET}")
        print(f"  {DIM}\U0001f1ec\U0001f1e7 {q['question_en']}{RESET}")
        print()

        resp = get_input(f"  {DIM}Press Enter to reveal answer...{RESET}")
        if resp is None or resp.strip().lower() == "q":
            break

        print()
        print(f"  {GREEN}\U0001f1ed\U0001f1fa {q['answer_hu']}{RESET}")
        print(f"  {DIM}\U0001f1ec\U0001f1e7 {q['answer_en']}{RESET}")

        if q.get("keywords_hu"):
            kws = q["keywords_hu"]
            if isinstance(kws, list):
                kw_str = ", ".join(kws)
            else:
                kw_str = kws
            print(f"  {MAGENTA}Keywords: {kw_str}{RESET}")

        print()
        resp = get_input(f"  {DIM}Enter = next | q = quit: {RESET}")
        if resp is None or resp.strip().lower() == "q":
            break

    record_session(progress, "learn", 0, total, topic)
    save_progress(progress, PROGRESS_FILE)
    print(f"\n{GREEN}Learning session complete!{RESET}\n")


# ---------------------------------------------------------------------------
# Mode: Quiz
# ---------------------------------------------------------------------------


def run_quiz(questions_list, progress, mode_name="quiz", topic=None, show_timer=False, exam_start=None, exam_duration=None):
    """
    Core quiz engine used by quiz, weak, and exam modes.

    Returns (total_score_sum, total_questions).
    """
    global _current_progress, _progress_dirty
    _current_progress = progress

    total = len(questions_list)
    total_score = 0.0

    for idx, q in enumerate(questions_list):
        print_divider()

        # Timer display for exam mode
        if show_timer and exam_start is not None and exam_duration is not None:
            elapsed = time.time() - exam_start
            remaining = max(0, exam_duration - elapsed)
            timer_color = GREEN if remaining > 600 else (YELLOW if remaining > 120 else RED)
            print(f"\n  {timer_color}Time remaining: {format_time(remaining)}{RESET}")
            if remaining <= 0:
                print(f"\n  {RED}{BOLD}TIME IS UP!{RESET}")
                # Score remaining questions as 0
                record_session(progress, mode_name, total_score, total, topic)
                save_progress(progress, PROGRESS_FILE)
                return (total_score, total)

        stars = DIFFICULTY_STARS.get(q.get("difficulty", "medium"), "\u2605")
        topic_num = q.get("topic", "?")
        topic_label = TOPIC_NAMES_HU.get(topic_num, f"Topic {topic_num}")

        print(f"\n  {BOLD}[Q {idx + 1}/{total}]{RESET} Topic {topic_num} - {topic_label} {YELLOW}{stars}{RESET}")
        print(f"  {CYAN}\U0001f1ed\U0001f1fa {q['question_hu']}{RESET}")
        print(f"  {DIM}\U0001f1ec\U0001f1e7 {q['question_en']}{RESET}")
        print()

        user_answer = get_input(f"  {BOLD}Your answer (Hungarian): {RESET}")
        if user_answer is None:
            break
        if user_answer.strip().lower() == "q":
            break

        keywords = q.get("keywords_hu", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]

        sc, matched, missed = score_answer(user_answer, keywords)
        total_score += sc
        record_attempt(progress, q, sc)

        print()
        # Feedback
        if sc >= 0.6:
            icon = f"{GREEN}\u2714{RESET}"
            label = f"{GREEN}Correct!{RESET}"
        elif sc >= 0.3:
            icon = f"{YELLOW}~{RESET}"
            label = f"{YELLOW}Partial match{RESET}"
        else:
            icon = f"{RED}\u2718{RESET}"
            label = f"{RED}Incorrect{RESET}"

        pct = int(sc * 100)
        print(f"  {icon} {label} ({pct}% keyword match)")
        print()
        print(f"  {GREEN}Correct answer:{RESET}")
        print(f"  {GREEN}\U0001f1ed\U0001f1fa {q['answer_hu']}{RESET}")
        print(f"  {DIM}\U0001f1ec\U0001f1e7 {q['answer_en']}{RESET}")
        print()

        if matched:
            print(f"  {GREEN}\u2714 Matched: {', '.join(matched)}{RESET}")
        if missed:
            print(f"  {RED}\u2718 Missed:  {', '.join(missed)}{RESET}")

        print()

    return (total_score, total)


def mode_quiz(questions, progress, topic):
    """Quiz mode for a specific topic."""
    topic_qs = get_questions_for_topic(questions, topic)
    if not topic_qs:
        print(f"{RED}No questions found for topic {topic}.{RESET}")
        return

    topic_label = TOPIC_NAMES_HU.get(topic, f"Topic {topic}")

    clear_screen()
    print_header(f"Quiz Mode -- Topic {topic}: {topic_label}")
    print(f"  {len(topic_qs)} questions. Type your answer in Hungarian.")
    print(f"  Type {BOLD}'q'{RESET} to quit early.\n")

    random.shuffle(topic_qs)
    total_score, total = run_quiz(topic_qs, progress, mode_name="quiz", topic=topic)

    # Summary
    print_divider()
    print_header("Quiz Results")
    pct = (total_score / total * 100) if total > 0 else 0
    color = GREEN if pct >= 60 else (YELLOW if pct >= 30 else RED)
    print(f"  Score: {color}{total_score:.1f} / {total} ({pct:.0f}%){RESET}")
    if pct >= 80:
        print(f"  {GREEN}Excellent work! Kiv\u00e1l\u00f3!{RESET}")
    elif pct >= 60:
        print(f"  {GREEN}Good job! J\u00f3 munka!{RESET}")
    elif pct >= 30:
        print(f"  {YELLOW}Keep practicing! Gyakorolj tov\u00e1bb!{RESET}")
    else:
        print(f"  {RED}Needs more study. Tanulj tov\u00e1bb!{RESET}")
    print()

    record_session(progress, "quiz", total_score, total, topic)
    save_progress(progress, PROGRESS_FILE)


# ---------------------------------------------------------------------------
# Mode: Weak spots
# ---------------------------------------------------------------------------


def mode_weak(questions, progress):
    """Focus on weak spots -- questions with low accuracy or never attempted."""
    global _current_progress
    _current_progress = progress

    clear_screen()
    print_header("Weak Spots Review")

    # Gather weak questions
    weak_qs = []
    all_qids = {question_id(q["question_hu"]): q for q in questions}

    # Find questions with bad accuracy
    for qid, q in all_qids.items():
        entry = progress["questions"].get(qid)
        if entry is None:
            # Never attempted
            weak_qs.append((0.0, q))
        elif entry.get("accuracy", 0) < 0.6:
            weak_qs.append((entry["accuracy"], q))

    if not weak_qs:
        print(f"  {GREEN}{BOLD}Congratulations! Gratul\u00e1lok!{RESET}")
        print(f"  {GREEN}No weak spots found. You're well prepared!{RESET}")
        print(f"  {GREEN}Nincs gyenge pont. J\u00f3l felk\u00e9sz\u00fclt\u00e9l!{RESET}\n")
        return

    # Sort by worst accuracy first
    weak_qs.sort(key=lambda x: x[0])
    weak_questions = [q for _, q in weak_qs]

    print(f"  Found {YELLOW}{len(weak_questions)}{RESET} questions to review (accuracy < 60% or never attempted).\n")

    total_score, total = run_quiz(weak_questions, progress, mode_name="weak")

    print_divider()
    print_header("Weak Spots Review Results")
    pct = (total_score / total * 100) if total > 0 else 0
    color = GREEN if pct >= 60 else (YELLOW if pct >= 30 else RED)
    print(f"  Score: {color}{total_score:.1f} / {total} ({pct:.0f}%){RESET}\n")

    record_session(progress, "weak", total_score, total)
    save_progress(progress, PROGRESS_FILE)


# ---------------------------------------------------------------------------
# Mode: Mock Exam
# ---------------------------------------------------------------------------


def mode_exam(questions, progress):
    """Simulate the real exam -- 2 random questions per topic, 60-minute timer."""
    global _current_progress
    _current_progress = progress

    clear_screen()
    print_header("Mock Exam -- Magyar Kultur\u00e1lis Ismereti Vizsga")
    print(f"  {BOLD}Rules:{RESET}")
    print(f"    - 2 questions from each of the 6 topics (12 total)")
    print(f"    - 60-minute time limit")
    print(f"    - Each question worth 2.5 points (max 30)")
    print(f"    - Pass threshold: 16 points")
    print(f"    - Answer in Hungarian")
    print()

    resp = get_input(f"  {BOLD}Press Enter to start the exam, or 'q' to cancel: {RESET}")
    if resp is None or resp.strip().lower() == "q":
        return

    # Select 2 random questions per topic
    exam_qs = []
    for t in range(1, 7):
        topic_qs = get_questions_for_topic(questions, t)
        if len(topic_qs) >= 2:
            exam_qs.extend(random.sample(topic_qs, 2))
        else:
            exam_qs.extend(topic_qs)

    random.shuffle(exam_qs)

    clear_screen()
    print_header("Exam in Progress")
    exam_duration = 60 * 60  # 60 minutes in seconds
    exam_start = time.time()

    total_score, total = run_quiz(
        exam_qs, progress,
        mode_name="exam",
        show_timer=True,
        exam_start=exam_start,
        exam_duration=exam_duration,
    )

    elapsed = time.time() - exam_start

    # Scoring: each question worth 2.5 points
    # total_score is fraction-based (0 to total), convert to exam points
    points = (total_score / total * 30) if total > 0 else 0
    passed = points >= 16

    print_divider()
    print_header("Exam Results")

    print(f"  Time used: {format_time(elapsed)} / 60:00")
    print()

    color = GREEN if passed else RED
    print(f"  {BOLD}Score: {color}{points:.1f} / 30 points{RESET}")
    print(f"  Keyword accuracy: {total_score:.1f} / {total} questions")
    print()

    if passed:
        print(f"  {BG_GREEN}{BOLD}{WHITE}  PASSED -- MEGFELELT  {RESET}")
        print(f"  {GREEN}Gratul\u00e1lok! Congratulations!{RESET}")
    else:
        print(f"  {BG_RED}{BOLD}{WHITE}  FAILED -- NEM FELELT MEG  {RESET}")
        print(f"  {YELLOW}Keep studying! Tanulj tov\u00e1bb!{RESET}")
        print(f"  {YELLOW}You needed 16 points, you got {points:.1f}.{RESET}")

    print()
    record_session(progress, "exam", points, 30)
    save_progress(progress, PROGRESS_FILE)


# ---------------------------------------------------------------------------
# Mode: Vocab Drill
# ---------------------------------------------------------------------------


def mode_vocab(questions, progress, topic=None):
    """Vocabulary drill -- flash-card style keyword practice."""
    global _current_progress, _progress_dirty
    _current_progress = progress

    clear_screen()
    print_header("Vocabulary Drill -- Sz\u00f3kincs Gyakorl\u00e1s")

    # Collect vocab pairs: (hungarian_keyword, english_context, question_context)
    vocab_pairs = []
    seen_keywords = set()

    filtered = questions
    if topic is not None:
        filtered = get_questions_for_topic(questions, topic)
        if not filtered:
            print(f"{RED}No questions found for topic {topic}.{RESET}")
            return

    for q in filtered:
        keywords = q.get("keywords_hu", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]

        for kw in keywords:
            norm = normalize_text(kw)
            if norm not in seen_keywords:
                seen_keywords.add(norm)
                vocab_pairs.append({
                    "keyword_hu": kw,
                    "question_en": q["question_en"],
                    "answer_en": q["answer_en"],
                    "answer_hu": q["answer_hu"],
                    "topic": q["topic"],
                })

    if not vocab_pairs:
        print(f"{RED}No vocabulary words found.{RESET}")
        return

    random.shuffle(vocab_pairs)

    total_cards = len(vocab_pairs)
    print(f"  {total_cards} unique keywords to practice.")
    print(f"  Two rounds: English -> Hungarian, then Hungarian -> English.")
    print(f"  Type {BOLD}'q'{RESET} to quit early.\n")

    correct_count = 0
    total_attempts = 0

    # Round 1: English context -> Hungarian keyword
    print_header("Round 1: English -> Hungarian")
    print(f"  Given the English context, type the Hungarian keyword.\n")

    for idx, vp in enumerate(vocab_pairs):
        print_divider()
        print(f"\n  {BOLD}[{idx + 1}/{total_cards}]{RESET}")
        print(f"  {CYAN}Context: {vp['question_en']}{RESET}")
        print(f"  {DIM}Answer context: {vp['answer_en']}{RESET}")
        print()

        user_input = get_input(f"  {BOLD}Hungarian keyword: {RESET}")
        if user_input is None or user_input.strip().lower() == "q":
            break

        total_attempts += 1
        is_match = fuzzy_match_keyword(user_input, vp["keyword_hu"], threshold=0.75)

        if is_match:
            correct_count += 1
            print(f"  {GREEN}\u2714 Correct! -- {vp['keyword_hu']}{RESET}")
            record_vocab_attempt(progress, vp["keyword_hu"], True)
        else:
            print(f"  {RED}\u2718 Expected: {vp['keyword_hu']}{RESET}")
            record_vocab_attempt(progress, vp["keyword_hu"], False)
        print()

    # Round 2: Hungarian keyword -> English meaning
    print_header("Round 2: Hungarian -> English")
    print(f"  Given the Hungarian keyword, explain its meaning in English.\n")

    random.shuffle(vocab_pairs)

    for idx, vp in enumerate(vocab_pairs):
        print_divider()
        print(f"\n  {BOLD}[{idx + 1}/{total_cards}]{RESET}")
        print(f"  {CYAN}Hungarian keyword: {vp['keyword_hu']}{RESET}")
        print()

        user_input = get_input(f"  {BOLD}English meaning: {RESET}")
        if user_input is None or user_input.strip().lower() == "q":
            break

        total_attempts += 1
        # For English direction, check if user's answer is somewhat close
        # to the English answer context using fuzzy matching
        # We accept if any significant word from answer_en appears
        answer_words = [w for w in vp["answer_en"].split() if len(w) > 3]
        matched_any = False
        for aw in answer_words:
            if fuzzy_match_keyword(user_input, aw, threshold=0.7):
                matched_any = True
                break

        # Also check question context
        if not matched_any:
            q_words = [w for w in vp["question_en"].split() if len(w) > 3]
            for qw in q_words:
                if fuzzy_match_keyword(user_input, qw, threshold=0.7):
                    matched_any = True
                    break

        if matched_any:
            correct_count += 1
            print(f"  {GREEN}\u2714 Good!{RESET}")
            record_vocab_attempt(progress, vp["keyword_hu"] + "_en", True)
        else:
            print(f"  {YELLOW}~ The full context:{RESET}")
            record_vocab_attempt(progress, vp["keyword_hu"] + "_en", False)

        print(f"  {DIM}Q: {vp['question_en']}{RESET}")
        print(f"  {DIM}A: {vp['answer_en']}{RESET}")
        print()

    # Summary
    print_divider()
    print_header("Vocab Drill Results")
    pct = (correct_count / total_attempts * 100) if total_attempts > 0 else 0
    color = GREEN if pct >= 60 else (YELLOW if pct >= 30 else RED)
    print(f"  Score: {color}{correct_count} / {total_attempts} ({pct:.0f}%){RESET}")

    # Show mastered vs unmastered words
    mastered = 0
    for vp in vocab_pairs:
        entry = progress["vocab"].get(vp["keyword_hu"], {})
        if entry.get("attempts", 0) > 0:
            acc = entry.get("correct", 0) / entry["attempts"]
            if acc >= 0.8 and entry["attempts"] >= 2:
                mastered += 1

    print(f"  Mastered words: {GREEN}{mastered}{RESET} / {total_cards}")
    print()

    record_session(progress, "vocab", correct_count, total_attempts, topic)
    save_progress(progress, PROGRESS_FILE)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def show_stats(questions, progress):
    """Display comprehensive study statistics."""
    clear_screen()
    print_header("Study Statistics -- Tanul\u00e1si Statisztika")

    sessions = progress.get("sessions", [])
    q_data = progress.get("questions", {})
    vocab_data = progress.get("vocab", {})

    # ---- Session summary ----
    total_sessions = len(sessions)
    print(f"  {BOLD}Total study sessions:{RESET} {total_sessions}")

    if sessions:
        # Study streak
        session_dates = set()
        for s in sessions:
            try:
                dt = datetime.datetime.fromisoformat(s["date"])
                session_dates.add(dt.date())
            except (ValueError, KeyError):
                pass

        if session_dates:
            sorted_dates = sorted(session_dates, reverse=True)
            streak = 0
            today = datetime.date.today()
            check_date = today
            for d in sorted_dates:
                if d == check_date:
                    streak += 1
                    check_date -= datetime.timedelta(days=1)
                elif d < check_date:
                    break

            print(f"  {BOLD}Current study streak:{RESET} {GREEN}{streak} day(s){RESET}")
            print(f"  {BOLD}Total unique days studied:{RESET} {len(session_dates)}")

        # Last session
        try:
            last = datetime.datetime.fromisoformat(sessions[-1]["date"])
            print(f"  {BOLD}Last session:{RESET} {last.strftime('%Y-%m-%d %H:%M')}")
        except (ValueError, KeyError):
            pass
    else:
        print(f"  {YELLOW}No sessions recorded yet. Start studying!{RESET}")

    # ---- Per-topic accuracy ----
    print()
    print_divider()
    print(f"\n  {BOLD}Per-Topic Accuracy:{RESET}\n")

    topic_stats = {}
    for t in range(1, 7):
        topic_stats[t] = {"attempts": 0, "correct": 0}

    for qid, entry in q_data.items():
        t = entry.get("topic")
        if t and t in topic_stats:
            topic_stats[t]["attempts"] += entry.get("attempts", 0)
            topic_stats[t]["correct"] += entry.get("correct", 0)

    recommend_topic = None
    worst_accuracy = 1.0

    for t in range(1, 7):
        stats = topic_stats[t]
        label = TOPIC_NAMES_HU.get(t, f"Topic {t}")
        if stats["attempts"] > 0:
            acc = stats["correct"] / stats["attempts"]
            pct = acc * 100
            color = GREEN if pct >= 60 else (YELLOW if pct >= 30 else RED)
            bar_len = int(acc * 20)
            bar = f"{color}{'█' * bar_len}{DIM}{'░' * (20 - bar_len)}{RESET}"
            print(f"    Topic {t}: {label}")
            print(f"    {bar} {color}{pct:.0f}%{RESET} ({stats['correct']}/{stats['attempts']})")
            print()
            if acc < worst_accuracy:
                worst_accuracy = acc
                recommend_topic = t
        else:
            print(f"    Topic {t}: {label}")
            print(f"    {DIM}{'░' * 20}{RESET} {YELLOW}Not attempted{RESET}")
            print()
            if worst_accuracy > 0:
                recommend_topic = t
                worst_accuracy = 0

    # ---- Overall readiness ----
    print_divider()
    total_attempts = sum(s["attempts"] for s in topic_stats.values())
    total_correct = sum(s["correct"] for s in topic_stats.values())

    if total_attempts > 0:
        overall = total_correct / total_attempts * 100
        color = GREEN if overall >= 60 else (YELLOW if overall >= 30 else RED)
        print(f"\n  {BOLD}Overall readiness:{RESET} {color}{overall:.0f}%{RESET}")
    else:
        print(f"\n  {BOLD}Overall readiness:{RESET} {YELLOW}N/A (no attempts yet){RESET}")

    # ---- Exam results ----
    exam_sessions = [s for s in sessions if s.get("mode") == "exam"]
    if exam_sessions:
        print()
        print_divider()
        print(f"\n  {BOLD}Mock Exam History:{RESET}\n")
        for es in exam_sessions[-5:]:  # Last 5 exams
            try:
                dt = datetime.datetime.fromisoformat(es["date"]).strftime("%Y-%m-%d %H:%M")
            except (ValueError, KeyError):
                dt = "?"
            pts = es.get("score", 0)
            passed = pts >= 16
            status = f"{GREEN}PASSED{RESET}" if passed else f"{RED}FAILED{RESET}"
            print(f"    {dt} -- {pts:.1f}/30 pts -- {status}")
        print()

    # ---- Most missed questions ----
    print_divider()
    print(f"\n  {BOLD}Most Missed Questions:{RESET}\n")

    missed_list = []
    for qid, entry in q_data.items():
        if entry.get("attempts", 0) > 0 and entry.get("accuracy", 1.0) < 0.6:
            missed_list.append(entry)

    missed_list.sort(key=lambda x: x.get("accuracy", 0))

    if missed_list:
        for m in missed_list[:5]:
            acc = m.get("accuracy", 0) * 100
            t = m.get("topic", "?")
            qtext = m.get("question_hu", "?")
            print(f"    {RED}{acc:.0f}%{RESET} -- [Topic {t}] {qtext}")
    else:
        print(f"    {GREEN}No frequently missed questions! Great work!{RESET}")

    # ---- Vocab stats ----
    if vocab_data:
        print()
        print_divider()
        print(f"\n  {BOLD}Vocabulary:{RESET}")
        total_vocab = len(vocab_data)
        mastered = sum(
            1 for v in vocab_data.values()
            if v.get("attempts", 0) >= 2 and (v.get("correct", 0) / v["attempts"]) >= 0.8
        )
        print(f"    Total words practiced: {total_vocab}")
        print(f"    Mastered: {GREEN}{mastered}{RESET} / {total_vocab}")
    print()

    # ---- Recommendation ----
    print_divider()
    print(f"\n  {BOLD}Recommendation:{RESET}")
    if recommend_topic is not None:
        label = TOPIC_NAMES_HU.get(recommend_topic, f"Topic {recommend_topic}")
        if worst_accuracy == 0:
            print(f"    {CYAN}Start with Topic {recommend_topic}: {label} (not attempted yet){RESET}")
            print(f"    Run: python study.py --mode learn --topic {recommend_topic}")
        else:
            print(f"    {CYAN}Focus on Topic {recommend_topic}: {label} (lowest accuracy){RESET}")
            print(f"    Run: python study.py --mode quiz --topic {recommend_topic}")
    else:
        print(f"    {GREEN}All topics look good! Try a mock exam.{RESET}")
        print(f"    Run: python study.py --mode exam")
    print()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Hungarian Cultural Knowledge Exam -- CLI Study Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  learn   Review questions and answers for a topic
  quiz    Test yourself on a topic with keyword matching
  weak    Focus on questions you got wrong or never attempted
  exam    Simulate the real exam (12 questions, 60-min timer)
  vocab   Vocabulary flash-card drill

Examples:
  python study.py --mode learn --topic 1
  python study.py --mode quiz --topic 3
  python study.py --mode weak
  python study.py --mode exam
  python study.py --mode vocab
  python study.py --mode vocab --topic 2
  python study.py --stats
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["learn", "quiz", "weak", "exam", "vocab"],
        help="Study mode to use",
    )
    parser.add_argument(
        "--topic",
        type=int,
        choices=[1, 2, 3, 4, 5, 6],
        help="Topic number (1-6)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show study statistics",
    )

    args = parser.parse_args()

    # Must specify either --mode or --stats
    if not args.mode and not args.stats:
        parser.print_help()
        print(f"\n{YELLOW}Please specify --mode or --stats.{RESET}")
        sys.exit(1)

    # Validate topic requirement
    if args.mode in ("learn", "quiz") and args.topic is None:
        print(f"{RED}Error: --topic is required for '{args.mode}' mode.{RESET}")
        print(f"{YELLOW}Usage: python study.py --mode {args.mode} --topic N{RESET}")
        sys.exit(1)

    # Load data
    questions = load_questions(QUESTIONS_FILE)
    progress = load_progress(PROGRESS_FILE)

    global _current_progress
    _current_progress = progress

    if args.stats:
        show_stats(questions, progress)
        return

    if args.mode == "learn":
        mode_learn(questions, progress, args.topic)
    elif args.mode == "quiz":
        mode_quiz(questions, progress, args.topic)
    elif args.mode == "weak":
        mode_weak(questions, progress)
    elif args.mode == "exam":
        mode_exam(questions, progress)
    elif args.mode == "vocab":
        mode_vocab(questions, progress, args.topic)


if __name__ == "__main__":
    main()
