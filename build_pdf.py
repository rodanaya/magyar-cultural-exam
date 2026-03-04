import sys, os
sys.stdout.reconfigure(encoding='utf-8')

import markdown
from xhtml2pdf import pisa

FILES = [
    ("study-guide.md",       "Tanulmányi Útmutató — Mentális Térképek"),
    ("cheat-sheets.md",      "Gyors Összefoglalók (6 témakör)"),
    ("flashcards.md",        "Flashcards — Kérdés & Válasz"),
    ("fill-in-the-blank.md", "Hiánypótló Feladatok"),
    ("practice-test.md",     "Mintavizsga"),
]

CSS_STYLE = """
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 9pt;
    line-height: 1.45;
    color: #1a1a1a;
}

/* Cover */
.cover {
    text-align: center;
    padding: 60pt 20pt;
    page-break-after: always;
}
.cover h1 {
    font-size: 26pt;
    color: #c0392b;
    border-bottom: 2pt solid #c0392b;
    padding-bottom: 10pt;
}
.cover .meta { font-size: 11pt; color: #666; margin: 6pt 0; }
.cover .toc {
    text-align: left;
    display: block;
    margin: 24pt auto;
    border: 1pt solid #ddd;
    padding: 14pt 20pt;
    width: 300pt;
}
.cover .toc h2 { font-size: 12pt; color: #c0392b; margin-top: 0; }
.cover .toc li { margin: 5pt 0; font-size: 10pt; }

/* Content */
.content-section { page-break-before: always; }

h1 {
    font-size: 16pt;
    color: #c0392b;
    border-bottom: 2pt solid #c0392b;
    padding-bottom: 4pt;
    margin-top: 0;
    page-break-after: avoid;
}
h2 {
    font-size: 12pt;
    color: #c0392b;
    background: #fdf2f2;
    padding: 4pt 8pt;
    margin-top: 14pt;
    page-break-after: avoid;
    page-break-before: always;
}
h3 {
    font-size: 10pt;
    color: #2c3e50;
    margin-top: 10pt;
    margin-bottom: 4pt;
    page-break-after: avoid;
}

p { margin: 3pt 0 6pt 0; }

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 6pt 0 10pt 0;
    font-size: 8.5pt;
}
th {
    background-color: #c0392b;
    color: white;
    padding: 4pt 6pt;
    text-align: left;
    font-weight: bold;
}
td {
    padding: 3pt 6pt;
    border-bottom: 0.5pt solid #e0e0e0;
    vertical-align: top;
}
tr.even td { background-color: #fdf5f5; }

/* Blockquotes */
blockquote {
    margin: 4pt 0 8pt 0;
    padding: 5pt 10pt;
    background: #fff8e1;
    border-left: 3pt solid #f39c12;
    font-size: 8.5pt;
    color: #555;
}
blockquote p { margin: 1pt 0; }

ul, ol { margin: 3pt 0 6pt 0; padding-left: 16pt; }
li { margin: 2pt 0; }

hr {
    border-top: 1pt solid #c0392b;
    margin: 10pt 0;
}

strong { font-weight: bold; }
em { font-style: italic; }

@page {
    size: A4;
    margin: 15mm 12mm 15mm 12mm;
}
"""

def md_to_html(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    # Fix table row alternating color via zebra class injection not easy in xhtml2pdf
    # Use basic markdown conversion
    html = markdown.markdown(
        text,
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
    )
    return html

# Build full HTML
body_parts = []

# Cover
body_parts.append("""
<div class="cover">
  <h1>Magyar Kulturalis Ismereti Vizsga</h1>
  <p class="meta">Teljes tanulmányi csomag nyomtatáshoz</p>
  <p class="meta" style="color:#999;">12 kérdés &middot; 6 témakör &middot; 30 pont &middot; Átmenő: 16 pont</p>
  <div class="toc">
    <h2>Tartalom</h2>
    <ol>
      <li>Tanulmányi útmutató — mentális térképek</li>
      <li>Gyors összefoglalók (6 x 1 oldal)</li>
      <li>Flashcards — kérdés &amp; válasz kártyák</li>
      <li>Hiánypótló feladatok</li>
      <li>Mintavizsga</li>
    </ol>
  </div>
  <p class="meta" style="margin-top:30pt;">A vizsga <strong>magyarul</strong> van!</p>
</div>
""")

for path, title in FILES:
    print(f"  Converting {path}...")
    html_content = md_to_html(path)
    body_parts.append(f'<div class="content-section">{html_content}</div>')

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
    result = pisa.CreatePDF(
        full_html.encode('utf-8'),
        dest=out,
        encoding='utf-8'
    )

if result.err:
    print(f"Errors: {result.err}")
else:
    size_mb = os.path.getsize('study-package.pdf') / (1024 * 1024)
    print(f"Done! study-package.pdf — {size_mb:.1f} MB")
