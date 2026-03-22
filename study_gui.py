#!/usr/bin/env python3
"""
Magyar Kulturális Ismereti Vizsga — Textual TUI Study Tool v2
=============================================================
Enhancements: multiple choice mode, keyboard shortcuts everywhere,
self-rating in Learn (feeds SRS), 7-day SRS forecast, hint button.

Run:
    pip install textual
    python study_gui.py
"""

from __future__ import annotations

import datetime
import random
import sys
import os
import time
import unicodedata

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Button, Static, Input, Rule, ProgressBar
    from textual.containers import Container, ScrollableContainer, Horizontal, Vertical
    from textual.screen import Screen, ModalScreen
    from textual.binding import Binding
    from textual import on
except ImportError:
    print("Textual not installed. Run:  pip install textual")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from study import (
    load_questions, load_progress, save_progress,
    score_answer, question_id, get_questions_for_topic,
    record_attempt, record_session, record_vocab_attempt,
    QUESTIONS_FILE, PROGRESS_FILE,
)

# ── Enhancement 1: Accent-aware typo tolerance ────────────────────────────────


def normalize_hu(text: str) -> str:
    """Lowercase and strip Hungarian combining accent marks via NFD decomposition."""
    lowered = text.lower()
    nfd = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def score_answer_tolerant(user_input: str, keywords: list) -> tuple:
    """
    Wrapper around score_answer that also tries accent-stripped input.
    Returns the better (score, matched, missed) tuple.
    """
    result = score_answer(user_input, keywords)
    score, matched, missed = result
    if score < 1.0:
        result2 = score_answer(normalize_hu(user_input), keywords)
        if result2[0] > score:
            return result2
    return result


# ── Enhancement 2: Leech detection ───────────────────────────────────────────


def update_leech(progress: dict, qid: str, correct: bool) -> None:
    """
    Track consecutive wrong answers per question.
    Sets is_leech=True when consecutive_wrong >= 5.
    Caller is responsible for saving progress.
    """
    entry = progress.setdefault("questions", {}).setdefault(qid, {
        "attempts": 0, "correct": 0, "last_seen": None,
        "accuracy": 0.0, "question_hu": "", "topic": None,
    })
    if correct:
        entry["consecutive_wrong"] = 0
        entry["is_leech"] = False
    else:
        entry["consecutive_wrong"] = entry.get("consecutive_wrong", 0) + 1
        entry["is_leech"] = entry["consecutive_wrong"] >= 5


# ── Enhancement 3: Smart session sizing ──────────────────────────────────────


def weighted_sample(pool: list, n: int, progress: dict) -> list:
    """
    Draw up to n unique questions from pool, weighted by performance.
    Unseen questions get weight 3.0, accuracy < 0.4 gets 2.0, others 1.0.
    """
    if not pool:
        return []
    q_data = progress.get("questions", {})
    weights = []
    for q in pool:
        qid = question_id(q["question_hu"])
        entry = q_data.get(qid)
        if entry is None:
            weights.append(3.0)
        elif entry.get("accuracy", 1.0) < 0.4:
            weights.append(2.0)
        else:
            weights.append(1.0)

    target = min(n, len(pool))
    chosen: list = []
    seen_ids: set = set()
    max_attempts = target * 20
    attempts = 0
    while len(chosen) < target and attempts < max_attempts:
        picks = random.choices(pool, weights=weights, k=1)
        p = picks[0]
        pid = question_id(p["question_hu"])
        if pid not in seen_ids:
            seen_ids.add(pid)
            chosen.append(p)
        attempts += 1

    if len(chosen) < target:
        # Fallback: shuffle and slice
        remaining = [q for q in pool if question_id(q["question_hu"]) not in seen_ids]
        random.shuffle(remaining)
        chosen.extend(remaining[: target - len(chosen)])

    return chosen


# ── Constants ─────────────────────────────────────────────────────────────────

TOPIC_SHORT = {
    1: "Symbols & Holidays",    2: "History",
    3: "Literature & Music",    4: "Law & Institutions",
    5: "Citizens' Rights",      6: "Everyday Hungary",
}
TOPIC_HU = {
    1: "Nemzeti jelképek és ünnepek",   2: "Magyar történelem",
    3: "Irodalom és zene",              4: "Alaptörvény és intézmények",
    5: "Állampolgári jogok",            6: "Mindennapi Magyarország",
}

# ── Topic introductions (shown in Study Guide before Q&A) ─────────────────────

TOPIC_INTRO = {
    1: (
        "Magyarország nemzeti jelképei: a piros-fehér-zöld trikolór zászló (felül piros, középen "
        "fehér, alul zöld), a koronás kettős keresztes és hármas halmos címer, a Himnusz "
        "(szöveg: Kölcsey Ferenc 1823, zene: Erkel Ferenc) és a Szózat (Vörösmarty Mihály). "
        "A kokárda piros-fehér-zöld jelvény, március 15-én viselik. A három nemzeti ünnep: "
        "március 15. (1848-as polgári forradalom), augusztus 20. (I. István király napja, "
        "az államalapítás ünnepe), október 23. (1956-os forradalom és az 1989-es köztársaság "
        "kikiáltásának napja).",
        "Hungary's national symbols: the red-white-green tricolor flag (red on top, white in the "
        "middle, green at the bottom), the crowned coat of arms with double cross and triple hill, "
        "the Himnusz (text: Ferenc Kölcsey 1823, music: Ferenc Erkel) and the Szózat (Mihály "
        "Vörösmarty). The kokárda (cockade) is a red-white-green badge worn on March 15. "
        "The three national holidays: March 15 (1848 civic revolution), August 20 (St. Stephen's "
        "Day, founding of the state), October 23 (1956 revolution and 1989 proclamation of "
        "the Republic).",
    ),
    2: (
        "Magyar történelem főbb dátumai: honfoglalás 895–896 (Árpád vezér, 7 törzs, "
        "Kárpát-medence), keresztény királyság megalapítása 1000-ben (I. István / Szent István, "
        "Szent Korona), tatárjárás 1241–42, Hunyadi Mátyás király 1458–90 (Corvina könyvtár, "
        "fekete sereg), mohácsi csata 1526, török hódoltság 1526–1699, 1848-as forradalom "
        "(Kossuth Lajos, Petőfi Sándor, Széchenyi István), Trianoni béke 1920, 1956-os "
        "forradalom (október 23.), rendszerváltás 1989.",
        "Key dates in Hungarian history: the conquest 895–896 (Prince Árpád, 7 tribes, "
        "Carpathian Basin), founding of the Christian kingdom 1000 (Stephen I / Saint Stephen, "
        "Holy Crown), Mongol invasion 1241–42, King Matthias (Mátyás) 1458–90 (Corvina library, "
        "Black Army), Battle of Mohács 1526, Ottoman occupation 1526–1699, 1848 revolution "
        "(Lajos Kossuth, Sándor Petőfi, István Széchenyi), Treaty of Trianon 1920, 1956 "
        "revolution (October 23), transition to democracy 1989.",
    ),
    3: (
        "A magyar irodalom és zene kiemelkedő alakjai. IRODALOM: Petőfi Sándor (János vitéz, "
        "Nemzeti dal), Arany János (Toldi-trilógia, Buda halála), Vörösmarty Mihály (Szózat, "
        "Csongor és Tünde), Kölcsey Ferenc (Himnusz szövege), Madách Imre (Az ember tragédiája), "
        "Jókai Mór (Az arany ember, A kőszívű ember fiai), Gárdonyi Géza (Egri csillagok), "
        "Katona József (Bánk bán), Ady Endre (Új versek). "
        "ZENE: Erkel Ferenc (Himnusz zenéje, Bánk bán opera), Bartók Béla (Kékszakállú herceg "
        "vára, Csodálatos mandarin, népdalkutatás), Kodály Zoltán (Háry János, Psalmus "
        "Hungaricus, Kodály-módszer), Liszt Ferenc (Magyar rapszódiák, Faust-szimfónia).",
        "Outstanding figures of Hungarian literature and music. LITERATURE: Sándor Petőfi "
        "(John the Valiant, National Song), János Arany (Toldi trilogy, Death of Buda), "
        "Mihály Vörösmarty (Szózat/Appeal, Csongor and Tünde), Ferenc Kölcsey (text of Himnusz), "
        "Imre Madách (The Tragedy of Man), Mór Jókai (The Man with the Golden Touch, The Baron's "
        "Sons), Géza Gárdonyi (Eclipse of the Crescent Moon / Stars of Eger), József Katona "
        "(Bánk bán), Endre Ady (New Poems). "
        "MUSIC: Ferenc Erkel (music of Himnusz, Bánk bán opera), Béla Bartók (Bluebeard's "
        "Castle, The Miraculous Mandarin, folk music research), Zoltán Kodály (Háry János, "
        "Psalmus Hungaricus, Kodály Method), Ferenc Liszt (Hungarian Rhapsodies, Faust Symphony).",
    ),
    4: (
        "Magyarország Alaptörvénye 2012. január 1-jén lépett hatályba, felváltva az 1949-es "
        "alkotmányt. A törvényhozó hatalom: Országgyűlés (199 képviselő, 4 évre választva). "
        "A végrehajtó hatalom: Kormány, élén a miniszterelnökkel. Az államfő: köztársasági elnök "
        "(5 évre, az Országgyűlés választja). Az igazságszolgáltató hatalom: bíróságok; az "
        "Alkotmánybíróság az Alaptörvény őre. Az Állami Számvevőszék a pénzügyi ellenőrző szerv. "
        "Az alapvető jogokat az Alaptörvény II–XXXI. cikkei rögzítik.",
        "Hungary's Fundamental Law (constitution) entered into force on 1 January 2012, replacing "
        "the 1949 constitution. Legislative power: the National Assembly (199 members, elected for "
        "4 years). Executive power: the Government, led by the Prime Minister. Head of state: the "
        "President of the Republic (elected by the National Assembly for 5 years). Judicial power: "
        "the courts; the Constitutional Court guards the Fundamental Law. The State Audit Office "
        "is the financial oversight body. Fundamental rights are laid down in Articles II–XXXI.",
    ),
    5: (
        "Magyar állampolgárság általános feltételei: legalább 8 éves folyamatos magyarországi "
        "lakóhely, büntetlen előélet, megélhetés biztosítása, és a kulturális ismereti vizsga "
        "sikeres teljesítése. Kedvezményes honosítás: házastárs (3 év), menekült jogállású (3 év), "
        "kiskorú gyermek (ha szülei állampolgárok). A kulturális vizsga: 30 kérdés, 60 perc, "
        "az átmenéshez 16 pont kell (53%). Állampolgári kötelességek: adófizetés, honvédelem, "
        "törvénytisztelet. Jogok: szavazati jog, szabad mozgás, oktatáshoz való jog.",
        "General requirements for Hungarian citizenship: at least 8 years of continuous residence "
        "in Hungary, clean criminal record, proof of livelihood, and passing the cultural knowledge "
        "exam. Preferential naturalization: spouse (3 years), refugee status (3 years), minor child "
        "(if parents are citizens). The cultural exam: 30 questions, 60 minutes, 16 points (53%) "
        "needed to pass. Civic duties: paying taxes, national defence, law-abiding. "
        "Rights: right to vote, freedom of movement, right to education.",
    ),
    6: (
        "Magyarország általános adatai: terület 93.028 km², főváros Budapest (1,7 millió lakos), "
        "teljes népesség kb. 10 millió fő. Legmagasabb pont: Kékes (1014 m, Mátra). Fő folyók: "
        "Duna (Magyarország kettévágja), Tisza. Legnagyobb tó: Balaton (600 km², Közép-Európa "
        "legnagyobb tava). Közigazgatás: 19 megye + Budapest. Szomszédos országok: Ausztria, "
        "Szlovákia, Ukrajna, Románia, Szerbia, Horvátország, Szlovénia (7 ország). "
        "Deviza: forint (HUF). EU-tagság: 2004. május 1. óta. NATO-tag: 1999 óta.",
        "General facts about Hungary: area 93,028 km², capital Budapest (1.7M residents), "
        "total population ~10 million. Highest point: Kékes (1014 m, Mátra mountains). Main rivers: "
        "the Danube (Duna, bisects Hungary), Tisza. Largest lake: Balaton (600 km², Central "
        "Europe's largest lake). Administration: 19 counties + Budapest. Neighboring countries: "
        "Austria, Slovakia, Ukraine, Romania, Serbia, Croatia, Slovenia (7 countries). "
        "Currency: forint (HUF). EU member since 1 May 2004. NATO member since 1999.",
    ),
}

# ── Topic 3 Authors & Works reference (used in Study Guide) ───────────────────

TOPIC3_AUTHORS = [
    # (name_hu, name_en, works_hu, works_en)
    ("Petőfi Sándor (1823–1849)",
     "Sándor Petőfi (1823–1849)",
     "János vitéz · Nemzeti dal · Az apostol · Talpra magyar! · A helység kalapácsa",
     "John the Valiant · National Song · The Apostle · Rise Up, Hungarians! · The Village Hammer"),
    ("Arany János (1817–1882)",
     "János Arany (1817–1882)",
     "Toldi · Toldi estéje · Toldi szerelme (Toldi-trilógia) · Buda halála · Rege a csodaszarvasról",
     "Toldi · Toldi's Eve · Toldi's Love (Toldi trilogy) · Death of Buda · Legend of the Wondrous Stag"),
    ("Vörösmarty Mihály (1800–1855)",
     "Mihály Vörösmarty (1800–1855)",
     "Szózat · Csongor és Tünde · Vén cigány · Zalán futása",
     "Szózat (Appeal) · Csongor and Tünde · The Old Gypsy · The Flight of Zalán"),
    ("Kölcsey Ferenc (1790–1838)",
     "Ferenc Kölcsey (1790–1838)",
     "Himnusz szövege (1823) · Huszt · Parainesis · Vanitatum vanitas",
     "Text of the Himnusz (1823) · Huszt · Parainesis · Vanitatum vanitas"),
    ("Madách Imre (1823–1864)",
     "Imre Madách (1823–1864)",
     "Az ember tragédiája (drámai költemény)",
     "The Tragedy of Man (dramatic poem)"),
    ("Jókai Mór (1825–1904)",
     "Mór Jókai (1825–1904)",
     "Az arany ember · A kőszívű ember fiai · Fekete gyémántok · Az új földesúr",
     "The Man with the Golden Touch · The Baron's Sons · Black Diamonds · The New Landlord"),
    ("Gárdonyi Géza (1863–1922)",
     "Géza Gárdonyi (1863–1922)",
     "Egri csillagok · Isten rabjai · A láthatatlan ember",
     "Eclipse of the Crescent Moon (Stars of Eger) · Slave of God · The Invisible Man"),
    ("Katona József (1791–1830)",
     "József Katona (1791–1830)",
     "Bánk bán (dráma, nemzeti tragédia)",
     "Bánk bán (drama, national tragedy)"),
    ("Ady Endre (1877–1919)",
     "Endre Ady (1877–1919)",
     "Új versek · Vér és arany · A Tisza-parton · Góg és Magóg fia vagyok én",
     "New Poems · Blood and Gold · On the Banks of the Tisza · I am the son of Gog and Magog"),
    ("Erkel Ferenc (1810–1893)  ♪ ZENÉSZ",
     "Ferenc Erkel (1810–1893)  ♪ COMPOSER",
     "Himnusz zenéje · Bánk bán (opera) · Hunyadi László (opera) · Sarolta (opera)",
     "Music of the Himnusz · Bánk bán (opera) · Hunyadi László (opera) · Sarolta (opera)"),
    ("Bartók Béla (1881–1945)  ♪ ZENÉSZ",
     "Béla Bartók (1881–1945)  ♪ COMPOSER",
     "Kékszakállú herceg vára · Csodálatos mandarin · Cantata Profana · népdalkutatás & gyűjtés",
     "Bluebeard's Castle · The Miraculous Mandarin · Cantata Profana · folk music research & collection"),
    ("Kodály Zoltán (1882–1967)  ♪ ZENÉSZ",
     "Zoltán Kodály (1882–1967)  ♪ COMPOSER",
     "Háry János (daljáték) · Psalmus Hungaricus · Budavári Te Deum · Kodály-módszer (zenepedagógia)",
     "Háry János (musical play) · Psalmus Hungaricus · Budavári Te Deum · Kodály Method (music education)"),
    ("Liszt Ferenc (1811–1886)  ♪ ZENÉSZ",
     "Ferenc Liszt (1811–1886)  ♪ COMPOSER",
     "Magyar rapszódiák (19 db) · Faust-szimfónia · Haláltánc · Les Préludes",
     "Hungarian Rhapsodies (19 pieces) · Faust Symphony · Totentanz · Les Préludes"),
]

# ── SRS helpers ───────────────────────────────────────────────────────────────


def srs_quality(score: float) -> int:
    if score >= 0.9: return 5
    if score >= 0.7: return 4
    if score >= 0.6: return 3
    if score >= 0.3: return 2
    if score >= 0.1: return 1
    return 0


def update_srs(progress: dict, qid: str, quality: int) -> None:
    srs = progress.setdefault("srs", {})
    entry = srs.setdefault(qid, {"interval": 0, "ease": 2.5, "due": None})
    ef, interval = entry["ease"], entry["interval"]
    if quality < 3:
        interval = 1
    elif interval == 0:
        interval = 1
    elif interval == 1:
        interval = 6
    else:
        interval = round(interval * ef)
    ef = max(1.3, ef + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    entry["interval"] = interval
    entry["ease"] = round(ef, 3)
    entry["due"] = (
        datetime.date.today() + datetime.timedelta(days=interval)
    ).isoformat()


def get_due_questions(progress: dict, questions: list) -> list:
    today = datetime.date.today().isoformat()
    srs = progress.get("srs", {})
    result = []
    for q in questions:
        entry = srs.get(question_id(q["question_hu"]))
        if entry is None or not entry.get("due") or entry["due"] <= today:
            result.append(q)
    return result


def srs_forecast(progress: dict, questions: list, days: int = 7) -> list:
    """Return [(date, count)] for the next `days` days."""
    srs = progress.get("srs", {})
    today = datetime.date.today()
    counts: dict = {}
    for q in questions:
        entry = srs.get(question_id(q["question_hu"]))
        if not entry or not entry.get("due"):
            delta = 0
        else:
            delta = (datetime.date.fromisoformat(entry["due"]) - today).days
        if 0 <= delta < days:
            counts[delta] = counts.get(delta, 0) + 1
    return [(today + datetime.timedelta(days=d), counts.get(d, 0)) for d in range(days)]


# ── General helpers ───────────────────────────────────────────────────────────


def topic_accuracy(progress: dict, topic: int) -> tuple:
    correct = attempts = 0
    for entry in progress.get("questions", {}).values():
        if entry.get("topic") == topic:
            attempts += entry.get("attempts", 0)
            correct += entry.get("correct", 0)
    return correct, attempts


def accuracy_bar(correct: int, attempts: int, width: int = 18) -> str:
    if not attempts:
        return f"[white]{'─' * width}[/white] [white]--[/white]"
    pct = correct / attempts
    filled = round(pct * width)
    color = "bright_green" if pct >= 0.6 else ("yellow" if pct >= 0.3 else "bright_red")
    return (
        f"[{color}]{'█' * filled}[/{color}]"
        f"[white]{'░' * (width - filled)}[/white]"
        f" [{color}]{pct * 100:.0f}%[/{color}]"
    )


def study_streak(progress: dict) -> int:
    dates: set = set()
    for s in progress.get("sessions", []):
        try:
            dates.add(datetime.datetime.fromisoformat(s["date"]).date())
        except (ValueError, KeyError):
            pass
    streak, check = 0, datetime.date.today()
    for d in sorted(dates, reverse=True):
        if d == check:
            streak += 1
            check -= datetime.timedelta(days=1)
        elif d < check:
            break
    return streak


def mask_keyword(kw: str) -> str:
    """'Kolcsey Ferenc' → 'K_______ F_____'"""
    return " ".join(
        w[0] + "_" * (len(w) - 1) if len(w) > 1 else w for w in kw.split()
    )


def build_mc_options(q: dict, all_questions: list) -> list:
    """Return [(answer_text, is_correct)] × 4, shuffled."""
    correct = q["answer_hu"]
    pool = [x for x in all_questions if x["question_hu"] != q["question_hu"]]
    random.shuffle(pool)
    wrong: list = []
    seen = {correct}
    for c in pool:
        ans = c["answer_hu"]
        if len(ans) > 72:
            ans = ans[:70] + "…"
        if ans not in seen:
            seen.add(ans)
            wrong.append(ans)
        if len(wrong) == 3:
            break
    while len(wrong) < 3:
        wrong.append("—")
    options = [(correct, True)] + [(w, False) for w in wrong]
    random.shuffle(options)
    return options


# ── Home Screen ───────────────────────────────────────────────────────────────


class HomeScreen(Screen):
    """Dashboard: topic selector, mode launcher, accuracy + SRS forecast."""

    BINDINGS = [
        Binding("1", "sel1", "T1", show=False),
        Binding("2", "sel2", "T2", show=False),
        Binding("3", "sel3", "T3", show=False),
        Binding("4", "sel4", "T4", show=False),
        Binding("5", "sel5", "T5", show=False),
        Binding("6", "sel6", "T6", show=False),
        Binding("g", "launch_guide",  "Guide"),
        Binding("l", "launch_learn",  "Learn"),
        Binding("q", "launch_quiz",   "Quiz"),
        Binding("m", "launch_mc",     "M-Choice"),
        Binding("w", "launch_weak",   "Weak"),
        Binding("e", "launch_exam",   "Exam"),
        Binding("s", "launch_stats",  "Stats"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="home-layout"):
            with Vertical(id="left-panel"):
                yield Static("TOPICS", classes="panel-title")
                for t in range(1, 7):
                    yield Button(
                        f"T{t}  {TOPIC_SHORT[t]}",
                        id=f"topic-{t}", classes="topic-btn",
                    )
                yield Rule()
                yield Static("MODES", classes="panel-title")
                yield Button("📚  Study Guide",      id="mode-guide",  classes="mode-btn", variant="success")
                yield Button("📖  Learn",           id="mode-learn",  classes="mode-btn")
                yield Button("❓  Quiz",             id="mode-quiz",   classes="mode-btn")
                yield Button("🔢  Multiple Choice",  id="mode-mc",     classes="mode-btn")
                yield Button("⚠   Weak Spots",      id="mode-weak",   classes="mode-btn")
                yield Button("⏰  SRS Review",       id="mode-srs",    classes="mode-btn", variant="warning")
                yield Button("📝  Mock Exam",        id="mode-exam",   classes="mode-btn")
                yield Button("🔤  Vocab Drill",      id="mode-vocab",  classes="mode-btn")
                yield Button("📊  Statistics",       id="mode-stats",  classes="mode-btn")
            with ScrollableContainer(id="right-panel"):
                yield Static(id="dashboard-content")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_dashboard()

    def on_screen_resume(self) -> None:
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        app = self.app
        progress, questions = app.progress, app.questions
        due_count = len(get_due_questions(progress, questions))
        streak = study_streak(progress)
        sessions = progress.get("sessions", [])

        lines = []

        # ── Status banner ─────────────────────────────────────────────────────
        today_str = datetime.date.today().strftime("%A, %d %B %Y")
        lines.append(f"[bold white]{today_str}[/bold white]")
        lines.append("")

        if due_count > 0:
            lines.append(
                f"[bold yellow on dark_orange] ⚡  {due_count} SRS card(s) due for review today [/bold yellow on dark_orange]"
            )
        else:
            lines.append(
                "[bold green on dark_green] ✓  All caught up — no SRS cards due today [/bold green on dark_green]"
            )

        streak_icon = "🔥" if streak >= 3 else ("★" if streak >= 1 else "○")
        lines.append(
            f"\n  {streak_icon}  [bold white]Streak:[/bold white] [bright_green]{streak} day(s)[/bright_green]"
            f"     [bold white]Sessions:[/bold white] [cyan]{len(sessions)}[/cyan]"
            f"     [bold white]Questions:[/bold white] [cyan]{len(questions)}[/cyan]\n"
        )

        # ── Per-topic accuracy ────────────────────────────────────────────────
        lines.append("[bold bright_white]  Per-Topic Accuracy[/bold bright_white]")
        lines.append("  [white]" + "─" * 50 + "[/white]")
        overall_c = overall_a = 0
        topic_accs = {}
        for t in range(1, 7):
            c, a = topic_accuracy(progress, t)
            overall_c += c
            overall_a += a
            topic_accs[t] = (c, a)
            pct_str = f"{c/a*100:3.0f}%" if a else " -- "
            pct_color = "bright_green" if a and c/a >= 0.6 else ("yellow" if a and c/a >= 0.3 else ("bright_red" if a else "white"))
            sel = "[bold cyan]▶[/bold cyan] " if t == app.selected_topic else "  "
            lines.append(
                f"{sel}[bold white]T{t}[/bold white]  {accuracy_bar(c, a, 16)}  "
                f"[{pct_color}]{pct_str}[/{pct_color}]  [bright_white]{TOPIC_SHORT[t]}[/bright_white]"
            )

        lines.append("  [white]" + "─" * 50 + "[/white]")
        if overall_a:
            opct = overall_c / overall_a * 100
            oc = "bright_green" if opct >= 60 else ("yellow" if opct >= 30 else "bright_red")
            bar_filled = round(opct / 100 * 30)
            bar = f"[{oc}]{'█' * bar_filled}[/{oc}][white]{'░' * (30 - bar_filled)}[/white]"
            lines.append(f"  [bold white]Overall Readiness:[/bold white]  {bar}  [{oc}]{opct:.0f}%[/{oc}]")
        else:
            lines.append("  [bold white]Overall Readiness:[/bold white]  [white]No data yet — start studying![/white]")

        # ── Leech count ───────────────────────────────────────────────────────
        leech_count = sum(
            1 for entry in progress.get("questions", {}).values()
            if entry.get("is_leech")
        )
        if leech_count:
            lines.append(
                f"\n  [bold bright_red]⚠  Leeches: {leech_count}[/bold bright_red]  "
                f"[white](wrong 5× in a row — use Weak Spots mode)[/white]"
            )

        # ── SRS 7-day forecast ────────────────────────────────────────────────
        forecast = srs_forecast(progress, questions, 7)
        max_c = max((c for _, c in forecast), default=1) or 1
        today = datetime.date.today()
        lines.append("\n  [bold bright_white]SRS Review Forecast[/bold bright_white]")
        lines.append("  [white]" + "─" * 50 + "[/white]")
        for dt, count in forecast:
            delta = (dt - today).days
            day_label = dt.strftime("%a %d")
            prefix = "[bold yellow]▶ Today  [/bold yellow]" if delta == 0 else f"[white]  +{delta}d {day_label}[/white]"
            bw = round(count / max_c * 18) if count else 0
            color = "yellow" if (delta == 0 and count) else ("cyan" if count else "white")
            bar = f"[{color}]{'█' * bw}[/{color}][white]{'░' * (18 - bw)}[/white]"
            cnt = f"[{color}]{count:>3}[/{color}]" if count else "[white]  0[/white]"
            lines.append(f"  {prefix}  {bar} {cnt}")

        # ── Selected topic hint ───────────────────────────────────────────────
        lines.append("")
        lines.append("  [white]" + "─" * 50 + "[/white]")
        if app.selected_topic:
            t = app.selected_topic
            c, a = topic_accs[t]
            pct = f" · {c/a*100:.0f}% accuracy" if a else ""
            lines.append(
                f"  [bold cyan]▶  Topic {t}: {TOPIC_HU.get(t, '')}[/bold cyan][white]{pct}[/white]"
            )
            lines.append(
                "  [bright_white]G[/bright_white][white]=Guide  [/white]"
                "[bright_white]L[/bright_white][white]=Learn  [/white]"
                "[bright_white]Q[/bright_white][white]=Quiz  [/white]"
                "[bright_white]M[/bright_white][white]=Multiple Choice  [/white]"
                "[bright_white]W[/bright_white][white]=Weak Spots[/white]"
            )
        else:
            lines.append(
                "  [bright_yellow]Select a topic (1–6) using the buttons or number keys[/bright_yellow]"
            )
            lines.append(
                "  [bright_white]G[/bright_white][white]=Guide  [/white]"
                "[bright_white]L[/bright_white][white]=Learn  [/white]"
                "[bright_white]Q[/bright_white][white]=Quiz  [/white]"
                "[bright_white]M[/bright_white][white]=Multiple Choice  [/white]"
                "[bright_white]E[/bright_white][white]=Exam[/white]"
            )

        # Update topic buttons: label + variant based on accuracy
        for t in range(1, 7):
            c, a = topic_accs[t]
            pct_str = f"{c/a*100:.0f}%" if a else "--"
            btn = self.query_one(f"#topic-{t}", Button)
            btn.label = f"T{t}  {TOPIC_SHORT[t][:13]:<13} {pct_str:>4}"
            if a and c / a >= 0.6:
                btn.variant = "success"
            elif a and c / a >= 0.3:
                btn.variant = "warning"
            elif a:
                btn.variant = "error"
            else:
                btn.variant = "default"

        self.query_one("#dashboard-content", Static).update("\n".join(lines))

    # ── Topic / mode helpers ──────────────────────────────────────────────────

    def _select_topic(self, t: int) -> None:
        self.app.selected_topic = t
        for i in range(1, 7):
            self.query_one(f"#topic-{i}", Button).variant = (
                "primary" if i == t else "default"
            )
        self.refresh_dashboard()

    def _launch(self, mode: str) -> None:
        app = self.app
        if mode in ("learn", "quiz", "mc", "guide") and not app.selected_topic:
            self.notify("Select a topic first (press 1–6)", severity="warning")
            return
        if mode == "guide":
            pool = list(get_questions_for_topic(app.questions, app.selected_topic))
            app.push_screen(StudyGuideScreen(pool, app.selected_topic))
        elif mode == "learn":
            pool = list(get_questions_for_topic(app.questions, app.selected_topic))
            qs = weighted_sample(pool, 20, app.progress)
            app.push_screen(LearnScreen(qs, app.selected_topic))
        elif mode == "quiz":
            pool = list(get_questions_for_topic(app.questions, app.selected_topic))
            qs = weighted_sample(pool, 20, app.progress)
            app.push_screen(QuizScreen(qs, "quiz", topic=app.selected_topic))
        elif mode == "mc":
            pool = list(get_questions_for_topic(app.questions, app.selected_topic))
            qs = weighted_sample(pool, 20, app.progress)
            app.push_screen(MultiChoiceScreen(qs, app.selected_topic))
        elif mode == "weak":
            qs = self._weak_questions()
            if not qs:
                self.notify("No weak spots — great work!", severity="information")
                return
            app.push_screen(QuizScreen(qs, "weak"))
        elif mode == "srs":
            qs = get_due_questions(app.progress, app.questions)
            if not qs:
                self.notify("No cards due today!", severity="information")
                return
            random.shuffle(qs)
            app.push_screen(QuizScreen(qs, "srs"))
        elif mode == "exam":
            app.push_screen(ExamBriefingScreen(self._exam_questions()))
        elif mode == "vocab":
            app.push_screen(VocabScreen(app.selected_topic))
        elif mode == "stats":
            app.push_screen(StatsScreen())

    def _weak_questions(self) -> list:
        q_data = self.app.progress.get("questions", {})
        qmap = {question_id(q["question_hu"]): q for q in self.app.questions}
        weak = []
        for qid, q in qmap.items():
            entry = q_data.get(qid)
            acc = entry["accuracy"] if entry else 0.0
            if entry is None or acc < 0.6:
                weak.append((acc, q))
        weak.sort(key=lambda x: x[0])
        if topic := self.app.selected_topic:
            weak = [(a, q) for a, q in weak if q.get("topic") == topic]
        return [q for _, q in weak]

    def _exam_questions(self) -> list:
        qs = []
        for t in range(1, 7):
            tqs = get_questions_for_topic(self.app.questions, t)
            qs.extend(random.sample(tqs, min(2, len(tqs))))
        random.shuffle(qs)
        return qs

    # ── Keyboard actions ──────────────────────────────────────────────────────

    def action_sel1(self): self._select_topic(1)
    def action_sel2(self): self._select_topic(2)
    def action_sel3(self): self._select_topic(3)
    def action_sel4(self): self._select_topic(4)
    def action_sel5(self): self._select_topic(5)
    def action_sel6(self): self._select_topic(6)

    def action_launch_guide(self):  self._launch("guide")
    def action_launch_learn(self):  self._launch("learn")
    def action_launch_quiz(self):   self._launch("quiz")
    def action_launch_mc(self):     self._launch("mc")
    def action_launch_weak(self):   self._launch("weak")
    def action_launch_exam(self):   self._launch("exam")
    def action_launch_stats(self):  self._launch("stats")

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid and bid.startswith("topic-"):
            self._select_topic(int(bid.split("-")[1]))
            return
        mode_map = {
            "mode-guide": "guide",
            "mode-learn": "learn", "mode-quiz": "quiz",  "mode-mc":    "mc",
            "mode-weak":  "weak",  "mode-srs":  "srs",   "mode-exam":  "exam",
            "mode-vocab": "vocab", "mode-stats": "stats",
        }
        if bid in mode_map:
            self._launch(mode_map[bid])


# ── Confirm Screen ────────────────────────────────────────────────────────────


class ConfirmScreen(ModalScreen):
    """Modal dialog asking the user to confirm leaving mid-session."""

    def __init__(self, message: str = "Leave this session? Progress will not be saved.") -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Static(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes, leave", id="btn-confirm-yes", variant="error")
                yield Button("No, stay",   id="btn-confirm-no",  variant="primary")

    def on_mount(self) -> None:
        self.query_one("#confirm-dialog").border_title = " ⚠  Confirm "

    @on(Button.Pressed, "#btn-confirm-yes")
    def on_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-confirm-no")
    def on_no(self) -> None:
        self.dismiss(False)


# ── Learn Screen ──────────────────────────────────────────────────────────────


class LearnScreen(Screen):
    """Card-by-card: question → reveal → self-rate (feeds SRS)."""

    BINDINGS = [
        Binding("space",  "reveal",     "Reveal",      show=True),
        Binding("r",      "reveal",     "Reveal",      show=False),
        Binding("1",      "rate_bad",   "1 Didn't know", show=True),
        Binding("3",      "rate_ok",    "3 Got it",    show=True),
        Binding("5",      "rate_good",  "5 Easy",      show=True),
        Binding("s",      "skip",       "Skip",        show=True),
        Binding("right",  "next_card",  "Next",        show=False),
        Binding("left",   "prev_card",  "Prev",        show=False),
        Binding("escape", "go_home",    "Home"),
    ]

    def __init__(self, questions: list, topic: int) -> None:
        super().__init__()
        self.questions = list(questions)
        self.topic = topic
        self.idx = 0
        self.revealed = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="learn-layout"):
            yield Static(id="learn-progress", classes="section-title")
            yield ProgressBar(total=len(self.questions), id="session-bar", show_eta=False)
            yield Rule()
            with ScrollableContainer(id="card-area"):
                yield Static(id="card-question", classes="question-text")
                yield Button("Reveal Answer  [Space / R]", id="btn-reveal", variant="primary")
                yield Static(id="card-answer",   classes="answer-text")
                yield Static(id="card-keywords", classes="keywords-text")
                with Horizontal(id="rating-row"):
                    yield Button("1  Didn't know", id="btn-rate-1", variant="error")
                    yield Button("2  Almost",      id="btn-rate-2", variant="warning")
                    yield Button("3  Got it!",     id="btn-rate-3", variant="success")
                    yield Button("Skip  [S]",      id="btn-skip",   variant="default")
            yield Rule()
            with Horizontal(id="learn-nav"):
                yield Button("← Prev",  id="btn-prev", variant="default")
                yield Button("⌂ Home",  id="btn-home", variant="warning")
        yield Footer()

    def on_mount(self) -> None:
        self._show_card()

    def _show_card(self) -> None:
        q = self.questions[self.idx]
        total = len(self.questions)
        diff = {1: "★☆☆", 2: "★★☆", 3: "★★★"}.get(q.get("difficulty", 1), "★☆☆")
        t_name = TOPIC_SHORT.get(self.topic, "")

        self.query_one("#session-bar", ProgressBar).update(progress=self.idx)
        self.query_one("#learn-progress", Static).update(
            f"[bold]📖  Learn[/bold]  [dim]Topic {self.topic}: {t_name}[/dim]  "
            f"[yellow]{diff}[/yellow]"
        )
        card_area = self.query_one("#card-area")
        card_area.border_title = f" Card {self.idx + 1} / {total} "

        self.query_one("#card-question", Static).update(
            f"\n[bold cyan]🇭🇺  {q['question_hu']}[/bold cyan]\n\n"
            f"[dim]🇬🇧  {q['question_en']}[/dim]\n"
        )
        self.query_one("#card-answer",   Static).update("")
        self.query_one("#card-keywords", Static).update("")
        self.query_one("#btn-reveal",    Button).display = True
        self.query_one("#rating-row",    Horizontal).display = False
        self.revealed = False

    def _reveal(self) -> None:
        q = self.questions[self.idx]
        kws = q.get("keywords_hu", [])
        if isinstance(kws, str):
            kws = [k.strip() for k in kws.split(",") if k.strip()]
        kw_rich = "  ".join(f"[bold magenta]{k}[/bold magenta]" for k in kws)

        self.query_one("#card-answer", Static).update(
            f"\n[bold green]🇭🇺  {q['answer_hu']}[/bold green]\n\n"
            f"[dim]🇬🇧  {q['answer_en']}[/dim]\n"
        )
        kw_line = (
            f"[dim]Keywords:[/dim]  {kw_rich}\n\n" if kw_rich else "\n"
        )
        self.query_one("#card-keywords", Static).update(
            kw_line +
            "[dim]Rate yourself:  "
            "[red]1[/red] Didn't know  ·  "
            "[yellow]2[/yellow] Almost  ·  "
            "[green]3[/green] Got it![/dim]"
        )
        self.query_one("#btn-reveal",  Button).display = False
        self.query_one("#rating-row",  Horizontal).display = True
        self.query_one("#card-area").border_title = " ✦ Answer revealed — rate yourself "
        self.revealed = True

    def _rate(self, quality: int) -> None:
        """Record SRS rating and advance to next card."""
        if not self.revealed:
            return
        q = self.questions[self.idx]
        qid = question_id(q["question_hu"])
        update_srs(self.app.progress, qid, quality)
        save_progress(self.app.progress, PROGRESS_FILE)

        srs_entry = self.app.progress.get("srs", {}).get(qid, {})
        interval = srs_entry.get("interval", 1)
        labels = {1: "✘ Didn't know", 3: "~ Almost", 5: "✓ Got it!"}
        self.notify(
            f"{labels.get(quality, '')} — next review in {interval} day(s)",
            timeout=1.5,
        )

        self.idx += 1
        if self.idx >= len(self.questions):
            record_session(
                self.app.progress, "learn", 0, len(self.questions), self.topic
            )
            save_progress(self.app.progress, PROGRESS_FILE)
            self.notify("All cards reviewed!", severity="information")
            self.app.pop_screen()
        else:
            self._show_card()

    # ── Keyboard actions ──────────────────────────────────────────────────────

    def action_reveal(self) -> None:
        if not self.revealed:
            self._reveal()

    def action_rate_bad(self) -> None:
        """Rate as 'Didn't know' (quality 1) — only fires after reveal."""
        if self.revealed:
            self._rate(1)

    def action_rate_ok(self) -> None:
        """Rate as 'Got it' (quality 3) — only fires after reveal."""
        if self.revealed:
            self._rate(3)

    def action_rate_good(self) -> None:
        """Rate as 'Easy' (quality 5) — only fires after reveal."""
        if self.revealed:
            self._rate(5)

    def action_next_card(self) -> None:
        if not self.revealed:
            self._reveal()
        else:
            self._rate(3)   # neutral rating if user just presses →

    def action_prev_card(self) -> None:
        if self.idx > 0:
            self.idx -= 1
            self._show_card()

    def action_skip(self) -> None:
        """Skip the current card without updating SRS."""
        self.idx += 1
        if self.idx >= len(self.questions):
            record_session(
                self.app.progress, "learn", 0, len(self.questions), self.topic
            )
            save_progress(self.app.progress, PROGRESS_FILE)
            self.notify("All cards reviewed!", severity="information")
            self.app.pop_screen()
        else:
            self._show_card()

    def action_go_home(self) -> None:
        if self.idx > 0:
            def _handle_confirm(confirmed: bool) -> None:
                if confirmed:
                    self.app.pop_screen()
            self.app.push_screen(ConfirmScreen(), _handle_confirm)
        else:
            self.app.pop_screen()

    # ── Button handlers ───────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-reveal")
    def on_reveal(self) -> None:
        self._reveal()

    @on(Button.Pressed, "#btn-rate-1")
    def on_rate1(self) -> None:
        self._rate(1)

    @on(Button.Pressed, "#btn-rate-2")
    def on_rate2(self) -> None:
        self._rate(3)

    @on(Button.Pressed, "#btn-rate-3")
    def on_rate3(self) -> None:
        self._rate(5)

    @on(Button.Pressed, "#btn-prev")
    def on_prev(self) -> None:
        self.action_prev_card()

    @on(Button.Pressed, "#btn-skip")
    def on_skip(self) -> None:
        self.action_skip()

    @on(Button.Pressed, "#btn-home")
    def on_home(self) -> None:
        self.action_go_home()


# ── Quiz Screen ───────────────────────────────────────────────────────────────


class QuizScreen(Screen):
    """Free-text quiz for quiz / weak / srs / exam modes. Has hint button."""

    BINDINGS = [
        Binding("escape", "go_back",         "Back"),
        Binding("h",      "hint",            "Hint",        show=True),
        Binding("enter",  "submit_or_next",  "Submit/Next", show=True),
    ]

    def __init__(
        self,
        questions: list,
        mode: str,
        topic: int = None,
        is_exam: bool = False,
    ) -> None:
        super().__init__()
        self.questions = list(questions)
        self.mode = mode
        self.topic = topic
        self.is_exam = is_exam
        self.idx = 0
        self.total_score = 0.0
        self.answered = False
        self.hint_used = False
        self.exam_start: float = None
        self.exam_duration = 60 * 60

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="quiz-layout"):
            yield Static(id="quiz-header", classes="section-title")
            yield ProgressBar(total=len(self.questions), id="session-bar", show_eta=False)
            yield Rule()
            with ScrollableContainer(id="quiz-area"):
                yield Static(id="quiz-question", classes="question-text")
                yield Input(
                    placeholder="Type your answer in Hungarian…",
                    id="answer-input",
                )
                with Horizontal(id="quiz-buttons"):
                    yield Button("Submit  [Enter]", id="btn-submit", variant="primary")
                    yield Button("Hint  [H]",       id="btn-hint",   variant="default")
                    yield Button("Next →",          id="btn-next",   variant="success")
                yield Static(id="quiz-feedback", classes="feedback-text")
            yield Rule()
            with Horizontal(id="quiz-nav"):
                yield Button("⌂ Home  [Esc]", id="btn-back", variant="warning")
        yield Footer()

    def on_mount(self) -> None:
        if self.is_exam:
            self.exam_start = time.time()
            self.set_interval(1.0, self._tick_timer)
        self._show_question()

    # ── Timer ─────────────────────────────────────────────────────────────────

    def _tick_timer(self) -> None:
        if not self.is_exam or self.exam_start is None:
            return
        remaining = max(0.0, self.exam_duration - (time.time() - self.exam_start))
        if remaining <= 0:
            self.notify("Time's up!", severity="error")
            self._finish()
            return
        m, s = divmod(int(remaining), 60)
        tc = "green" if remaining > 600 else ("yellow" if remaining > 120 else "red")
        total = len(self.questions)
        self.query_one("#quiz-header", Static).update(
            f"[bold]Mock Exam[/bold]  [dim]Q {self.idx + 1}/{total}[/dim]  "
            f"[{tc}]⏱ {m:02d}:{s:02d}[/{tc}]"
        )

    def _mode_label(self) -> str:
        return {"quiz": "Quiz", "weak": "Weak Spots",
                "srs": "SRS Review", "exam": "Mock Exam"}.get(self.mode, self.mode.title())

    # ── Display ───────────────────────────────────────────────────────────────

    def _show_question(self) -> None:
        if self.idx >= len(self.questions):
            self._finish()
            return

        q = self.questions[self.idx]
        total = len(self.questions)
        diff = {1: "★", 2: "★★", 3: "★★★"}.get(
            q.get("difficulty", 1), "★"
        )
        self.query_one("#session-bar", ProgressBar).update(progress=self.idx)
        t_num = q.get("topic", "?")
        t_name = TOPIC_SHORT.get(t_num, f"Topic {t_num}")

        diff = {1: "★☆☆", 2: "★★☆", 3: "★★★"}.get(q.get("difficulty", 1), "★☆☆")
        pct_done = self.idx / total * 100 if total else 0

        if not self.is_exam:
            self.query_one("#quiz-header", Static).update(
                f"[bold]{self._mode_label()}[/bold]  "
                f"[dim]Q {self.idx + 1}/{total}  ·  "
                f"Score: {self.total_score:.1f}  ·  "
                f"{pct_done:.0f}% done[/dim]"
            )

        quiz_area = self.query_one("#quiz-area")
        quiz_area.border_title = f" {self._mode_label()} — Q {self.idx + 1} / {total} "

        self.query_one("#quiz-question", Static).update(
            f"[dim]Topic {t_num}: {t_name}  {diff}[/dim]\n\n"
            f"[bold cyan]🇭🇺  {q['question_hu']}[/bold cyan]\n\n"
            f"[dim]🇬🇧  {q['question_en']}[/dim]"
        )
        self.query_one("#quiz-feedback", Static).update("")

        inp = self.query_one("#answer-input", Input)
        inp.value = ""
        inp.placeholder = "Írja ide a választ magyarul… / Type the answer in Hungarian…"
        inp.focus()

        self.query_one("#btn-submit", Button).display = True
        self.query_one("#btn-hint",   Button).display = not self.is_exam
        self.query_one("#btn-next",   Button).display = False
        self.answered = False
        self.hint_used = False

    # ── Hint ──────────────────────────────────────────────────────────────────

    def _show_hint(self) -> None:
        if self.is_exam:
            return
        if self.answered or self.hint_used:
            return
        self.hint_used = True
        q = self.questions[self.idx]
        kws = q.get("keywords_hu", [])
        if isinstance(kws, str):
            kws = [k.strip() for k in kws.split(",") if k.strip()]
        masked = "   ".join(mask_keyword(kw) for kw in kws)
        self.query_one("#quiz-feedback", Static).update(
            f"[dim]Hint (−20% score penalty):[/dim]  [yellow]{masked}[/yellow]"
        )
        self.query_one("#btn-hint", Button).display = False

    # ── Submit ────────────────────────────────────────────────────────────────

    def _submit(self) -> None:
        if self.answered:
            return
        q = self.questions[self.idx]
        user_answer = self.query_one("#answer-input", Input).value.strip()

        kws = q.get("keywords_hu", [])
        if isinstance(kws, str):
            kws = [k.strip() for k in kws.split(",") if k.strip()]

        sc, matched, missed = score_answer_tolerant(user_answer, kws)
        if self.hint_used:
            sc *= 0.8

        self.total_score += sc
        self.answered = True

        record_attempt(self.app.progress, q, sc)
        qid = question_id(q["question_hu"])
        is_correct = sc >= 0.6
        update_leech(self.app.progress, qid, is_correct)
        update_srs(self.app.progress, qid, srs_quality(sc))
        save_progress(self.app.progress, PROGRESS_FILE)

        if sc >= 0.6:
            result = f"[bold green] ✔  Correct!  {sc * 100:.0f}% [/bold green]"
            quiz_title = " ✔ Correct "
        elif sc >= 0.3:
            result = f"[bold yellow] ~  Partial  {sc * 100:.0f}% [/bold yellow]"
            quiz_title = " ~ Partial "
        else:
            result = f"[bold red] ✘  Incorrect  {sc * 100:.0f}% [/bold red]"
            quiz_title = " ✘ Incorrect "

        self.query_one("#quiz-area").border_title = quiz_title
        hint_note = "  [dim](−20% hint penalty)[/dim]" if self.hint_used else ""
        srs_entry = self.app.progress.get("srs", {}).get(qid, {})
        interval = srs_entry.get("interval", 1)
        matched_line = f"\n[green]  ✔  Matched:  {', '.join(matched)}[/green]" if matched else ""
        missed_line  = f"\n[red]  ✘  Missed:   {', '.join(missed)}[/red]"      if missed  else ""

        self.query_one("#quiz-feedback", Static).update(
            f"{result}{hint_note}\n\n"
            f"[bold]Correct answer:[/bold]\n"
            f"[bold green]🇭🇺  {q['answer_hu']}[/bold green]\n"
            f"[dim]🇬🇧  {q['answer_en']}[/dim]"
            f"{matched_line}{missed_line}\n\n"
            f"[dim]Next SRS review in {interval} day(s)  ·  Press Enter for next →[/dim]"
        )

        self.query_one("#btn-submit", Button).display = False
        self.query_one("#btn-hint",   Button).display = False
        self.query_one("#btn-next",   Button).display = True

    # ── Finish ────────────────────────────────────────────────────────────────

    def _finish(self) -> None:
        total = len(self.questions)
        if self.mode == "exam":
            pts = self.total_score / total * 30 if total else 0
            passed = pts >= 16
            record_session(self.app.progress, "exam", pts, 30)
            save_progress(self.app.progress, PROGRESS_FILE)
            self.notify(
                f"Exam done — {pts:.1f}/30 pts — {'PASSED ✔' if passed else 'FAILED ✘'}",
                severity="information" if passed else "error",
            )
        else:
            pct = self.total_score / total * 100 if total else 0
            record_session(self.app.progress, self.mode, self.total_score, total, self.topic)
            save_progress(self.app.progress, PROGRESS_FILE)
            self.notify(
                f"{self._mode_label()} done!  {self.total_score:.1f}/{total} ({pct:.0f}%)",
                severity="information",
            )
        self.app.pop_screen()

    # ── Keyboard actions ──────────────────────────────────────────────────────

    def action_go_back(self) -> None:
        if self.idx > 0:
            def _handle_confirm(confirmed: bool) -> None:
                if confirmed:
                    self.app.pop_screen()
            self.app.push_screen(ConfirmScreen(), _handle_confirm)
        else:
            self.app.pop_screen()

    def action_hint(self) -> None:
        self._show_hint()

    def action_submit_or_next(self) -> None:
        """Submit answer if not yet answered; advance to next question if already answered."""
        if not self.answered:
            self._submit()
        else:
            self.idx += 1
            self._show_question()

    # ── Button / Input handlers ───────────────────────────────────────────────

    @on(Button.Pressed, "#btn-submit")
    def on_submit_btn(self) -> None:
        self._submit()

    @on(Button.Pressed, "#btn-hint")
    def on_hint_btn(self) -> None:
        self._show_hint()

    @on(Input.Submitted, "#answer-input")
    def on_enter(self) -> None:
        if not self.answered:
            self._submit()
        else:
            self.idx += 1
            self._show_question()

    @on(Button.Pressed, "#btn-next")
    def on_next(self) -> None:
        self.idx += 1
        self._show_question()

    @on(Button.Pressed, "#btn-back")
    def on_back(self) -> None:
        self.action_go_back()


# ── Multiple Choice Screen ────────────────────────────────────────────────────


class MultiChoiceScreen(Screen):
    """4-option multiple choice — press 1-4 or click to answer."""

    BINDINGS = [
        Binding("1", "pick1", "A", show=True),
        Binding("2", "pick2", "B", show=True),
        Binding("3", "pick3", "C", show=True),
        Binding("4", "pick4", "D", show=True),
        Binding("enter",  "next_q",  "Next",  show=False),
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, questions: list, topic: int) -> None:
        super().__init__()
        self.questions = list(questions)
        self.topic = topic
        self.idx = 0
        self.score = 0
        self.answered = False
        self.options: list = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="mc-layout"):
            yield Static(id="mc-header", classes="section-title")
            yield Rule()
            with ScrollableContainer(id="mc-area"):
                yield Static(id="mc-question", classes="question-text")
                with Vertical(id="mc-options"):
                    yield Button("", id="mc-opt-1", classes="mc-opt")
                    yield Button("", id="mc-opt-2", classes="mc-opt")
                    yield Button("", id="mc-opt-3", classes="mc-opt")
                    yield Button("", id="mc-opt-4", classes="mc-opt")
                yield Static(id="mc-feedback", classes="feedback-text")
            yield Rule()
            with Horizontal(id="mc-nav"):
                yield Button("Next →  [Enter]", id="btn-next", variant="success")
                yield Button("⌂ Home  [Esc]",   id="btn-back", variant="warning")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#btn-next", Button).display = False
        self._show_question()

    def _show_question(self) -> None:
        if self.idx >= len(self.questions):
            self._finish()
            return

        q = self.questions[self.idx]
        total = len(self.questions)
        self.options = build_mc_options(q, self.app.questions)
        self.answered = False

        t_num = q.get("topic", "?")
        t_name = TOPIC_SHORT.get(t_num, f"Topic {t_num}")
        self.query_one("#mc-header", Static).update(
            f"[bold]Multiple Choice[/bold]  [dim]Q {self.idx + 1}/{total}[/dim]  "
            f"[dim]Score: {self.score}/{self.idx}[/dim]  "
            f"[dim]Topic {t_num}: {t_name}[/dim]"
        )
        self.query_one("#mc-question", Static).update(
            f"[bold cyan]🇭🇺 {q['question_hu']}[/bold cyan]\n"
            f"[dim]🇬🇧 {q['question_en']}[/dim]"
        )
        self.query_one("#mc-feedback", Static).update("")

        labels = ["A", "B", "C", "D"]
        for i, (text, _) in enumerate(self.options):
            btn = self.query_one(f"#mc-opt-{i + 1}", Button)
            display = f"{i + 1}.  {labels[i]})  {text}"
            btn.label = display
            btn.variant = "default"

        self.query_one("#btn-next", Button).display = False

    def _pick(self, idx: int) -> None:
        if self.answered or idx >= len(self.options):
            return
        self.answered = True

        text, is_correct = self.options[idx]
        q = self.questions[self.idx]

        # Colour the buttons
        for i, (_, correct) in enumerate(self.options):
            btn = self.query_one(f"#mc-opt-{i + 1}", Button)
            if correct:
                btn.variant = "success"
            elif i == idx and not is_correct:
                btn.variant = "error"

        sc = 1.0 if is_correct else 0.0
        if is_correct:
            self.score += 1

        record_attempt(self.app.progress, q, sc)
        qid = question_id(q["question_hu"])
        update_leech(self.app.progress, qid, is_correct)
        update_srs(self.app.progress, qid, 5 if is_correct else 0)
        save_progress(self.app.progress, PROGRESS_FILE)

        if is_correct:
            self.query_one("#mc-feedback", Static).update(
                "[bold green]✔  Correct![/bold green]"
            )
        else:
            correct_text = next(t for t, c in self.options if c)
            self.query_one("#mc-feedback", Static).update(
                f"[bold red]✘  Wrong.[/bold red]  "
                f"Correct: [green]{correct_text}[/green]"
            )

        self.query_one("#btn-next", Button).display = True

    def _finish(self) -> None:
        total = len(self.questions)
        pct = self.score / total * 100 if total else 0
        record_session(self.app.progress, "mc", self.score, total, self.topic)
        save_progress(self.app.progress, PROGRESS_FILE)
        self.notify(
            f"Multiple Choice done!  {self.score}/{total} ({pct:.0f}%)",
            severity="information",
        )
        self.app.pop_screen()

    # ── Keyboard actions ──────────────────────────────────────────────────────

    def action_pick1(self): self._pick(0)
    def action_pick2(self): self._pick(1)
    def action_pick3(self): self._pick(2)
    def action_pick4(self): self._pick(3)

    def action_next_q(self) -> None:
        if self.answered:
            self.idx += 1
            self._show_question()

    def action_go_back(self) -> None:
        if self.idx > 0:
            def _handle_confirm(confirmed: bool) -> None:
                if confirmed:
                    self.app.pop_screen()
            self.app.push_screen(ConfirmScreen(), _handle_confirm)
        else:
            self.app.pop_screen()

    # ── Button handlers ───────────────────────────────────────────────────────

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid and bid.startswith("mc-opt-"):
            self._pick(int(bid.split("-")[-1]) - 1)
        elif bid == "btn-next":
            self.idx += 1
            self._show_question()
        elif bid == "btn-back":
            self.action_go_back()


# ── Vocab Screen ──────────────────────────────────────────────────────────────


class VocabScreen(Screen):
    """Flip-card vocabulary drill."""

    BINDINGS = [
        Binding("space",  "flip",    "Flip"),
        Binding("y",      "correct", "Correct"),
        Binding("n",      "wrong",   "Wrong"),
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, topic: int = None) -> None:
        super().__init__()
        self.topic = topic
        self.cards: list = []
        self.idx = 0
        self.correct = 0
        self.total = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="vocab-layout"):
            yield Static(id="vocab-progress", classes="section-title")
            yield Rule()
            with ScrollableContainer(id="vocab-card"):
                yield Static(id="vocab-front",  classes="question-text")
                yield Button("Flip Card  [Space]", id="btn-flip", variant="primary")
                yield Static(id="vocab-back",   classes="answer-text")
                with Horizontal(id="vocab-rate"):
                    yield Button("Wrong  [N]",   id="btn-wrong",   variant="error")
                    yield Button("Correct  [Y]", id="btn-correct", variant="success")
            yield Rule()
            with Horizontal(id="vocab-nav"):
                yield Button("⌂ Home  [Esc]", id="btn-back", variant="warning")
        yield Footer()

    def on_mount(self) -> None:
        qs = self.app.questions
        if self.topic:
            qs = get_questions_for_topic(qs, self.topic)
        seen: set = set()
        for q in qs:
            kws = q.get("keywords_hu", [])
            if isinstance(kws, str):
                kws = [k.strip() for k in kws.split(",") if k.strip()]
            for kw in kws:
                if kw not in seen:
                    seen.add(kw)
                    self.cards.append({
                        "keyword_hu": kw,
                        "question_en": q["question_en"],
                        "answer_en": q["answer_en"],
                    })
        random.shuffle(self.cards)
        self._show_card()

    def _show_card(self) -> None:
        if not self.cards:
            self.notify("No vocab cards.", severity="warning")
            self.app.pop_screen()
            return
        card = self.cards[self.idx]
        total = len(self.cards)
        self.query_one("#vocab-progress", Static).update(
            f"[bold]Vocab Drill[/bold]  [dim]Card {self.idx + 1}/{total}[/dim]  "
            f"[green]{self.correct}[/green] correct / {self.total} answered"
        )
        self.query_one("#vocab-front", Static).update(
            f"[dim]English context:[/dim]\n[cyan]{card['question_en']}[/cyan]\n\n"
            f"[dim]Answer context:[/dim]\n[dim]{card['answer_en']}[/dim]"
        )
        self.query_one("#vocab-back",  Static).update("")
        self.query_one("#btn-flip",    Button).display = True
        self.query_one("#vocab-rate",  Horizontal).display = False

    def _flip(self) -> None:
        card = self.cards[self.idx]
        self.query_one("#vocab-back", Static).update(
            f"\n[bold]Hungarian keyword:[/bold]\n"
            f"[bold white]{card['keyword_hu']}[/bold white]"
        )
        self.query_one("#btn-flip",   Button).display = False
        self.query_one("#vocab-rate", Horizontal).display = True

    def _next(self, is_correct: bool) -> None:
        card = self.cards[self.idx]
        record_vocab_attempt(self.app.progress, card["keyword_hu"], is_correct)
        save_progress(self.app.progress, PROGRESS_FILE)
        self.total += 1
        if is_correct:
            self.correct += 1
        self.idx += 1
        if self.idx >= len(self.cards):
            pct = self.correct / self.total * 100 if self.total else 0
            record_session(self.app.progress, "vocab", self.correct, self.total, self.topic)
            save_progress(self.app.progress, PROGRESS_FILE)
            self.notify(f"Vocab done!  {self.correct}/{self.total} ({pct:.0f}%)")
            self.app.pop_screen()
        else:
            self._show_card()

    def action_flip(self):    self._flip()
    def action_correct(self): self._next(True)
    def action_wrong(self):   self._next(False)
    def action_go_back(self): self.app.pop_screen()

    @on(Button.Pressed, "#btn-flip")
    def on_flip(self) -> None:    self._flip()
    @on(Button.Pressed, "#btn-correct")
    def on_correct(self) -> None:  self._next(True)
    @on(Button.Pressed, "#btn-wrong")
    def on_wrong(self) -> None:    self._next(False)
    @on(Button.Pressed, "#btn-back")
    def on_back(self) -> None:     self.app.pop_screen()


# ── Stats Screen ──────────────────────────────────────────────────────────────


class StatsScreen(Screen):
    """Full statistics dashboard."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer(id="stats-scroll"):
            yield Static(id="stats-content")
        with Horizontal(id="stats-nav"):
            yield Button("⌂ Home  [Esc]", id="btn-back", variant="warning")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        progress = self.app.progress
        sessions = progress.get("sessions", [])
        q_data = progress.get("questions", {})
        srs_data = progress.get("srs", {})
        lines: list = []

        lines.append("[bold]Study Statistics — Tanulási Statisztika[/bold]")
        lines.append("═" * 50)
        lines.append(f"\n[bold]Total Sessions:[/bold]  {len(sessions)}")

        streak = study_streak(progress)
        lines.append(f"[bold]Study Streak:[/bold]    [green]{streak} day(s)[/green]")

        session_dates: set = set()
        for s in sessions:
            try:
                session_dates.add(datetime.datetime.fromisoformat(s["date"]).date())
            except (ValueError, KeyError):
                pass
        lines.append(f"[bold]Unique Days:[/bold]     {len(session_dates)}")
        if sessions:
            try:
                last = datetime.datetime.fromisoformat(sessions[-1]["date"])
                lines.append(f"[bold]Last Session:[/bold]    {last.strftime('%Y-%m-%d %H:%M')}")
            except (ValueError, KeyError):
                pass

        lines.append("\n[bold]Per-Topic Accuracy[/bold]")
        lines.append("─" * 50)
        recommend_topic = None
        worst_acc = 1.0
        for t in range(1, 7):
            c, a = topic_accuracy(progress, t)
            lines.append(f"  T{t}  {accuracy_bar(c, a, 20)}  {TOPIC_SHORT[t]}  ({c}/{a})")
            if a > 0:
                acc = c / a
                if acc < worst_acc:
                    worst_acc = acc
                    recommend_topic = t
            elif worst_acc > 0:
                worst_acc = 0.0
                recommend_topic = t

        if srs_data:
            today = datetime.date.today().isoformat()
            due_today = sum(
                1 for e in srs_data.values()
                if not e.get("due") or e["due"] <= today
            )
            avg_ivl = sum(e.get("interval", 0) for e in srs_data.values()) / len(srs_data)
            lines.append("\n[bold]Spaced Repetition (SRS)[/bold]")
            lines.append("─" * 50)
            lines.append(f"  Cards tracked:  {len(srs_data)}")
            lines.append(f"  Due today:      [yellow]{due_today}[/yellow]")
            lines.append(f"  Avg interval:   {avg_ivl:.1f} days")

        exam_sessions = [s for s in sessions if s.get("mode") == "exam"]
        if exam_sessions:
            lines.append("\n[bold]Mock Exam History[/bold]")
            lines.append("─" * 50)
            for es in exam_sessions[-6:]:
                try:
                    dt = datetime.datetime.fromisoformat(es["date"]).strftime("%Y-%m-%d")
                except (ValueError, KeyError):
                    dt = "?"
                pts = es.get("score", 0)
                status = "[green]PASSED[/green]" if pts >= 16 else "[red]FAILED[/red]"
                lines.append(f"  {dt}  {pts:.1f}/30  {status}")

        lines.append("\n[bold]Most Missed Questions[/bold]")
        lines.append("─" * 50)
        missed = sorted(
            [e for e in q_data.values() if e.get("attempts", 0) > 0 and e.get("accuracy", 1.0) < 0.6],
            key=lambda x: x.get("accuracy", 0),
        )
        if missed:
            for m in missed[:5]:
                acc = m.get("accuracy", 0) * 100
                t = m.get("topic", "?")
                qtext = m.get("question_hu", "?")[:55]
                lines.append(f"  [red]{acc:.0f}%[/red]  [T{t}]  {qtext}")
        else:
            lines.append("  [green]No frequently missed questions — great work![/green]")

        # Enhancement 2: Leech Cards section
        leech_entries = [
            entry for entry in q_data.values() if entry.get("is_leech")
        ]
        lines.append("\n[bold red]Leech Cards[/bold red]  [dim](wrong 5x in a row)[/dim]")
        lines.append("─" * 50)
        if leech_entries:
            display = leech_entries[:10]
            for le in display:
                qtext = le.get("question_hu", "?")[:60]
                lines.append(f"  [red]•[/red] {qtext}")
            if len(leech_entries) > 10:
                lines.append(f"  [dim]…and {len(leech_entries) - 10} more[/dim]")
        else:
            lines.append("  [green]No leeches — great consistency![/green]")

        # Enhancement 6: Recent Sessions chart
        recent_sessions = sessions[-10:][::-1]  # last 10, newest first
        if recent_sessions:
            lines.append("\n[bold]Recent Sessions[/bold]")
            lines.append("─" * 50)
            for sess in recent_sessions:
                try:
                    date_str = datetime.datetime.fromisoformat(sess["date"]).strftime("%Y-%m-%d")
                except (ValueError, KeyError):
                    date_str = "?"
                mode_label = sess.get("mode", "?").title()
                topic_val = sess.get("topic", "")
                if topic_val:
                    mode_display = f"{mode_label} — T{topic_val}"
                else:
                    mode_display = mode_label
                raw_score = sess.get("score", 0)
                total_val = sess.get("total", 1) or 1
                # Normalise score to 0-100 percent
                if sess.get("mode") == "exam":
                    # exam score is already points out of 30
                    pct_int = int(raw_score / 30 * 100)
                else:
                    pct_int = int(raw_score / total_val * 100)
                pct_int = max(0, min(100, pct_int))
                filled = round(pct_int / 10)
                bar = "█" * filled + "░" * (10 - filled)
                if pct_int >= 80:
                    color = "green"
                elif pct_int >= 60:
                    color = "yellow"
                else:
                    color = "red"
                lines.append(
                    f"  {date_str}  {mode_display:<16}  "
                    f"[{color}]{bar}[/{color}]  [{color}]{pct_int}%[/{color}]"
                )

        if recommend_topic:
            tname = TOPIC_SHORT.get(recommend_topic, f"Topic {recommend_topic}")
            lines.append(f"\n[bold cyan]Recommendation:[/bold cyan]  "
                         f"Topic {recommend_topic}: {tname}")

        self.query_one("#stats-content", Static).update("\n".join(lines))

    def action_go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-back")
    def on_back(self) -> None:
        self.app.pop_screen()


# ── Exam Briefing Screen ──────────────────────────────────────────────────────


class ExamBriefingScreen(Screen):
    """Briefing screen shown before the mock exam starts."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, exam_questions: list) -> None:
        super().__init__()
        self.exam_questions = exam_questions

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="briefing-layout"):
            yield Static(
                "[bold]📋 Mock Exam[/bold]",
                id="briefing-title",
                classes="section-title",
            )
            yield Rule()
            yield Static(
                "\n[bold]Rules:[/bold]\n"
                "  • 30 questions · 2 per topic · 45 minutes · Pass: 60%\n\n"
                "[dim]Hints are disabled during the exam.[/dim]\n",
                id="briefing-rules",
            )
            yield Button("Start Exam", id="btn-start-exam", variant="primary")
            yield Button("⌂ Back  [Esc]", id="btn-back", variant="warning")
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-start-exam")
    def on_start(self) -> None:
        self.app.pop_screen()
        self.app.push_screen(QuizScreen(self.exam_questions, "exam", is_exam=True))

    @on(Button.Pressed, "#btn-back")
    def on_back(self) -> None:
        self.app.pop_screen()


# ── Study Guide Screen ────────────────────────────────────────────────────────


class StudyGuideScreen(Screen):
    """Bilingual study guide: READ the material first, then jump to practice.

    Left column = Magyar (Hungarian), Right column = English.
    Includes topic overview + Authors & Works reference for Topic 3.
    """

    BINDINGS = [
        Binding("escape", "go_back",      "Home"),
        Binding("l",      "launch_learn", "Flashcards"),
        Binding("q",      "launch_quiz",  "Quiz"),
        Binding("m",      "launch_mc",    "MC"),
    ]

    def __init__(self, questions: list, topic: int) -> None:
        super().__init__()
        self.questions = list(questions)
        self.topic = topic

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="guide-layout"):
            yield Static(id="guide-header", classes="section-title")
            with Horizontal(id="guide-actions"):
                yield Button("📖  Flashcards  [L]",      id="btn-guide-learn", variant="primary")
                yield Button("❓  Quiz  [Q]",             id="btn-guide-quiz",  variant="success")
                yield Button("🔢  Multiple Choice  [M]",  id="btn-guide-mc",    variant="default")
                yield Button("⌂  Home  [Esc]",            id="btn-guide-home",  variant="warning")
            yield Rule()
            with Horizontal(id="guide-columns"):
                with ScrollableContainer(id="guide-col-hu"):
                    yield Static(
                        "[bold cyan]🇭🇺  MAGYAR  —  olvasd el, majd gyakorolj![/bold cyan]",
                        classes="guide-col-title",
                    )
                    yield Static(id="guide-hu-content")
                with ScrollableContainer(id="guide-col-en"):
                    yield Static(
                        "[bold white]🇬🇧  ENGLISH  —  read it, then practise![/bold white]",
                        classes="guide-col-title",
                    )
                    yield Static(id="guide-en-content")
        yield Footer()

    def on_mount(self) -> None:
        self._render_guide()

    def _render_guide(self) -> None:
        t = self.topic
        t_hu = TOPIC_HU.get(t, f"Téma {t}")
        t_en = TOPIC_SHORT.get(t, f"Topic {t}")

        self.query_one("#guide-header", Static).update(
            f"[bold]📚  Study Guide — Topic {t}: {t_hu}[/bold]  "
            f"[dim]/ {t_en}  ·  {len(self.questions)} kérdés/questions[/dim]"
        )

        self.query_one("#guide-columns").border_title = (
            f" 🇭🇺 Magyar  ║  🇬🇧 English — Topic {t}: {t_en} "
        )

        hu_lines: list = []
        en_lines: list = []

        # ── Topic overview ────────────────────────────────────────────────────
        intro = TOPIC_INTRO.get(t)
        if intro:
            hu_intro, en_intro = intro
            hu_lines += [
                "[bold yellow]══ ÖSSZEFOGLALÓ ══[/bold yellow]",
                "",
                hu_intro,
                "",
                "─" * 44,
                "",
            ]
            en_lines += [
                "[bold yellow]══ OVERVIEW ══[/bold yellow]",
                "",
                en_intro,
                "",
                "─" * 44,
                "",
            ]

        # ── Authors & Works reference (Topic 3 only) ──────────────────────────
        if t == 3:
            hu_lines += [
                "[bold magenta]══ SZERZŐK ÉS MŰVEIK ══[/bold magenta]",
                "[dim](Olvassa el és jegyezze meg ezt a táblázatot!)[/dim]",
                "",
            ]
            en_lines += [
                "[bold magenta]══ AUTHORS AND THEIR WORKS ══[/bold magenta]",
                "[dim](Read and memorise this reference table!)[/dim]",
                "",
            ]
            for name_hu, name_en, works_hu, works_en in TOPIC3_AUTHORS:
                hu_lines += [
                    f"[bold cyan]{name_hu}[/bold cyan]",
                    f"  [green]{works_hu}[/green]",
                    "",
                ]
                en_lines += [
                    f"[bold cyan]{name_en}[/bold cyan]",
                    f"  [green]{works_en}[/green]",
                    "",
                ]
            hu_lines += ["─" * 44, ""]
            en_lines += ["─" * 44, ""]

        # ── All Q&A pairs ─────────────────────────────────────────────────────
        hu_lines += ["[bold yellow]══ KÉRDÉSEK ÉS VÁLASZOK ══[/bold yellow]", ""]
        en_lines += ["[bold yellow]══ QUESTIONS AND ANSWERS ══[/bold yellow]", ""]

        for i, q in enumerate(self.questions, 1):
            diff = {1: "★", 2: "★★", 3: "★★★"}.get(q.get("difficulty", 1), "★")
            kws = q.get("keywords_hu", [])
            if isinstance(kws, str):
                kws = [k.strip() for k in kws.split(",") if k.strip()]
            kw_str = "  ·  ".join(f"[magenta]{k}[/magenta]" for k in kws)

            hu_lines += [
                f"[bold cyan]K{i:02d}[/bold cyan]  [yellow]{diff}[/yellow]",
                f"[bold]{q['question_hu']}[/bold]",
                "",
                f"[green]→  {q['answer_hu']}[/green]",
            ]
            if kw_str:
                hu_lines.append(f"[dim]Kulcsszavak:  {kw_str}[/dim]")
            hu_lines += ["", "─" * 44, ""]

            en_lines += [
                f"[bold cyan]Q{i:02d}[/bold cyan]  [yellow]{diff}[/yellow]",
                f"[bold]{q['question_en']}[/bold]",
                "",
                f"[green]→  {q['answer_en']}[/green]",
            ]
            if kw_str:
                en_lines.append(f"[dim]Keywords:  {kw_str}[/dim]")
            en_lines += ["", "─" * 44, ""]

        self.query_one("#guide-hu-content", Static).update("\n".join(hu_lines))
        self.query_one("#guide-en-content", Static).update("\n".join(en_lines))

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_launch_learn(self) -> None:
        pool = list(get_questions_for_topic(self.app.questions, self.topic))
        qs = weighted_sample(pool, 20, self.app.progress)
        self.app.push_screen(LearnScreen(qs, self.topic))

    def action_launch_quiz(self) -> None:
        pool = list(get_questions_for_topic(self.app.questions, self.topic))
        qs = weighted_sample(pool, 20, self.app.progress)
        self.app.push_screen(QuizScreen(qs, "quiz", topic=self.topic))

    def action_launch_mc(self) -> None:
        pool = list(get_questions_for_topic(self.app.questions, self.topic))
        qs = weighted_sample(pool, 20, self.app.progress)
        self.app.push_screen(MultiChoiceScreen(qs, self.topic))

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-guide-learn":  self.action_launch_learn()
        elif bid == "btn-guide-quiz": self.action_launch_quiz()
        elif bid == "btn-guide-mc":   self.action_launch_mc()
        elif bid == "btn-guide-home": self.app.pop_screen()


# ── App ───────────────────────────────────────────────────────────────────────


class StudyApp(App):
    TITLE = "Magyar Cultural Exam"
    SUB_TITLE = "Hungarian Cultural Knowledge Exam Prep"

    CSS = """
    /* ── Global ── */
    Screen { background: $background; color: $text; }
    Header { background: $primary-darken-2; color: $text; }
    Footer { background: $panel; color: $text-muted; }
    Rule   { margin: 1 0; color: $primary-darken-3; }
    Input  { margin: 1 0 0 0; border: tall $primary-darken-1; color: $text; }
    Button { margin: 0 1 0 0; color: $text; }
    Button.-success { color: white; }
    Button.-error   { color: white; }
    Button.-warning { color: $text; }
    ProgressBar { height: 1; margin: 0 1; }
    Static { color: $text; }

    /* ── Home Screen ── */
    #home-layout { height: 1fr; }

    #left-panel {
        width: 36;
        dock: left;
        border-right: tall $primary-darken-2;
        padding: 1 1;
        background: $panel;
        overflow-y: auto;
    }
    #right-panel {
        padding: 1 3;
        background: $background;
        color: $text;
    }
    .panel-title {
        color: $accent;
        text-style: bold;
        margin: 1 0 0 0;
        padding: 0 0 0 1;
        border-left: tall $accent;
    }
    .topic-btn {
        width: 100%;
        margin: 0 0 1 0;
        height: 1;
    }
    .topic-btn-good  { width: 100%; margin: 0 0 1 0; height: 1; }
    .topic-btn-ok    { width: 100%; margin: 0 0 1 0; height: 1; }
    .topic-btn-poor  { width: 100%; margin: 0 0 1 0; height: 1; }
    .mode-btn {
        width: 100%;
        margin: 0 0 1 0;
        height: 1;
    }

    /* ── Shared screen layouts ── */
    #learn-layout, #quiz-layout, #vocab-layout, #mc-layout {
        padding: 1 2;
        height: 1fr;
    }
    .section-title {
        color: $text-muted;
        padding-bottom: 1;
    }

    /* ── Card / Quiz content areas ── */
    #card-area, #quiz-area, #vocab-card, #mc-area {
        height: 1fr;
        border: round $primary;
        border-title-color: $accent;
        border-title-style: bold;
        padding: 1 2;
        margin-bottom: 1;
        background: $panel;
    }
    .question-text {
        padding: 1 0;
        min-height: 5;
        color: $text;
    }
    .answer-text   { padding: 1 0; min-height: 3; color: $success; }
    .feedback-text { padding: 1 0; }
    .keywords-text { padding: 0 0 1 0; color: $text-muted; }

    /* ── Nav bars ── */
    #learn-nav, #quiz-nav, #vocab-nav, #mc-nav, #stats-nav {
        height: 3;
        align: right middle;
        padding: 0 1;
        border-top: solid $primary-darken-2;
        background: $panel;
    }
    #rating-row   { height: 3; margin-top: 1; }
    #quiz-buttons { height: 3; margin-top: 1; }
    #vocab-rate   { height: 3; margin-top: 1; align: center middle; }

    /* ── Multiple choice ── */
    .mc-opt {
        width: 100%;
        margin: 0 0 1 0;
        height: 2;
    }
    #mc-options { margin-top: 1; }

    /* ── Stats ── */
    #stats-scroll { padding: 1 3; height: 1fr; }

    /* ── Confirm dialog ── */
    ConfirmScreen { align: center middle; }
    #confirm-dialog {
        width: 62;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: round $warning;
        border-title-color: $warning;
        border-title-style: bold;
    }
    #confirm-message { margin-bottom: 2; text-align: center; }
    #confirm-buttons { height: 3; align: center middle; }

    /* ── Study Guide ── */
    #guide-layout {
        height: 1fr;
        padding: 0 1;
    }
    #guide-actions {
        height: 3;
        margin: 1 0 0 0;
    }
    #guide-columns {
        height: 1fr;
        border: round $primary;
        border-title-color: $accent;
        border-title-style: bold;
        margin-top: 1;
        background: $panel;
    }
    #guide-col-hu {
        width: 1fr;
        border-right: tall $primary-darken-2;
        padding: 1 2;
        overflow-y: auto;
    }
    #guide-col-en {
        width: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }
    .guide-col-title {
        text-style: bold;
        text-align: center;
        padding: 0 0 1 0;
        margin-bottom: 1;
        border-bottom: solid $accent-darken-2;
        background: $primary-darken-3;
    }

    /* ── Exam Briefing ── */
    #briefing-layout {
        align: center middle;
        padding: 2 4;
    }
    #briefing-title { text-align: center; margin-bottom: 1; }
    #briefing-rules {
        border: round $primary-darken-1;
        padding: 1 2;
        background: $panel;
        margin-bottom: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.questions = load_questions(QUESTIONS_FILE)
        self.progress = load_progress(PROGRESS_FILE)
        self.selected_topic: int = None

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    def on_unmount(self) -> None:
        save_progress(self.progress, PROGRESS_FILE)


def main() -> None:
    StudyApp().run()


if __name__ == "__main__":
    main()
