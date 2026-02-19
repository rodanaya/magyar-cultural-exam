# 🇭🇺 Magyar Cultural Exam — Study Tool

A comprehensive study app for the **Hungarian Cultural Knowledge Exam** (*Magyar Kulturális Ismereti Vizsga*) — required for permanent residency in Hungary.

**132 practice questions · 6 exam topics · Spaced repetition · Two interfaces**

---

## Screenshots

```
┌─────────────────────────────────────────────────────────────────────┐
│  Magyar Cultural Exam — Hungarian Cultural Knowledge Exam Prep      │
├──────────────────────┬──────────────────────────────────────────────┤
│ TOPICS               │ ⚡ 132 card(s) due for SRS review today      │
│ T1  Symbols          │                                              │
│ T2  History          │ Streak: 0 day(s)   Sessions: 6              │
│ T3  Lit & Music      │                                              │
│ T4  Law              │ Per-Topic Accuracy                           │
│ T5  Rights           │ ──────────────────────────────────────────── │
│ T6  Everyday         │ T1  ░░░░░░░░░░░░░░░░░░ 0%  Symbols          │
│ ─────────────────── │ T2  ░░░░░░░░░░░░░░░░░░ 0%  History          │
│ MODES               │ ...                                          │
│ 📖 Learn             │ SRS Forecast — next 7 days                  │
│ ❓ Quiz              │ Today   ████████████████████ 132            │
│ 🔢 Multiple Choice  │   +1d   ░░░░░░░░░░░░░░░░░░░░ 0             │
│ ⚠  Weak Spots       │   +2d   ░░░░░░░░░░░░░░░░░░░░ 0             │
│ ⏰ SRS Review        │                                              │
│ 📝 Mock Exam         │ Press 1-6 to select topic · l/q/m for modes │
│ 🔤 Vocab Drill       │                                              │
│ 📊 Statistics        │                                              │
└──────────────────────┴──────────────────────────────────────────────┘
 l Learn  q Quiz  m M-Choice  w Weak  e Exam  s Stats  ^p palette
```

---

## Features

### Study Modes

| Mode | Description | Interface |
|------|-------------|-----------|
| **Learn** | Card-by-card review with self-rating that feeds the SRS scheduler | TUI + CLI |
| **Quiz** | Free-text answers in Hungarian with fuzzy keyword matching | TUI + CLI |
| **Multiple Choice** | 4-option MC — press 1–4 to answer, no typing needed | TUI only |
| **Weak Spots** | Automatically focuses on questions you keep getting wrong | TUI + CLI |
| **SRS Review** | Daily review queue based on spaced repetition schedule | TUI + CLI |
| **Mock Exam** | 12 questions, 60-minute timer, scored out of 30 points | TUI + CLI |
| **Vocab Drill** | Flash-card keyword practice (EN → HU and HU → EN) | TUI + CLI |
| **Statistics** | Full dashboard: accuracy bars, streak, exam history, recommendations | TUI + CLI |

### Spaced Repetition (SRS)
The TUI uses the **SM-2 algorithm** (same as Anki) to schedule reviews:
- Rate each card after revealing: **1** Didn't know · **2** Almost · **3** Got it
- Cards you know well get pushed days/weeks out
- Weak cards come back tomorrow
- The 7-day forecast bar shows your upcoming review workload

### Keyboard Shortcuts (TUI)

| Screen | Keys |
|--------|------|
| Home | `1`–`6` select topic · `L` learn · `Q` quiz · `M` multiple choice · `W` weak · `E` exam · `S` stats |
| Learn | `Space`/`R` reveal · `1`/`2`/`3` rate · `←`/`→` prev/next · `Esc` home |
| Quiz | `Enter` submit/next · `H` hint (-20% penalty) · `Esc` back |
| Multiple Choice | `1`–`4` pick answer · `Enter` next · `Esc` back |
| Vocab | `Space` flip · `Y` correct · `N` wrong · `Esc` back |

### Hint System
In Quiz mode, press **H** to reveal masked keywords (`K_______ F_____`). Costs −20% of that question's score — useful when you almost remember something.

---

## The 6 Exam Topics

| # | Hungarian | English | Questions |
|---|-----------|---------|-----------|
| 1 | Nemzeti jelképek és ünnepek | National symbols & holidays | 19 |
| 2 | Magyar történelem | Hungarian history | 24 |
| 3 | Irodalom és zene | Literature & music | 22 |
| 4 | Alaptörvény és intézmények | Fundamental Law & institutions | 17 |
| 5 | Állampolgári jogok | Citizens' rights & obligations | 14 |
| 6 | Mindennapi Magyarország | Everyday Hungary | 36 |

---

## Installation & Usage

### TUI (recommended)

```bash
pip install textual
python study_gui.py
```

### CLI (no dependencies)

```bash
python study.py --mode learn --topic 1
python study.py --mode quiz  --topic 3
python study.py --mode weak
python study.py --mode exam
python study.py --mode vocab
python study.py --stats
```

**Requirements:** Python 3.8+
**TUI dependency:** `textual` (`pip install textual`)
**CLI:** standard library only, no install needed

---

## Project Structure

```
├── study_gui.py          # Textual TUI (main app)
├── study.py              # CLI tool (no dependencies)
├── questions.json        # 132 questions & answers
├── progress.json         # Your study progress & SRS data (auto-managed)
├── MANUAL.md             # Full CLI manual
├── study_topic1_symbols.md     ┐
├── study_topic2_history.md     │
├── study_topic3_literature.md  │  Printable bilingual study sheets
├── study_topic4_institutions.md│
├── study_topic5_rights.md      │
└── study_topic6_everyday.md    ┘
```

---

## About the Exam

The **Magyar Kulturális Ismereti Vizsga** is a written exam required for Hungarian permanent residency. It consists of:
- **12 questions** (2 randomly drawn from each of the 6 topics)
- **60-minute time limit**
- **30 points maximum** (each question worth 2.5 pts)
- **16 points needed to pass**
- Answers must be written in Hungarian

Partial answers earn partial credit — writing any correct keywords helps.

---

## Recommended Study Plan

| Phase | Activity |
|-------|----------|
| Week 1 | **Learn** all 6 topics · read study sheets |
| Week 2 | **Quiz** each topic · check stats after each session |
| Week 3 | **Weak Spots** + **SRS Review** daily · **Vocab Drill** |
| Days before | 2–3 **Mock Exams** · aim for 20+ points |

**Reset progress** at any time by deleting `progress.json`.

---

## Tips for the Real Exam

1. **Write something for every question** — partial answers earn partial credit
2. **Key facts to memorise first:**
   - 3 national holidays: március 15, augusztus 20, október 23
   - Himnusz author: Kölcsey Ferenc (1823)
   - First king: Szent István (1000/1001)
   - Parliament: 199 képviselő, 4-year terms
   - 7 neighbours: Ausztria, Szlovákia, Ukrajna, Románia, Szerbia, Horvátország, Szlovénia
   - EU 2004 · Schengen 2007
3. **Topic 6 (Everyday Hungary)** is the easiest to score on — mostly numbers and names
4. **Grammar doesn't matter** — examiners look for correct terms and facts

---

*Built with Python · [Textual](https://textual.textualize.io/) · SM-2 spaced repetition*
