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

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Button, Static, Input, Rule
    from textual.containers import Container, ScrollableContainer, Horizontal, Vertical
    from textual.screen import Screen
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
        return f"[dim]{'─' * width}[/dim] [dim]--[/dim]"
    pct = correct / attempts
    filled = round(pct * width)
    color = "green" if pct >= 0.6 else ("yellow" if pct >= 0.3 else "red")
    return (
        f"[{color}]{'█' * filled}[/{color}]"
        f"[dim]{'░' * (width - filled)}[/dim]"
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

        if due_count > 0:
            lines.append(
                f"[bold yellow]⚡ {due_count} card(s) due for SRS review today[/bold yellow]"
            )
        else:
            lines.append("[bold green]✓ All caught up — no SRS cards due today[/bold green]")

        lines.append(
            f"\n[bold]Streak:[/bold] [green]{streak} day(s)[/green]"
            f"   [bold]Sessions:[/bold] {len(sessions)}\n"
        )

        # Per-topic accuracy
        lines.append("[bold]Per-Topic Accuracy[/bold]")
        lines.append("─" * 48)
        overall_c = overall_a = 0
        for t in range(1, 7):
            c, a = topic_accuracy(progress, t)
            overall_c += c
            overall_a += a
            lines.append(f"  [bold]T{t}[/bold]  {accuracy_bar(c, a)}  {TOPIC_SHORT[t]}")
        lines.append("─" * 48)
        if overall_a:
            opct = overall_c / overall_a * 100
            oc = "green" if opct >= 60 else ("yellow" if opct >= 30 else "red")
            lines.append(f"[bold]Overall Readiness:[/bold] [{oc}]{opct:.0f}%[/{oc}]\n")
        else:
            lines.append("[bold]Overall Readiness:[/bold] [dim]No data yet[/dim]\n")

        # SRS 7-day forecast
        forecast = srs_forecast(progress, questions, 7)
        max_c = max((c for _, c in forecast), default=1) or 1
        today = datetime.date.today()
        lines.append("[bold]SRS Forecast — next 7 days[/bold]")
        lines.append("─" * 48)
        for dt, count in forecast:
            delta = (dt - today).days
            label = "Today  " if delta == 0 else f"  +{delta}d   "
            bw = round(count / max_c * 20) if count else 0
            color = "yellow" if (delta == 0 and count) else ("cyan" if count else "dim")
            bar = f"[{color}]{'█' * bw}[/{color}][dim]{'░' * (20 - bw)}[/dim]"
            cnt = f"[{color}]{count}[/{color}]" if count else "[dim]0[/dim]"
            lines.append(f"  {label} {bar} {cnt}")

        lines.append("")
        if app.selected_topic:
            t = app.selected_topic
            lines.append(
                f"[bold cyan]● Topic {t}: {TOPIC_HU.get(t, TOPIC_SHORT.get(t, ''))}[/bold cyan]"
            )
        else:
            lines.append("[dim]Press 1-6 to select a topic · l/q/m/w/e/s for modes[/dim]")

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
        if mode in ("learn", "quiz", "mc") and not app.selected_topic:
            self.notify("Select a topic first (press 1–6)", severity="warning")
            return
        if mode == "learn":
            qs = list(get_questions_for_topic(app.questions, app.selected_topic))
            app.push_screen(LearnScreen(qs, app.selected_topic))
        elif mode == "quiz":
            qs = list(get_questions_for_topic(app.questions, app.selected_topic))
            random.shuffle(qs)
            app.push_screen(QuizScreen(qs, "quiz", topic=app.selected_topic))
        elif mode == "mc":
            qs = list(get_questions_for_topic(app.questions, app.selected_topic))
            random.shuffle(qs)
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
            app.push_screen(QuizScreen(self._exam_questions(), "exam", is_exam=True))
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
            "mode-learn": "learn", "mode-quiz": "quiz",  "mode-mc":    "mc",
            "mode-weak":  "weak",  "mode-srs":  "srs",   "mode-exam":  "exam",
            "mode-vocab": "vocab", "mode-stats": "stats",
        }
        if bid in mode_map:
            self._launch(mode_map[bid])


# ── Learn Screen ──────────────────────────────────────────────────────────────


class LearnScreen(Screen):
    """Card-by-card: question → reveal → self-rate (feeds SRS)."""

    BINDINGS = [
        Binding("space",  "reveal",    "Reveal"),
        Binding("r",      "reveal",    "Reveal", show=False),
        Binding("1",      "rate1",     "Didn't know", show=False),
        Binding("2",      "rate2",     "Almost",      show=False),
        Binding("3",      "rate3",     "Got it",      show=False),
        Binding("right",  "next_card", "Next",  show=False),
        Binding("left",   "prev_card", "Prev",  show=False),
        Binding("escape", "go_home",   "Home"),
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
        diff = {"easy": "★", "medium": "★★", "hard": "★★★"}.get(
            q.get("difficulty", "medium"), "★★"
        )
        self.query_one("#learn-progress", Static).update(
            f"[bold]Learn — Topic {self.topic}: {TOPIC_SHORT.get(self.topic, '')}[/bold]  "
            f"[dim]Card {self.idx + 1}/{total}[/dim]  [yellow]{diff}[/yellow]"
        )
        self.query_one("#card-question", Static).update(
            f"[bold cyan]🇭🇺 {q['question_hu']}[/bold cyan]\n"
            f"[dim]🇬🇧 {q['question_en']}[/dim]"
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
            f"\n[bold green]🇭🇺 {q['answer_hu']}[/bold green]\n"
            f"[dim]🇬🇧 {q['answer_en']}[/dim]"
        )
        self.query_one("#card-keywords", Static).update(
            f"\n[dim]Keywords:[/dim]  {kw_rich}\n\n"
            f"[dim]Rate yourself: 1 = Didn't know · 2 = Almost · 3 = Got it[/dim]"
            if kw_rich else
            f"\n[dim]Rate yourself: 1 = Didn't know · 2 = Almost · 3 = Got it[/dim]"
        )
        self.query_one("#btn-reveal",  Button).display = False
        self.query_one("#rating-row",  Horizontal).display = True
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

    def action_rate1(self) -> None:
        self._rate(1)

    def action_rate2(self) -> None:
        self._rate(3)

    def action_rate3(self) -> None:
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

    def action_go_home(self) -> None:
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

    @on(Button.Pressed, "#btn-home")
    def on_home(self) -> None:
        self.app.pop_screen()


# ── Quiz Screen ───────────────────────────────────────────────────────────────


class QuizScreen(Screen):
    """Free-text quiz for quiz / weak / srs / exam modes. Has hint button."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("h",      "hint",    "Hint"),
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
        diff = {"easy": "★", "medium": "★★", "hard": "★★★"}.get(
            q.get("difficulty", "medium"), "★★"
        )
        t_num = q.get("topic", "?")
        t_name = TOPIC_SHORT.get(t_num, f"Topic {t_num}")

        if not self.is_exam:
            self.query_one("#quiz-header", Static).update(
                f"[bold]{self._mode_label()}[/bold]  [dim]Q {self.idx + 1}/{total}[/dim]  "
                f"[dim]Score: {self.total_score:.1f}[/dim]"
            )

        self.query_one("#quiz-question", Static).update(
            f"[dim]Topic {t_num}: {t_name}  {diff}[/dim]\n\n"
            f"[bold cyan]🇭🇺 {q['question_hu']}[/bold cyan]\n"
            f"[dim]🇬🇧 {q['question_en']}[/dim]"
        )
        self.query_one("#quiz-feedback", Static).update("")

        inp = self.query_one("#answer-input", Input)
        inp.value = ""
        inp.focus()

        self.query_one("#btn-submit", Button).display = True
        self.query_one("#btn-hint",   Button).display = True
        self.query_one("#btn-next",   Button).display = False
        self.answered = False
        self.hint_used = False

    # ── Hint ──────────────────────────────────────────────────────────────────

    def _show_hint(self) -> None:
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

        sc, matched, missed = score_answer(user_answer, kws)
        if self.hint_used:
            sc *= 0.8

        self.total_score += sc
        self.answered = True

        record_attempt(self.app.progress, q, sc)
        qid = question_id(q["question_hu"])
        update_srs(self.app.progress, qid, srs_quality(sc))
        save_progress(self.app.progress, PROGRESS_FILE)

        if sc >= 0.6:
            result = f"[bold green]✔  Correct! ({sc * 100:.0f}%)[/bold green]"
        elif sc >= 0.3:
            result = f"[bold yellow]~  Partial ({sc * 100:.0f}%)[/bold yellow]"
        else:
            result = f"[bold red]✘  Incorrect ({sc * 100:.0f}%)[/bold red]"

        hint_note = "  [dim](hint penalty applied)[/dim]" if self.hint_used else ""
        srs_entry = self.app.progress.get("srs", {}).get(qid, {})
        interval = srs_entry.get("interval", 1)
        matched_line = f"\n[green]✔  Matched:  {', '.join(matched)}[/green]" if matched else ""
        missed_line  = f"\n[red]✘  Missed:   {', '.join(missed)}[/red]"   if missed  else ""

        self.query_one("#quiz-feedback", Static).update(
            f"{result}{hint_note}\n\n"
            f"[bold]Answer:[/bold]\n"
            f"[green]🇭🇺 {q['answer_hu']}[/green]\n"
            f"[dim]🇬🇧 {q['answer_en']}[/dim]"
            f"{matched_line}{missed_line}\n\n"
            f"[dim]Next SRS review in {interval} day(s)[/dim]"
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
        self.app.pop_screen()

    def action_hint(self) -> None:
        self._show_hint()

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
        self.app.pop_screen()


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
            self.app.pop_screen()


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


# ── App ───────────────────────────────────────────────────────────────────────


class StudyApp(App):
    TITLE = "Magyar Cultural Exam"
    SUB_TITLE = "Hungarian Cultural Knowledge Exam Prep"

    CSS = """
    Screen { background: $surface; }

    #home-layout { height: 1fr; }

    #left-panel {
        width: 32;
        dock: left;
        border-right: solid $primary-darken-2;
        padding: 1 1;
        background: $panel;
        overflow-y: auto;
    }
    #right-panel { padding: 1 2; }

    .panel-title {
        color: $accent;
        text-style: bold;
        margin: 1 0 0 0;
    }
    .topic-btn, .mode-btn {
        width: 100%;
        margin: 0 0 1 0;
    }

    #learn-layout, #quiz-layout, #vocab-layout, #mc-layout {
        padding: 1 2;
        height: 1fr;
    }
    .section-title { color: $text-muted; }

    .question-text { padding: 1 0; min-height: 5; }
    .answer-text   { padding: 1 0; min-height: 3; }
    .feedback-text { padding: 1 0; }
    .keywords-text { padding: 0 0 1 0; }

    #card-area, #quiz-area, #vocab-card, #mc-area {
        height: 1fr;
        border: solid $primary-darken-2;
        padding: 1 2;
        margin-bottom: 1;
    }

    #rating-row {
        height: 3;
        margin-top: 1;
    }
    #learn-nav, #quiz-nav, #vocab-nav, #mc-nav, #stats-nav {
        height: 3;
        align: right middle;
        padding: 0 1;
    }
    #quiz-buttons { height: 3; margin-top: 1; }
    #vocab-rate   { height: 3; margin-top: 1; align: center middle; }

    .mc-opt {
        width: 100%;
        margin: 0 0 1 0;
    }
    #mc-options { margin-top: 1; }

    #stats-scroll { padding: 1 2; height: 1fr; }

    Input  { margin: 1 0 0 0; }
    Button { margin: 0 1 0 0; }
    Rule   { margin: 1 0; }
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
