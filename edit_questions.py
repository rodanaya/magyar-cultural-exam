#!/usr/bin/env python3
"""Interactive editor for questions.json — Magyar Exam study app."""

import json
import os
import sys
import unicodedata
import textwrap

# ---------------------------------------------------------------------------
# Ensure UTF-8 I/O on Windows (must happen before any print/input calls)
# ---------------------------------------------------------------------------
if os.name == "nt":
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
    if hasattr(sys.stdin, "buffer"):
        sys.stdin = io.TextIOWrapper(
            sys.stdin.buffer, encoding="utf-8", errors="replace"
        )

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

QUESTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions.json")
DOCS_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "questions.json")

# ---------------------------------------------------------------------------
# Topic definitions (integers, matching questions.json)
# ---------------------------------------------------------------------------

TOPIC_NAMES = {
    1: "Nemzeti jelképek és ünnepek",
    2: "Magyar történelem",
    3: "Irodalom és zene",
    4: "Alaptörvény és intézmények",
    5: "Állampolgári jogok",
    6: "Mindennapi Magyarország",
}

TOPIC_SHORT = {
    1: "T1 – Jelképek & Ünnepek",
    2: "T2 – Történelem",
    3: "T3 – Irodalom & Zene",
    4: "T4 – Alaptörvény",
    5: "T5 – Állampolgári jogok",
    6: "T6 – Mindennapi Mo.",
}

PAGE_SIZE = 20

# ---------------------------------------------------------------------------
# ANSI color support
# ---------------------------------------------------------------------------

def _detect_ansi() -> bool:
    """Return True if this terminal likely supports ANSI escape codes."""
    if os.name == "nt":
        # Enable VT100 processing on Windows 10+
        try:
            ret = os.system("")   # empty command; side-effect: enables VT mode
            # Also try the ctypes route for a reliable check
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
                return True
            return False
        except Exception:
            return False
    # On Unix-likes, check for a real TTY
    return sys.stdout.isatty()


_ANSI = _detect_ansi()

# Color constants — empty strings when ANSI is not available
if _ANSI:
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    RED    = "\033[31m"
    CYAN   = "\033[36m"
    RESET  = "\033[0m"
else:
    BOLD = DIM = GREEN = YELLOW = RED = CYAN = RESET = ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """NFD-decompose, strip combining marks, lowercase — for accent-insensitive search."""
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return stripped.lower()


def stars(n: int) -> str:
    """Return star string, e.g. stars(2) -> '★★☆'."""
    n = max(1, min(3, int(n)))
    return "★" * n + "☆" * (3 - n)


def wrap(text: str, width: int = 70, indent: str = "    ") -> str:
    """Wrap text at width, indenting continuation lines."""
    lines = textwrap.wrap(str(text), width=width)
    return ("\n" + indent).join(lines) if lines else ""


def topic_label(t) -> str:
    """Return a short display label for a topic (int or unknown)."""
    if isinstance(t, int) and t in TOPIC_SHORT:
        return TOPIC_SHORT[t]
    return f"Topic {t}"


def topic_full(t) -> str:
    """Return the full Hungarian topic name."""
    if isinstance(t, int) and t in TOPIC_NAMES:
        return TOPIC_NAMES[t]
    return f"Topic {t}"


def divider(char: str = "═", width: int = 44) -> str:
    return char * width


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_header(subtitle: str = "") -> None:
    print(f"\n{BOLD}{divider()}{RESET}")
    print(f"{BOLD}  Magyar Exam — Question Editor{RESET}")
    if subtitle:
        print(f"  {DIM}{subtitle}{RESET}")
    print(f"{BOLD}{divider()}{RESET}")


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def load_questions() -> list:
    """Load questions from QUESTIONS_FILE. Exit on failure."""
    if not os.path.isfile(QUESTIONS_FILE):
        print(f"{RED}Error: questions file not found:{RESET}\n  {QUESTIONS_FILE}")
        sys.exit(1)
    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("Expected a JSON array at top level.")
        return data
    except json.JSONDecodeError as exc:
        print(f"{RED}JSON parse error in {QUESTIONS_FILE}:{RESET}\n  {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"{RED}Failed to load questions:{RESET}\n  {exc}")
        sys.exit(1)


def save_questions(qs: list) -> None:
    """Save questions to both QUESTIONS_FILE and DOCS_FILE."""
    payload = json.dumps(qs, ensure_ascii=False, indent=2)
    errors = []

    for path in (QUESTIONS_FILE, DOCS_FILE):
        try:
            dir_part = os.path.dirname(path)
            if dir_part and not os.path.isdir(dir_part):
                os.makedirs(dir_part, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(payload)
        except Exception as exc:
            errors.append(f"  {path}: {exc}")

    if errors:
        print(f"{RED}Warning — could not write to:{RESET}")
        for e in errors:
            print(e)
    else:
        print(f"{GREEN}Saved to both files.{RESET}")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def fmt_list_line(idx_1based: int, q: dict) -> str:
    """One-line summary for the list view."""
    t_label = topic_label(q.get("topic"))
    diff    = stars(q.get("difficulty", 1))
    qtext   = q.get("question_hu", "")[:60]
    if len(q.get("question_hu", "")) > 60:
        qtext += "…"
    num = f"#{idx_1based:03d}"
    return (
        f"  {BOLD}{num}{RESET}  "
        f"{CYAN}{t_label:<22}{RESET}  "
        f"{YELLOW}{diff}{RESET}  "
        f"{qtext}"
    )


def fmt_full_question(idx_1based: int, q: dict) -> None:
    """Print a full question card."""
    print(f"\n{BOLD}{divider('-', 44)}{RESET}")
    print(f"  {BOLD}#{idx_1based:03d}{RESET}  "
          f"{CYAN}{topic_full(q.get('topic'))}{RESET}  "
          f"{YELLOW}{stars(q.get('difficulty', 1))}{RESET}")
    print(f"{divider('-', 44)}")
    print(f"  {BOLD}Kérdés (HU):{RESET}")
    print(f"    {wrap(q.get('question_hu', ''))}")
    print(f"  {DIM}Question (EN):{RESET}")
    print(f"    {wrap(q.get('question_en', ''))}")
    print(f"  {BOLD}Válasz (HU):{RESET}")
    print(f"    {wrap(q.get('answer_hu', ''))}")
    print(f"  {DIM}Answer (EN):{RESET}")
    print(f"    {wrap(q.get('answer_en', ''))}")
    kw = q.get("keywords_hu", [])
    print(f"  {BOLD}Kulcsszavak:{RESET}  {', '.join(kw) if kw else '(none)'}")
    print(f"{divider('-', 44)}")


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def prompt(label: str, default: str = "") -> str:
    """Prompt the user; return default if they press Enter."""
    if default:
        display_default = str(default)[:60]
        hint = f" [{display_default}]"
    else:
        hint = ""
    try:
        value = input(f"  {label}{hint}: ").strip()
    except EOFError:
        return default
    return value if value else default


def prompt_int(label: str, choices: list, default: int = None) -> int:
    """Prompt for an integer from choices."""
    hint = f" ({'/'.join(str(c) for c in choices)})"
    if default is not None:
        hint += f" [{default}]"
    while True:
        try:
            raw = input(f"  {label}{hint}: ").strip()
        except EOFError:
            return default if default is not None else choices[0]
        if not raw and default is not None:
            return default
        try:
            val = int(raw)
            if val in choices:
                return val
        except ValueError:
            pass
        print(f"  {RED}Please enter one of: {', '.join(str(c) for c in choices)}{RESET}")


def confirm(label: str, default: bool = False) -> bool:
    """Yes/No confirmation."""
    hint = "[y/N]" if not default else "[Y/n]"
    try:
        raw = input(f"  {label} {hint}: ").strip().lower()
    except EOFError:
        return default
    if not raw:
        return default
    return raw.startswith("y")


def parse_keywords(raw: str) -> list:
    """Parse comma-separated keyword string into a cleaned list."""
    return [kw.strip() for kw in raw.split(",") if kw.strip()]


# ---------------------------------------------------------------------------
# Topic chooser
# ---------------------------------------------------------------------------

def choose_topic(current: int = None) -> int:
    """Interactive topic picker. Returns the chosen topic int."""
    print(f"\n  {BOLD}Available topics:{RESET}")
    for num, name in TOPIC_NAMES.items():
        marker = f" {GREEN}(current){RESET}" if num == current else ""
        print(f"    {BOLD}{num}{RESET}.  {name}{marker}")
    print(f"    {BOLD}0{RESET}.  (enter a custom topic number)")

    choices = list(TOPIC_NAMES.keys()) + [0]
    default = current if current in TOPIC_NAMES else None
    choice = prompt_int("Select topic", choices, default=default)

    if choice == 0:
        while True:
            try:
                raw = input("  Custom topic number: ").strip()
                val = int(raw)
                return val
            except (ValueError, EOFError):
                print(f"  {RED}Enter an integer.{RESET}")
    return choice


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(qs: list) -> None:
    """[L] Paginated list of all questions."""
    if not qs:
        print(f"\n  {YELLOW}No questions loaded.{RESET}")
        return

    total   = len(qs)
    pages   = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page    = 0

    while True:
        clear_screen()
        print_header(f"List — page {page + 1}/{pages}  ({total} questions total)")
        start = page * PAGE_SIZE
        end   = min(start + PAGE_SIZE, total)
        for i in range(start, end):
            print(fmt_list_line(i + 1, qs[i]))

        print(f"\n  {DIM}[N]ext  [P]rev  [number] view full  [Enter] menu{RESET}")
        try:
            raw = input("  > ").strip().lower()
        except EOFError:
            return

        if raw == "n":
            if page < pages - 1:
                page += 1
            else:
                print(f"  {YELLOW}Already on last page.{RESET}")
        elif raw == "p":
            if page > 0:
                page -= 1
            else:
                print(f"  {YELLOW}Already on first page.{RESET}")
        elif raw == "":
            return
        elif raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < total:
                fmt_full_question(idx + 1, qs[idx])
                input("  [Enter] to continue...")
            else:
                print(f"  {RED}Invalid question number.{RESET}")
                input("  [Enter] to continue...")
        else:
            print(f"  {YELLOW}Unrecognised input.{RESET}")


def cmd_search(qs: list) -> None:
    """[S] Search across all text fields."""
    print_header("Search")
    try:
        term = input("  Search term: ").strip()
    except EOFError:
        return
    if not term:
        print(f"  {YELLOW}Empty search — returning to menu.{RESET}")
        return

    norm_term = normalize(term)
    matches = []
    for idx, q in enumerate(qs):
        haystack = " ".join([
            q.get("question_hu", ""),
            q.get("question_en", ""),
            q.get("answer_hu", ""),
            q.get("answer_en", ""),
            " ".join(q.get("keywords_hu", [])),
        ])
        if norm_term in normalize(haystack):
            matches.append((idx, q))

    if not matches:
        print(f"\n  {YELLOW}No matches for '{term}'.{RESET}")
        input("  [Enter] to continue...")
        return

    print(f"\n  {GREEN}{len(matches)} match(es):{RESET}\n")
    for idx, q in matches:
        print(fmt_list_line(idx + 1, q))

    print(f"\n  {DIM}Enter a question number to view it, or [Enter] to go back.{RESET}")
    try:
        raw = input("  > ").strip()
    except EOFError:
        return

    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(qs):
            fmt_full_question(idx + 1, qs[idx])
            input("  [Enter] to continue...")
        else:
            print(f"  {RED}Invalid question number.{RESET}")
            input("  [Enter] to continue...")


def cmd_add(qs: list) -> None:
    """[A] Add a new question interactively."""
    print_header("Add New Question")

    topic = choose_topic()
    difficulty = prompt_int("Difficulty", [1, 2, 3])

    print(f"\n  {BOLD}Enter question fields (Ctrl+C to cancel):{RESET}\n")
    question_hu = prompt("question_hu (Hungarian question)")
    question_en = prompt("question_en (English translation)")
    answer_hu   = prompt("answer_hu   (Hungarian answer)")
    answer_en   = prompt("answer_en   (English answer)")
    kw_raw      = prompt("keywords_hu (comma-separated)")
    keywords_hu = parse_keywords(kw_raw)

    new_q = {
        "question_hu": question_hu,
        "question_en": question_en,
        "answer_hu":   answer_hu,
        "answer_en":   answer_en,
        "topic":       topic,
        "difficulty":  difficulty,
        "keywords_hu": keywords_hu,
    }

    # Preview
    print(f"\n  {BOLD}Preview:{RESET}")
    fmt_full_question(len(qs) + 1, new_q)

    if confirm("Save this question?", default=False):
        qs.append(new_q)
        save_questions(qs)
        print(f"  {GREEN}Question #{len(qs)} added.{RESET}")
    else:
        print(f"  {YELLOW}Cancelled — nothing saved.{RESET}")

    input("  [Enter] to continue...")


def cmd_edit(qs: list) -> None:
    """[E] Edit an existing question."""
    print_header("Edit Question")
    if not qs:
        print(f"  {YELLOW}No questions to edit.{RESET}")
        input("  [Enter] to continue...")
        return

    try:
        raw = input(f"  Question number (1–{len(qs)}): ").strip()
    except EOFError:
        return

    if not raw.isdigit():
        print(f"  {RED}Invalid question number.{RESET}")
        input("  [Enter] to continue...")
        return

    idx = int(raw) - 1
    if not (0 <= idx < len(qs)):
        print(f"  {RED}Invalid question number.{RESET}")
        input("  [Enter] to continue...")
        return

    q = qs[idx]
    fmt_full_question(idx + 1, q)
    print(f"\n  {BOLD}Edit fields (press Enter to keep current value):{RESET}\n")

    # Topic
    print(f"  Current topic: {BOLD}{topic_full(q.get('topic'))}{RESET}")
    change_topic = confirm("Change topic?", default=False)
    if change_topic:
        new_topic = choose_topic(current=q.get("topic"))
    else:
        new_topic = q.get("topic")

    # Difficulty
    new_difficulty = prompt_int(
        "difficulty",
        [1, 2, 3],
        default=q.get("difficulty", 1),
    )

    # Text fields
    new_question_hu = prompt("question_hu", default=q.get("question_hu", ""))
    new_question_en = prompt("question_en", default=q.get("question_en", ""))
    new_answer_hu   = prompt("answer_hu",   default=q.get("answer_hu", ""))
    new_answer_en   = prompt("answer_en",   default=q.get("answer_en", ""))

    # Keywords
    current_kw = ", ".join(q.get("keywords_hu", []))
    kw_raw = prompt("keywords_hu (comma-separated)", default=current_kw)
    new_keywords = parse_keywords(kw_raw)

    updated_q = {
        "question_hu": new_question_hu,
        "question_en": new_question_en,
        "answer_hu":   new_answer_hu,
        "answer_en":   new_answer_en,
        "topic":       new_topic,
        "difficulty":  new_difficulty,
        "keywords_hu": new_keywords,
    }

    print(f"\n  {BOLD}Updated preview:{RESET}")
    fmt_full_question(idx + 1, updated_q)

    if confirm("Save changes?", default=False):
        qs[idx] = updated_q
        save_questions(qs)
        print(f"  {GREEN}Question #{idx + 1} updated.{RESET}")
    else:
        print(f"  {YELLOW}Cancelled — nothing saved.{RESET}")

    input("  [Enter] to continue...")


def cmd_delete(qs: list) -> None:
    """[D] Delete a question."""
    print_header("Delete Question")
    if not qs:
        print(f"  {YELLOW}No questions to delete.{RESET}")
        input("  [Enter] to continue...")
        return

    try:
        raw = input(f"  Question number to delete (1–{len(qs)}): ").strip()
    except EOFError:
        return

    if not raw.isdigit():
        print(f"  {RED}Invalid question number.{RESET}")
        input("  [Enter] to continue...")
        return

    idx = int(raw) - 1
    if not (0 <= idx < len(qs)):
        print(f"  {RED}Invalid question number.{RESET}")
        input("  [Enter] to continue...")
        return

    q = qs[idx]
    fmt_full_question(idx + 1, q)

    if confirm(f"{RED}Delete question #{idx + 1}?{RESET}", default=False):
        deleted = qs.pop(idx)
        save_questions(qs)
        short = deleted.get("question_hu", "")[:50]
        print(f"  {GREEN}Deleted:{RESET} {short}")
    else:
        print(f"  {YELLOW}Cancelled — nothing deleted.{RESET}")

    input("  [Enter] to continue...")


def cmd_topics(qs: list) -> None:
    """[T] Show topic summary."""
    print_header("Topic Summary")

    # Gather stats per topic
    topic_counts: dict = {}
    topic_diff_sum: dict = {}

    for q in qs:
        t = q.get("topic")
        d = q.get("difficulty", 1)
        topic_counts[t]   = topic_counts.get(t, 0) + 1
        topic_diff_sum[t] = topic_diff_sum.get(t, 0) + d

    # Print known topics first, then any unknown ones
    all_topics = sorted(
        set(list(TOPIC_NAMES.keys()) + list(topic_counts.keys()))
    )

    print()
    for t in all_topics:
        count    = topic_counts.get(t, 0)
        diff_sum = topic_diff_sum.get(t, 0)
        avg_diff = round(diff_sum / count) if count else 0
        label    = TOPIC_NAMES.get(t, f"Topic {t}")
        diff_str = stars(avg_diff) if avg_diff else "   "
        print(
            f"  {BOLD}T{t}{RESET}  "
            f"{CYAN}{label:<38}{RESET}  "
            f"{BOLD}{count:>3}{RESET} questions  "
            f"avg {YELLOW}{diff_str}{RESET}"
        )

    total = len(qs)
    print(f"\n  {DIM}Total: {total} questions across {len(topic_counts)} topic(s){RESET}")
    input("\n  [Enter] to continue...")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

MENU = f"""
{BOLD}{'═' * 44}{RESET}
{BOLD}  Magyar Exam — Question Editor{RESET}
{BOLD}{'═' * 44}{RESET}
  {BOLD}[L]{RESET} List all questions
  {BOLD}[S]{RESET} Search questions
  {BOLD}[A]{RESET} Add new question
  {BOLD}[E]{RESET} Edit a question
  {BOLD}[D]{RESET} Delete a question
  {BOLD}[T]{RESET} Topic summary
  {BOLD}[Q]{RESET} Quit
{BOLD}{'═' * 44}{RESET}"""


def main() -> None:
    """Main interactive loop."""
    try:
        qs = load_questions()
    except SystemExit:
        raise

    while True:
        clear_screen()
        print(MENU)
        print(f"  {DIM}Loaded {len(qs)} questions from:{RESET}")
        print(f"  {DIM}{QUESTIONS_FILE}{RESET}\n")

        try:
            choice = input("  Choice: ").strip().upper()
        except EOFError:
            choice = "Q"

        if choice == "L":
            cmd_list(qs)
        elif choice == "S":
            cmd_search(qs)
        elif choice == "A":
            cmd_add(qs)
        elif choice == "E":
            cmd_edit(qs)
        elif choice == "D":
            cmd_delete(qs)
        elif choice == "T":
            cmd_topics(qs)
        elif choice == "Q":
            print(f"\n  {GREEN}Goodbye!{RESET}\n")
            sys.exit(0)
        else:
            print(f"\n  {YELLOW}Unknown option '{choice}'. Press L/S/A/E/D/T/Q.{RESET}")
            import time
            time.sleep(0.8)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {GREEN}Goodbye!{RESET}\n")
        sys.exit(0)
