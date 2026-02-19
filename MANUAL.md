# Magyar Kulturalis Ismereti Vizsga - Study System Manual

## What is this?

A CLI-based study tool to prepare for the **Hungarian Cultural Knowledge Exam** (magyar kulturalis ismereti vizsga) required for permanent residence. The exam is written, in Hungarian, 12 questions (2 per topic), 60 minutes, 30 points max, 16 to pass.

This system includes:
- **132 practice questions** across all 6 exam topics
- **5 study modes** (learn, quiz, weak spots, mock exam, vocab drill)
- **Progress tracking** with accuracy stats and recommendations
- **6 printable study sheets** (bilingual Hungarian/English)

---

## Quick Start

Open a terminal in `D:\Python\vtest\` and run:

```
python study.py --mode learn --topic 1
```

That's it. No installs needed — Python 3.7+ standard library only.

---

## The 6 Exam Topics

| # | Topic (Hungarian) | Topic (English) | Questions |
|---|---|---|---|
| 1 | Nemzeti jelkepek es unnepek | National symbols & holidays | 19 |
| 2 | Magyar tortenelem | Hungarian history | 24 |
| 3 | Irodalom es zene | Literature & music | 22 |
| 4 | Alaptorveny es intezmenyek | Fundamental Law & institutions | 17 |
| 5 | Allampolgari jogok | Citizens' rights & obligations | 14 |
| 6 | Mindennapi Magyarorszag | Everyday Hungary | 36 |

---

## Study Modes

### Mode 1: Learn (`--mode learn --topic N`)

**What it does:** Shows every question and answer for a topic, one at a time. Read-only — no typing required.

**Best for:** First pass through new material, or reviewing before bed.

```
python study.py --mode learn --topic 1
```

**How it works:**
1. You see the question in Hungarian + English
2. Press **Enter** to reveal the answer
3. Read the answer in Hungarian + English, plus the keywords you'd need to write
4. Press **Enter** for next question, or **q** to quit

---

### Mode 2: Quiz (`--mode quiz --topic N`)

**What it does:** Tests you on a topic. You type answers in Hungarian, and it scores you by checking if you included the right keywords.

**Best for:** Active recall practice after you've done a learn pass.

```
python study.py --mode quiz --topic 3
```

**How it works:**
1. You see the question in Hungarian (with English subtitle)
2. Type your answer in Hungarian — doesn't need to be perfect sentences, just include the key terms
3. The system fuzzy-matches your answer against required keywords
4. You get feedback:
   - **Green checkmark** = 60%+ keywords matched (good)
   - **Yellow tilde** = 30-59% matched (partial)
   - **Red X** = under 30% (needs work)
5. It shows which keywords you hit and which you missed
6. At the end, you get a total score

**Scoring tip:** You don't need perfect grammar. If the question asks "Ki irta a Himnuszt?" and the keywords are `Kolcsey Ferenc` and `1823`, then typing `kolcsey ferenc 1823` will get you full marks.

**Results are saved** to `progress.json` automatically.

---

### Mode 3: Weak Spots (`--mode weak`)

**What it does:** Re-quizzes you on questions you previously got wrong (accuracy below 60%) or never attempted.

**Best for:** Targeted practice on your gaps. Run this after a few quiz sessions.

```
python study.py --mode weak
```

**How it works:**
- Loads your history from `progress.json`
- Finds your worst questions and drills them, worst-first
- If you have no weak spots, it congratulates you

---

### Mode 4: Mock Exam (`--mode exam`)

**What it does:** Simulates the real exam. 12 questions (2 random from each topic), 60-minute timer, scored out of 30 points.

**Best for:** Testing your readiness 1-2 days before the exam.

```
python study.py --mode exam
```

**How it works:**
1. Press Enter to start (the timer begins)
2. Answer 12 questions in Hungarian
3. Time remaining is shown before each question
4. At the end you get:
   - Score out of 30 points (each question = 2.5 points)
   - **PASSED / FAILED** result (16 points needed)
   - Breakdown of what you missed

**Exam strategy:** On the real exam, partial answers get partial credit. Write something for every question — even a few correct keywords will earn points.

---

### Mode 5: Vocab Drill (`--mode vocab`)

**What it does:** Flash-card drill on key Hungarian terms. Shows English context, you type the Hungarian word (and vice versa).

**Best for:** Drilling specific terms you keep forgetting.

```
python study.py --mode vocab
python study.py --mode vocab --topic 4    # filter to one topic
```

---

### Stats (`--stats`)

**What it does:** Shows your overall progress dashboard.

```
python study.py --stats
```

**Shows you:**
- Total sessions and study streak
- Per-topic accuracy with visual progress bars
- Overall readiness percentage
- Mock exam history (pass/fail)
- Top 5 most-missed questions
- Which topic to study next

---

## Recommended Study Plan

### Week 1: Learn all topics
```
python study.py --mode learn --topic 1
python study.py --mode learn --topic 2
python study.py --mode learn --topic 3
python study.py --mode learn --topic 4
python study.py --mode learn --topic 5
python study.py --mode learn --topic 6
```
Also read through the study sheets (see below).

### Week 2: Quiz each topic
```
python study.py --mode quiz --topic 1
python study.py --mode quiz --topic 2
...etc
```
After each session, check `--stats` to see where you're weakest.

### Week 3: Target weak spots
```
python study.py --mode weak
python study.py --mode vocab
```
Repeat daily. Focus on topics where your accuracy is below 60%.

### Days before exam: Mock exams
```
python study.py --mode exam
```
Take 2-3 mock exams. Aim for 20+ points (comfortable margin above the 16 pass threshold).

---

## Study Sheets (for printing / passive review)

Six bilingual markdown files you can read, print, or open in any markdown viewer:

| File | Content |
|---|---|
| `study_topic1_symbols.md` | Flag, coat of arms, anthem, holidays |
| `study_topic2_history.md` | Honfoglalas through 1989 regime change |
| `study_topic3_literature.md` | Authors, poets, composers |
| `study_topic4_institutions.md` | Parliament, president, government, courts |
| `study_topic5_rights.md` | Human rights generations, key documents |
| `study_topic6_everyday.md` | Geography, neighbors, EU, hungarikumok |

Each sheet has:
- Tables with **Hungarian term | English meaning | Detail**
- **MUST-KNOW** sections highlighted
- **Common exam questions** with model answers at the bottom

---

## Files Overview

| File | What it is | Edit it? |
|---|---|---|
| `study.py` | The study tool | No need |
| `questions.json` | All 132 questions & answers | Yes, if you want to add/fix questions |
| `progress.json` | Your study history | Auto-managed (delete to reset progress) |
| `study_topic*.md` | Printable study sheets | Read-only reference |

---

## Tips for the Exam

1. **Write something for every question.** Partial answers earn partial credit. Even 2-3 correct keywords can get you points.

2. **Focus on the must-know facts first:**
   - 3 national holidays + dates (marcius 15, augusztus 20, oktober 23)
   - Himnusz author (Kolcsey Ferenc, 1823)
   - First king (Szent Istvan, 1000/1001)
   - Parliament (199 kepviselo, 4 ev)
   - Current PM (Orban Viktor) and President (Sulyok Tamas)
   - 7 neighbors
   - EU 2004, Schengen 2007

3. **Memorize key Hungarian words**, not full sentences. The exam graders look for correct terms and facts.

4. **Topic 6 (Everyday Hungary) is the easiest to score on** — it's mostly numbers and names. Start there if you need quick wins.

5. **Don't worry about perfect Hungarian grammar.** Key facts and terms matter more than sentence structure.

6. **Reset your progress** anytime by deleting `progress.json`. A fresh start can help if your early bad scores are discouraging.

---

## Troubleshooting

**Characters look garbled?**
Use Windows Terminal or VS Code terminal instead of the old cmd.exe. The tool sets UTF-8 encoding automatically, but older terminals may not support it.

**Want to reset progress?**
Delete `progress.json`. It will be recreated on next run.

**Want to add your own questions?**
Edit `questions.json`. Each question needs these fields:
```json
{
  "question_hu": "Question in Hungarian",
  "question_en": "Question in English",
  "answer_hu": "Answer in Hungarian",
  "answer_en": "Answer in English",
  "topic": 1,
  "difficulty": 1,
  "keywords_hu": ["keyword1", "keyword2"]
}
```

**Ctrl+C during a session?**
Progress is saved automatically before exit.
