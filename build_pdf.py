import sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8')

import markdown
from xhtml2pdf import pisa

# ── Load questions for trimmed flashcards & fill-in-the-blank ──────────────
with open('questions.json', encoding='utf-8') as f:
    qs = json.load(f)
by_topic = {}
for item in qs:
    by_topic.setdefault(item['topic'], []).append(item)

TOPIC_NAMES = {
    1: "Nemzeti Jelképek és Ünnepek",
    2: "Magyarország Történelme",
    3: "Irodalom és Zenetörténet",
    4: "Az Alaptörvény Intézményei",
    5: "Állampolgári Jogok és Kötelezettségek",
    6: "Európa és Magyarország a Mindennapokban",
}

# ── Register fonts with ReportLab directly ─────────────────────────────────
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('MyArial',     'arial.ttf'))
pdfmetrics.registerFont(TTFont('MyArial-Bold','arialbd.ttf'))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily('MyArial', normal='MyArial', bold='MyArial-Bold',
                   italic='MyArial', boldItalic='MyArial-Bold')

CSS_STYLE = """

body {
    font-family: MyArial;
    font-size: 8.5pt;
    line-height: 1.4;
    color: #1a1a1a;
}

/* Cover */
.cover {
    text-align: center;
    padding: 40pt 20pt;
    page-break-after: always;
}
.cover h1 {
    font-size: 22pt;
    color: #c0392b;
    border-bottom: 2pt solid #c0392b;
    padding-bottom: 8pt;
}
.cover .meta { font-size: 10pt; color: #666; margin: 4pt 0; }
.toc {
    display: block;
    margin: 20pt auto;
    border: 1pt solid #ddd;
    padding: 12pt 16pt;
    width: 280pt;
    text-align: left;
}
.toc h2 { font-size: 11pt; color: #c0392b; margin-top: 0; }
.toc li { margin: 4pt 0; font-size: 9pt; }

/* Sections — only break between top-level docs */
.content-section { page-break-before: always; }

h1 {
    font-size: 14pt;
    color: #c0392b;
    border-bottom: 2pt solid #c0392b;
    padding-bottom: 3pt;
    margin-top: 0pt;
    margin-bottom: 8pt;
    page-break-after: avoid;
}
h2 {
    font-size: 11pt;
    color: #ffffff;
    background-color: #c0392b;
    padding: 3pt 7pt;
    margin-top: 10pt;
    margin-bottom: 5pt;
    page-break-after: avoid;
}
h3 {
    font-size: 9.5pt;
    color: #2c3e50;
    margin-top: 8pt;
    margin-bottom: 3pt;
    page-break-after: avoid;
}

p { margin: 2pt 0 5pt 0; }

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 4pt 0 8pt 0;
    font-size: 8pt;
}
th {
    background-color: #c0392b;
    color: white;
    padding: 3pt 5pt;
    text-align: left;
    font-weight: bold;
}
td {
    padding: 2.5pt 5pt;
    border-bottom: 0.4pt solid #e0e0e0;
    vertical-align: top;
}

/* Blockquotes */
blockquote {
    margin: 3pt 0 6pt 0;
    padding: 4pt 9pt;
    background: #fff8e1;
    border-left: 3pt solid #f39c12;
    font-size: 8pt;
    color: #555;
}
blockquote p { margin: 1pt 0; }

ul, ol { margin: 2pt 0 5pt 0; padding-left: 14pt; }
li { margin: 1.5pt 0; }

hr {
    border-top: 0.8pt solid #c0392b;
    margin: 7pt 0;
}

strong { font-weight: bold; }
em { font-style: italic; }

pre, code {
    font-family: MyArial;
    font-size: 7.5pt;
    background: #f5f5f5;
    padding: 2pt 4pt;
    white-space: pre-wrap;
    word-wrap: break-word;
}

@page {
    size: A4;
    margin: 12mm 10mm 12mm 10mm;
}
"""

def md_to_html(text):
    return markdown.markdown(
        text,
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
    )

# ── Build trimmed flashcards (top 5 per topic) ─────────────────────────────
def build_flashcards_html():
    parts = ['<h1>Flashcards — Kérdés &amp; Válasz</h1>']
    parts.append('<p><em>Vágd szét soronként · Hajtsd félbe: bal = kérdés, jobb = válasz</em></p>')
    for t in sorted(by_topic):
        parts.append(f'<h2>Téma {t} · {TOPIC_NAMES[t]}</h2>')
        parts.append('<table><thead><tr><th style="width:48%">KÉRDÉS</th><th style="width:52%">VÁLASZ</th></tr></thead><tbody>')
        # Pick top 5: prioritise difficulty=1 first, then 2
        pool = sorted(by_topic[t], key=lambda x: x.get('difficulty', 2))
        for q in pool[:5]:
            qt = q['question_hu'].replace('<', '&lt;').replace('>', '&gt;')
            at = q['answer_hu'].replace('<', '&lt;').replace('>', '&gt;')
            parts.append(f'<tr><td>{qt}</td><td>{at}</td></tr>')
        parts.append('</tbody></table>')
    return '\n'.join(parts)

# ── Build trimmed fill-in-the-blank (top 4 per topic) ──────────────────────
EXTRA_BLANK = {
    1: ["piros","fehér","zöld","erő","hűség","remény","kettős kereszt","hármas halom","jogar","országalma","palást","kokárda","lyukas"],
    2: ["honfoglalás","Kárpát-medence","Aranybulla","tatárjárás","kiegyezés","rendszerváltás","vértanú","honvéd","szabadságharc","Monarchia"],
    3: ["népzene","népdal","reneszánsz","barokk","felvilágosodás","klasszicizmus","romantika","szimfónia","rapszódia","nyelvújítás"],
    4: ["Alaptörvény","Országgyűlés","miniszterelnök","köztársasági elnök","titkos szavazás","főparancsnok"],
    5: ["alapjog","jogegyenlőség","halálbüntetés","Alkotmánybíróság","alkotmányellenes","sérthetetlen","elidegeníthetetlen"],
    6: ["vármegye","főváros","hungarikum","felekezet","tagállam","schengeni","csatlakozás"],
}

def cloze(answer, keywords, extra):
    result = answer
    all_kw = sorted(set(keywords + extra), key=lambda x: -len(x))
    for kw in all_kw:
        if kw and kw.lower() in result.lower():
            idx = result.lower().find(kw.lower())
            blank = '_' * max(len(kw), 5)
            result = result[:idx] + blank + result[idx + len(kw):]
    return result

def build_fitb_html():
    parts = ['<h1>Hiánypótló Feladatok</h1>']
    parts.append('<p><em>Töltsd ki a hiányzó magyar szavakat! Megoldókulcs alul.</em></p>')
    all_answers = []
    for t in sorted(by_topic):
        parts.append(f'<h2>Téma {t} · {TOPIC_NAMES[t]}</h2>')
        extra = EXTRA_BLANK.get(t, [])
        count = 0
        q_entries = []
        for q in by_topic[t]:
            if count >= 4:
                break
            keywords = q.get('keywords_hu', [])
            clozed = cloze(q['answer_hu'], keywords, extra)
            if clozed == q['answer_hu']:
                continue
            count += 1
            qtext = q['question_hu'].replace('<','&lt;').replace('>','&gt;')
            ctext = clozed.replace('<','&lt;').replace('>','&gt;')
            parts.append(f'<p><strong>{count}.</strong> <em>{qtext}</em><br/>{ctext}</p>')
            all_answers.append((t, count, q['answer_hu'].replace('<','&lt;').replace('>','&gt;')))

    parts.append('<hr/><h2>Megoldókulcs</h2>')
    for (t, n, ans) in all_answers:
        parts.append(f'<p><strong>T{t}-{n}.</strong> {ans}</p>')
    return '\n'.join(parts)

# ── Cheat sheets — load and strip ASCII trees (pre blocks) ─────────────────
def load_cheatsheets():
    with open('cheat-sheets.md', encoding='utf-8') as f:
        text = f.read()
    # Remove fenced code blocks (ASCII trees) that bloat pages
    text = re.sub(r'```[\s\S]*?```', '', text)
    return md_to_html(text)

# ── Practice test ───────────────────────────────────────────────────────────
def load_practice():
    with open('practice-test.md', encoding='utf-8') as f:
        text = f.read()
    return md_to_html(text)

# ── Assemble HTML ───────────────────────────────────────────────────────────
body_parts = []

body_parts.append("""
<div class="cover">
  <h1>Magyar Kulturalis Ismereti Vizsga</h1>
  <p class="meta">Teljes tanulmányi csomag nyomtatáshoz</p>
  <p class="meta" style="color:#999;">12 kérdés &middot; 6 témakör &middot; 30 pont &middot; Átmenő: 16 pont</p>
  <div class="toc">
    <h2>Tartalom</h2>
    <ol>
      <li>Gyors összefoglalók (6 x 1 oldal / témakör)</li>
      <li>Flashcards — top 5 kérdés témakörönként</li>
      <li>Hiánypótló feladatok — 4 / témakör</li>
      <li>Mintavizsga (12 kérdés)</li>
    </ol>
  </div>
  <p class="meta" style="margin-top:20pt;">A vizsga <strong>magyarul</strong> van!</p>
</div>
""")

print("  Converting cheat-sheets.md...")
body_parts.append(f'<div class="content-section">{load_cheatsheets()}</div>')

print("  Building compact flashcards...")
body_parts.append(f'<div class="content-section">{build_flashcards_html()}</div>')

print("  Building compact fill-in-the-blank...")
body_parts.append(f'<div class="content-section">{build_fitb_html()}</div>')

print("  Converting practice-test.md...")
body_parts.append(f'<div class="content-section">{load_practice()}</div>')

full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Magyar Kulturalis Ismereti Vizsga</title>
<style>{CSS_STYLE}</style>
</head>
<body>
{''.join(body_parts)}
</body>
</html>"""

print("Writing PDF...")
with open('study-package.pdf', 'wb') as out:
    result = pisa.CreatePDF(full_html.encode('utf-8'), dest=out, encoding='utf-8')

if result.err:
    print(f"Warnings/errors: {result.err}")

size_mb = os.path.getsize('study-package.pdf') / (1024 * 1024)
print(f"Done! study-package.pdf — {size_mb:.1f} MB")
