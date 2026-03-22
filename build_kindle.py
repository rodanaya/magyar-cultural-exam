#!/usr/bin/env python3
"""
Build a Kindle-ready EPUB study guide for Magyar Kulturális Ismereti Vizsga.
Output: kindle_study_guide.epub

No external dependencies — uses only Python stdlib (zipfile, json, uuid).
Send the .epub to your Kindle email or open with Kindle app.
"""

import json
import zipfile
import uuid
from pathlib import Path

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
OUTPUT_FILE    = Path(__file__).parent / "kindle_study_guide.epub"

BOOK_ID    = str(uuid.uuid4())
BOOK_TITLE = "Magyar Kulturális Ismereti Vizsga — Complete Study Guide"
BOOK_LANG  = "hu"
BOOK_DATE  = "2026-03-22"

# ── Topic metadata ────────────────────────────────────────────────────────────

TOPICS = {
    1: {"hu": "Nemzeti Jelképek és Ünnepek",       "en": "National Symbols and Holidays"},
    2: {"hu": "Magyarország Történelme",             "en": "History of Hungary"},
    3: {"hu": "Irodalom és Zenetörténet",            "en": "Literature and Music"},
    4: {"hu": "Az Alaptörvény Alapvető Intézményei","en": "Fundamental Institutions of the Constitution"},
    5: {"hu": "Állampolgári Jogok és Kötelezettségek","en": "Citizens' Rights and Obligations"},
    6: {"hu": "Európa és Magyarország a Mindennapokban","en": "Europe and Everyday Hungary"},
}

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
body {
  font-family: Georgia, serif;
  margin: 0;
  padding: 0.5em 0.8em;
  font-size: 1em;
  line-height: 1.5;
}
h1 { font-size: 1.5em; font-weight: bold; margin: 0.8em 0 0.3em 0; }
h2 { font-size: 1.25em; font-weight: bold; margin: 1em 0 0.3em 0;
     border-bottom: 2px solid #333; padding-bottom: 0.2em; }
h3 { font-size: 1.05em; font-weight: bold; margin: 0.8em 0 0.2em 0; }
h4 { font-size: 1em; font-weight: bold; margin: 0.5em 0 0.1em 0; font-style: italic; }
p  { margin: 0.3em 0; }
ul, ol { margin: 0.3em 0; padding-left: 1.5em; }
li { margin: 0.25em 0; }

/* Tables */
table { border-collapse: collapse; width: 100%; margin: 0.5em 0; font-size: 0.88em; }
th { background-color: #333; color: #fff; padding: 5px 6px; text-align: left; font-weight: bold; }
td { border: 1px solid #999; padding: 4px 6px; vertical-align: top; }
tr:nth-child(even) td { background-color: #f5f5f5; }

/* Chapter break */
.chapter { page-break-before: always; }

/* Callout boxes */
.callout {
  border: 2px solid #555;
  border-radius: 4px;
  padding: 0.5em 0.8em;
  margin: 0.6em 0;
  background: #f0f0f0;
}
.callout-title {
  font-weight: bold;
  font-size: 0.95em;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.3em;
}
.warn  { border-color: #c00; background: #fff0f0; }
.tip   { border-color: #080; background: #f0fff0; }
.info  { border-color: #00a; background: #f0f0ff; }

/* Q&A flashcard style */
.qa-block {
  border-left: 4px solid #555;
  margin: 0.7em 0;
  padding: 0.3em 0.6em;
  page-break-inside: avoid;
}
.qa-block.easy   { border-color: #2a7; }
.qa-block.medium { border-color: #c80; }
.qa-block.hard   { border-color: #c00; }

.q-hu { font-weight: bold; font-size: 1em; }
.q-en { font-style: italic; font-size: 0.88em; color: #555; margin-bottom: 0.3em; }
.answer-label { font-size: 0.78em; font-weight: bold; text-transform: uppercase;
                color: #777; margin-top: 0.4em; }
.a-hu { font-weight: bold; color: #111; }
.a-en { font-style: italic; font-size: 0.88em; color: #444; }
.keywords { font-size: 0.8em; color: #666; margin-top: 0.2em; }
.diff   { font-size: 0.78em; color: #999; float: right; }

/* Practice test */
.pt-q { margin: 0.6em 0; }
.pt-num { font-weight: bold; }

/* Cover */
.cover-title { font-size: 1.8em; font-weight: bold; text-align: center;
               margin: 2em 0 0.5em 0; }
.cover-sub   { font-size: 1em; text-align: center; font-style: italic; color: #444; }
.cover-info  { font-size: 0.9em; text-align: center; margin-top: 2em; }

/* Topic label pill */
.topic-label {
  display: inline-block;
  background: #333;
  color: #fff;
  font-size: 0.8em;
  font-weight: bold;
  padding: 1px 6px;
  border-radius: 3px;
}
"""

# ── Topic study content (hardcoded from source materials) ─────────────────────

TOPIC_CONTENT = {

1: """
<h2>Key Vocabulary</h2>
<table>
<tr><th>Magyar</th><th>English</th><th>Magyar</th><th>English</th></tr>
<tr><td><b>zászló / lobogó</b></td><td>flag</td><td><b>sáv</b></td><td>stripe</td></tr>
<tr><td><b>erő</b></td><td>strength</td><td><b>hűség</b></td><td>loyalty</td></tr>
<tr><td><b>remény</b></td><td>hope</td><td><b>vízszintes</b></td><td>horizontal</td></tr>
<tr><td><b>címer</b></td><td>coat of arms</td><td><b>kettős kereszt</b></td><td>double cross</td></tr>
<tr><td><b>hármas halom</b></td><td>triple hill</td><td><b>jogar</b></td><td>sceptre</td></tr>
<tr><td><b>országalma</b></td><td>orb</td><td><b>palást</b></td><td>coronation mantle</td></tr>
<tr><td><b>Himnusz</b></td><td>national anthem</td><td><b>Szózat</b></td><td>appeal / second anthem</td></tr>
<tr><td><b>kokárda</b></td><td>cockade / rosette</td><td><b>lyukas zászló</b></td><td>flag with hole</td></tr>
<tr><td><b>nemzeti ünnep</b></td><td>national holiday</td><td><b>forradalom</b></td><td>revolution</td></tr>
<tr><td><b>szabadságharc</b></td><td>war of independence</td><td><b>államalapítás</b></td><td>foundation of state</td></tr>
</table>

<h2>The National Flag</h2>
<div class="callout tip">
<div class="callout-title">Mnemonic: R-F-Z</div>
<p><b>Piros</b> (Red, top) = <b>eRő</b> (strength)<br/>
<b>Fehér</b> (White, middle) = <b>hűség</b> (loyalty)<br/>
<b>Zöld</b> (Green, bottom) = <b>remény</b> (hope)<br/>
Three <b>vízszintes</b> (horizontal) stripes.</p>
</div>

<h2>The Coat of Arms (Címer)</h2>
<table>
<tr><th>Part</th><th>What it shows</th><th>Symbolises</th></tr>
<tr><td><b>Left (Bal oldal)</b></td><td>4 silver + 4 red stripes (vágás)</td><td>Árpád dynasty kings</td></tr>
<tr><td><b>Right (Jobb oldal)</b></td><td>Double cross (kettős kereszt) on triple hill (hármas halom)</td><td>Christianity / geography</td></tr>
<tr><td><b>Top (Teteje)</b></td><td>Holy Crown — <b>Szent Korona</b></td><td>Constitutional continuity</td></tr>
</table>

<h2>Holy Crown &amp; Coronation Insignia</h2>
<ul>
<li>The <b>Szent Korona</b> is displayed in the <b>Parlament</b> (Parliament building)</li>
<li>It symbolises constitutional continuity and national unity</li>
<li><b>Koronázási jelvények</b> (Coronation insignia): <b>Korona · Jogar · Országalma · Kard · Palást</b></li>
<li><b>Koronázó városok</b> (coronation cities): Buda · Esztergom · <b>Pozsony</b> · Sopron · Székesfehérvár</li>
</ul>

<h2>National Anthem &amp; Szózat</h2>
<table>
<tr><th></th><th>Himnusz (Anthem)</th><th>Szózat (Appeal)</th></tr>
<tr><td><b>Szerző (Author)</b></td><td>Kölcsey Ferenc</td><td>Vörösmarty Mihály</td></tr>
<tr><td><b>Év (Year)</b></td><td><b>1823</b></td><td><b>1836</b></td></tr>
<tr><td><b>Zene (Music)</b></td><td>Erkel Ferenc</td><td>Egressy Béni</td></tr>
</table>
<p>Both are sung on national holidays. The Szózat is sometimes called the "second anthem."</p>

<h2>National Holidays</h2>
<table>
<tr><th>Date</th><th>Event</th><th>Symbol</th></tr>
<tr><td><b>Március 15.</b></td><td>1848–49 Revolution &amp; War of Independence</td><td>Piros-fehér-zöld <b>kokárda</b></td></tr>
<tr><td><b>Augusztus 20.</b></td><td>Foundation of the State · Saint Stephen's Day</td><td>Fireworks · Szent Jobb procession</td></tr>
<tr><td><b>Október 23.</b></td><td>1956 Revolution &amp; War of Independence</td><td><b>Lyukas zászló</b> (Rákosi coat of arms cut out)</td></tr>
</table>
<div class="callout warn">
<div class="callout-title">Exam Trap</div>
<p>The <b>lyukas zászló</b> (flag with hole) belongs to <b>1956</b>, not 1848. The <b>kokárda</b> (red-white-green rosette) belongs to <b>1848</b>.</p>
</div>
""",

2: """
<h2>Key Vocabulary</h2>
<table>
<tr><th>Magyar</th><th>English</th><th>Magyar</th><th>English</th></tr>
<tr><td><b>honfoglalás</b></td><td>conquest of homeland</td><td><b>törzs</b></td><td>tribe</td></tr>
<tr><td><b>Kárpát-medence</b></td><td>Carpathian Basin</td><td><b>fejedelem</b></td><td>chieftain / prince</td></tr>
<tr><td><b>Aranybulla</b></td><td>Golden Bull</td><td><b>tatárjárás</b></td><td>Mongol invasion</td></tr>
<tr><td><b>ostrom</b></td><td>siege</td><td><b>török hódoltság</b></td><td>Ottoman occupation</td></tr>
<tr><td><b>vértanú</b></td><td>martyr</td><td><b>honvéd</b></td><td>homeland defender</td></tr>
<tr><td><b>kiegyezés</b></td><td>Compromise / Ausgleich</td><td><b>Monarchia</b></td><td>Austro-Hungarian Monarchy</td></tr>
<tr><td><b>békediktátum</b></td><td>peace diktat</td><td><b>rendszerváltás</b></td><td>regime change</td></tr>
<tr><td><b>megtorlás</b></td><td>retaliation / reprisal</td><td><b>egypártrendszer</b></td><td>one-party system</td></tr>
</table>

<h2>Master Timeline</h2>
<table>
<tr><th>Year</th><th>Event</th><th>Key Name</th></tr>
<tr><td><b>895–896</b></td><td>Honfoglalás — 7 tribes enter Carpathian Basin</td><td>Árpád</td></tr>
<tr><td><b>1001. jan. 1.</b></td><td>I. István megkoronázása — first Christian king</td><td>Szent István</td></tr>
<tr><td><b>1222</b></td><td>Aranybulla — rights of nobles</td><td>II. András</td></tr>
<tr><td><b>1241–42</b></td><td>Tatárjárás (Mongol invasion) — devastating</td><td>IV. Béla*</td></tr>
<tr><td><b>1456</b></td><td>Nándorfehérvári csata — halted Ottomans 70 years</td><td>Hunyadi János</td></tr>
<tr><td><b>1458–1490</b></td><td>Renaissance golden age</td><td>Hunyadi Mátyás</td></tr>
<tr><td><b>1526. aug. 29.</b></td><td>Mohácsi csata — crushing defeat vs Ottomans</td><td>—</td></tr>
<tr><td><b>1541</b></td><td>Ottomans take Buda; country splits 3 ways (~150 yr)</td><td>—</td></tr>
<tr><td><b>1686. szept. 2.</b></td><td>Habsburgs recapture Buda</td><td>—</td></tr>
<tr><td><b>1703–1711</b></td><td>National uprising against Habsburgs</td><td>II. Rákóczi Ferenc</td></tr>
<tr><td><b>1848. márc. 15.</b></td><td>Revolution — Pilvax, 12 points, National Museum</td><td>Petőfi · Jókai · Vasvári</td></tr>
<tr><td><b>1848. ápr. 11.</b></td><td>First responsible government</td><td>PM: Batthyány Lajos</td></tr>
<tr><td><b>1849. aug. 13.</b></td><td>Surrender at Világos</td><td>Görgei Artúr</td></tr>
<tr><td><b>1849. okt. 6.</b></td><td>13 Aradi vértanú + Batthyány executed</td><td>13 martyrs</td></tr>
<tr><td><b>1867</b></td><td>Kiegyezés — Austro-Hungarian Monarchy formed</td><td>Deák Ferenc</td></tr>
<tr><td><b>1914. jún. 28.</b></td><td>Assassination in Sarajevo → WWI</td><td>Ferenc Ferdinánd</td></tr>
<tr><td><b>1920. jún. 4.</b></td><td>Trianoni békeszerződés — Hungary loses 2/3 territory</td><td>—</td></tr>
<tr><td><b>1944. márc. 19.</b></td><td>German occupation; Holocaust ~500–600k victims</td><td>—</td></tr>
<tr><td><b>1956. okt. 23.</b></td><td>Revolution — peaceful demo turns armed</td><td>Nagy Imre</td></tr>
<tr><td><b>1956. nov. 4.</b></td><td>Soviet troops suppress uprising</td><td>Kádár János</td></tr>
<tr><td><b>1989. jún. 16.</b></td><td>Ceremonial reburial of Nagy Imre</td><td>—</td></tr>
<tr><td><b>1990</b></td><td>First free elections after regime change</td><td>PM: Antall József · President: Göncz Árpád</td></tr>
<tr><td><b>1991</b></td><td>Soviet troops leave Hungary</td><td>—</td></tr>
</table>
<p><small>* IV. Béla = "második honalapító" (second founder of the homeland) — rebuilt the country after the Mongol invasion.</small></p>

<h2>Reform Era Key Figures (1825–1848)</h2>
<table>
<tr><th>Person</th><th>Why important</th></tr>
<tr><td><b>Széchenyi István</b> (1791–1860)</td><td>"a legnagyobb magyar" · Founded MTA (Academy of Sciences) · Built Lánchíd (Chain Bridge — first stone bridge Buda–Pest)</td></tr>
<tr><td><b>Kossuth Lajos</b></td><td>Finance minister 1848; leading revolutionary voice</td></tr>
<tr><td><b>Batthyány Lajos</b></td><td>First Prime Minister of responsible government; martyred Oct 6, 1849</td></tr>
<tr><td><b>Deák Ferenc</b></td><td>"a haza bölcse" (wise man of the homeland); architect of the 1867 Compromise</td></tr>
<tr><td><b>Petőfi Sándor</b></td><td>Poet; led March 15, 1848 revolutionary youth at Pilvax Café</td></tr>
</table>

<div class="callout warn">
<div class="callout-title">Numbers to Memorise</div>
<ul>
<li>Trianon: Hungary lost <b>~2/3</b> of territory; population <b>18.2M → 7.6M</b>; <b>3.3M</b> Hungarians left outside borders</li>
<li>1848 first government: Finance=Kossuth, Justice=Deák, PM=Batthyány</li>
<li>1956: Corvin köz &amp; Széna tér = emblematic resistance sites</li>
</ul>
</div>
""",

3: """
<h2>Key Vocabulary</h2>
<table>
<tr><th>Magyar</th><th>English</th><th>Magyar</th><th>English</th></tr>
<tr><td><b>népzene</b></td><td>folk music</td><td><b>népdal</b></td><td>folk song</td></tr>
<tr><td><b>zenész / zeneszerző</b></td><td>musician / composer</td><td><b>opera</b></td><td>opera</td></tr>
<tr><td><b>szimfónia</b></td><td>symphony</td><td><b>rapszódia</b></td><td>rhapsody</td></tr>
<tr><td><b>korszak</b></td><td>era / period</td><td><b>reneszánsz</b></td><td>Renaissance</td></tr>
<tr><td><b>barokk</b></td><td>Baroque</td><td><b>felvilágosodás</b></td><td>Enlightenment</td></tr>
<tr><td><b>klasszicizmus</b></td><td>Classicism</td><td><b>romantika</b></td><td>Romanticism</td></tr>
<tr><td><b>költő</b></td><td>poet</td><td><b>író</b></td><td>writer</td></tr>
<tr><td><b>regény</b></td><td>novel</td><td><b>dráma</b></td><td>drama / play</td></tr>
<tr><td><b>eposz</b></td><td>epic poem</td><td><b>népzenekutató</b></td><td>folk music researcher</td></tr>
</table>

<h2>Hungarian Composers</h2>
<table>
<tr><th>Composer</th><th>Key Works</th><th>Also known for</th></tr>
<tr><td><b>Erkel Ferenc</b></td><td>Himnusz (zenéje) · <i>Bánk bán</i> (opera)</td><td>Founded Hungarian Opera</td></tr>
<tr><td><b>Liszt Ferenc</b></td><td><i>Magyar rapszódiák</i> (Hungarian Rhapsodies)</td><td>World-famous pianist</td></tr>
<tr><td><b>Bartók Béla</b></td><td><i>A kékszakállú herceg vára</i> (Bluebeard's Castle)</td><td>Folk music researcher</td></tr>
<tr><td><b>Kodály Zoltán</b></td><td><i>Háry János</i></td><td>Folk music researcher; Kodály method</td></tr>
</table>

<h2>Hungarian Literature by Era</h2>
<table>
<tr><th>Korszak</th><th>Szerző</th><th>Fő mű</th></tr>
<tr><td><b>Reneszánsz</b></td><td>Janus Pannonius<br/>Balassi Bálint</td><td>Pannónia dicsérete<br/>Hogy Júliára talála…</td></tr>
<tr><td><b>Barokk</b></td><td>Zrínyi Miklós</td><td>Szigeti veszedelem (epic)</td></tr>
<tr><td><b>Felvilágosodás</b></td><td>Csokonai Vitéz Mihály<br/>Batsányi János</td><td>A reményhez<br/>A franciaországi változásokra</td></tr>
<tr><td><b>Klasszicizmus</b></td><td>Kazinczy Ferenc<br/>Berzsenyi Dániel</td><td>Language reform leader<br/>Az első szerelem</td></tr>
<tr><td><b>Romantika</b></td><td>Kölcsey Ferenc · Vörösmarty Mihály<br/>Petőfi Sándor · Jókai Mór<br/>Arany János · Katona József · Madách Imre</td><td>Himnusz · Szózat<br/>Nemzeti dal · A kőszívű ember fiai<br/>A walesi bárdok · Bánk bán · Az ember tragédiája</td></tr>
<tr><td><b>XX. század</b></td><td>Ady Endre · Móricz Zsigmond<br/>Kosztolányi Dezső · Karinthy Frigyes<br/>József Attila · Radnóti Miklós · Márai Sándor</td><td>Elbocsátó, szép üzenet · Rokonok<br/>Édes Anna · Így írtok ti<br/>Tiszta szívvel · Nem tudhatom… · Egy polgár vallomása</td></tr>
</table>

<h2>European Literature &amp; Music</h2>
<table>
<tr><th>Creator</th><th>Work</th><th>Note</th></tr>
<tr><td>William Shakespeare</td><td>Rómeó és Júlia</td><td>—</td></tr>
<tr><td>Voltaire</td><td>Candide</td><td>—</td></tr>
<tr><td>J. W. von Goethe</td><td>Faust</td><td>—</td></tr>
<tr><td><b>Beethoven</b></td><td><b>IX. szimfónia</b> (4th mvt = Örömóda)</td><td><b>EU Anthem</b> · text by Schiller (1785) · premiere 1824</td></tr>
<tr><td>Mozart</td><td>A varázsfuvola (The Magic Flute)</td><td>—</td></tr>
<tr><td>Csajkovszkij</td><td>A hattyúk tava (Swan Lake)</td><td>—</td></tr>
</table>
<div class="callout info">
<div class="callout-title">EU Anthem Key Facts</div>
<p><b>Beethoven</b> IX. szimfónia · 4th movement · <b>Örömóda</b> (Ode to Joy)<br/>
Text by <b>Friedrich Schiller</b> · written <b>1785</b> · symphony premiered <b>1824</b><br/>
Adopted as EU anthem.</p>
</div>
""",

4: """
<h2>Key Vocabulary</h2>
<table>
<tr><th>Magyar</th><th>English</th><th>Magyar</th><th>English</th></tr>
<tr><td><b>Alaptörvény</b></td><td>Fundamental Law / Constitution</td><td><b>jogrend</b></td><td>legal system</td></tr>
<tr><td><b>Országgyűlés</b></td><td>National Assembly / Parliament</td><td><b>képviselő</b></td><td>MP / representative</td></tr>
<tr><td><b>törvényhozás</b></td><td>legislation</td><td><b>költségvetés</b></td><td>budget</td></tr>
<tr><td><b>Kormány</b></td><td>Government</td><td><b>miniszterelnök</b></td><td>Prime Minister</td></tr>
<tr><td><b>végrehajtó hatalom</b></td><td>executive power</td><td><b>törvényhozó hatalom</b></td><td>legislative power</td></tr>
<tr><td><b>köztársasági elnök</b></td><td>President of the Republic</td><td><b>államfő</b></td><td>head of state</td></tr>
<tr><td><b>titkos szavazás</b></td><td>secret ballot</td><td><b>főparancsnok</b></td><td>Commander-in-Chief</td></tr>
<tr><td><b>feloszlatás</b></td><td>dissolution (of Parliament)</td><td><b>megbízatás</b></td><td>term of office</td></tr>
</table>

<h2>The Alaptörvény (Fundamental Law)</h2>
<div class="callout info">
<div class="callout-title">Critical Dates</div>
<p>Elfogadva (adopted): <b>2011. április 18.</b><br/>
Hatályba lépett (in force): <b>2012. január 1.</b><br/>
Hungary's highest legal norm — basis of the entire legal system.</p>
</div>

<h2>Three Branches of Power (Három Hatalmi Ág)</h2>
<table>
<tr><th>Branch</th><th>Institution</th><th>Key Numbers</th><th>Notes</th></tr>
<tr><td><b>Törvényhozó</b> (Legislative)</td><td>Országgyűlés (Parliament)</td><td><b>199 képviselő · 4 év</b></td><td>Supreme representative body; creates &amp; amends Fundamental Law; adopts budget; elects PM</td></tr>
<tr><td><b>Végrehajtó</b> (Executive)</td><td>Kormány (Government)</td><td>PM + 13 ministers; <b>14 minisztérium</b></td><td>PM elected by National Assembly; represents Hungary in European Council</td></tr>
<tr><td><b>Igazságszolgáltató</b> (Judicial)</td><td>Bíróságok + Alkotmánybíróság</td><td>—</td><td>Constitutional Court reviews constitutionality of laws</td></tr>
</table>

<h2>Current Leaders</h2>
<table>
<tr><th>Position</th><th>Person</th><th>Term</th><th>Elected by</th></tr>
<tr><td><b>Miniszterelnök</b> (PM)</td><td>Orbán Viktor</td><td>4 years</td><td>Országgyűlés</td></tr>
<tr><td><b>Köztársasági Elnök</b> (President)</td><td>Dr. Sulyok Tamás</td><td><b>5 years</b> (max 1× re-elect)</td><td>Országgyűlés — titkos szavazás</td></tr>
</table>

<h2>The 14 Ministries</h2>
<p>Agrár · Belügy · Energiaügy · Építési és Közlekedési · EU-ügyek · Honvédelmi · Igazságügyi · Közigazgatási és Területfejlesztési · Kulturális és Innovációs · Külgazdasági és Külügy · Miniszterelnöki Kabinetiroda · Miniszterelnökség · Nemzetgazdasági</p>

<div class="callout warn">
<div class="callout-title">Numbers to Know</div>
<ul>
<li>Parliament: <b>199 MPs</b>, <b>4-year</b> terms</li>
<li>President: <b>5-year</b> term, max <b>1 re-election</b></li>
<li>President is Commander-in-Chief of the Armed Forces</li>
<li>President can dissolve Parliament in cases specified by the Fundamental Law</li>
</ul>
</div>
""",

5: """
<h2>Key Vocabulary</h2>
<table>
<tr><th>Magyar</th><th>English</th><th>Magyar</th><th>English</th></tr>
<tr><td><b>alapjog</b></td><td>fundamental right</td><td><b>állampolgár</b></td><td>citizen</td></tr>
<tr><td><b>jogegyenlőség</b></td><td>legal equality</td><td><b>emberi méltóság</b></td><td>human dignity</td></tr>
<tr><td><b>gyülekezési szabadság</b></td><td>freedom of assembly</td><td><b>szólásszabadság</b></td><td>freedom of speech</td></tr>
<tr><td><b>sajtószabadság</b></td><td>freedom of the press</td><td><b>lelkiismereti szabadság</b></td><td>freedom of conscience</td></tr>
<tr><td><b>halálbüntetés</b></td><td>capital punishment</td><td><b>Alkotmánybíróság</b></td><td>Constitutional Court</td></tr>
<tr><td><b>alkotmányellenes</b></td><td>unconstitutional</td><td><b>sérthetetlen</b></td><td>inviolable</td></tr>
<tr><td><b>elidegeníthetetlen</b></td><td>inalienable</td><td><b>alapelv</b></td><td>fundamental principle</td></tr>
</table>

<h2>Historical Milestones of Human Rights</h2>
<table>
<tr><th>Document</th><th>Year</th><th>Country</th></tr>
<tr><td><b>Magna Carta Libertatum</b></td><td><b>1215</b></td><td>England (Anglia)</td></tr>
<tr><td><b>Aranybulla</b></td><td><b>1222</b></td><td>Hungary (Magyarország)</td></tr>
<tr><td><b>Emberi és Polgári Jogok Nyilatkozata</b></td><td><b>1789</b></td><td>France (Franciaország)</td></tr>
<tr><td><b>Emberi Jogok Európai Egyezménye</b></td><td><b>1950</b></td><td>Europe — obliges states to ensure listed rights for all under their jurisdiction</td></tr>
</table>

<h2>Three Generations of Rights</h2>
<table>
<tr><th>Generation</th><th>Type</th><th>Examples</th></tr>
<tr><td><b>1. generáció</b></td><td>Civil &amp; political</td><td>Right to life · personal freedom · freedom of assembly · freedom of conscience &amp; religion · freedom of speech &amp; press</td></tr>
<tr><td><b>2. generáció</b></td><td>Social &amp; economic</td><td>Right to work · right to strike · right to education · right to social security</td></tr>
<tr><td><b>3. generáció</b></td><td>Collective &amp; solidarity</td><td>Right to health &amp; environment · children's rights · patients' rights · rights of people with disabilities</td></tr>
</table>

<h2>Fundamental Rights in the Alaptörvény</h2>
<ul>
<li>Törvény előtti egyenlőség (equality before the law)</li>
<li>Élethez és emberi méltósághoz való jog (right to life and human dignity)</li>
<li>Tisztességes eljáráshoz való jog (right to a fair trial)</li>
<li>Gondolat, lelkiismeret és vallásszabadság (freedom of thought, conscience, religion)</li>
<li>Véleménynyilvánítás szabadsága (freedom of expression)</li>
<li>Gyülekezési szabadság (freedom of assembly)</li>
<li>Tulajdonjog és örökléshez való jog (right to property and inheritance)</li>
<li>Személyes adatok védelméhez való jog (right to protection of personal data)</li>
</ul>

<div class="callout warn">
<div class="callout-title">Capital Punishment</div>
<p>Halálbüntetés abolished in <b>1990</b> — the <b>Alkotmánybíróság</b> (Constitutional Court) declared it <b>alkotmányellenes</b> (unconstitutional).<br/>
<b>Principle:</b> A fundamental right may only be restricted to protect another fundamental right or constitutional value.</p>
</div>
""",

6: """
<h2>Key Vocabulary</h2>
<table>
<tr><th>Magyar</th><th>English</th><th>Magyar</th><th>English</th></tr>
<tr><td><b>főváros</b></td><td>capital city</td><td><b>vármegye</b></td><td>county</td></tr>
<tr><td><b>kerület</b></td><td>district</td><td><b>szomszédos ország</b></td><td>neighbouring country</td></tr>
<tr><td><b>hungarikum</b></td><td>uniquely Hungarian thing</td><td><b>felekezet</b></td><td>religious denomination</td></tr>
<tr><td><b>tagállam</b></td><td>member state</td><td><b>csatlakozás</b></td><td>accession / joining</td></tr>
<tr><td><b>schengeni övezet</b></td><td>Schengen Area</td><td><b>pénznem</b></td><td>currency</td></tr>
<tr><td><b>tájegység</b></td><td>geographical region</td><td><b>nép- és iparművészet</b></td><td>folk and applied arts</td></tr>
</table>

<h2>Hungary — Key Facts</h2>
<table>
<tr><th>Fact</th><th>Value</th></tr>
<tr><td>Államforma (Form of government)</td><td>Köztársaság (Republic)</td></tr>
<tr><td>Terület (Area)</td><td><b>93 000 km²</b></td></tr>
<tr><td>Népesség (Population)</td><td><b>9,6 millió</b></td></tr>
<tr><td>Főváros (Capital)</td><td><b>Budapest</b></td></tr>
<tr><td>Pénznem (Currency)</td><td><b>Forint</b></td></tr>
<tr><td>Hivatalos nyelv (Language)</td><td>Magyar (Hungarian)</td></tr>
<tr><td>Vármegyék (Counties)</td><td><b>19</b></td></tr>
<tr><td>Szomszédos országok (Neighbours)</td><td>Szlovákia · Ukrajna · Románia · Szerbia · Horvátország · Szlovénia · <b>Ausztria</b> (7 countries)</td></tr>
<tr><td>Legnagyobb tavak (Biggest lakes)</td><td>Balaton · Fertő tó · Velencei-tó</td></tr>
<tr><td>Legnagyobb folyók (Main rivers)</td><td>Duna · Tisza · Dráva · Rába</td></tr>
<tr><td>Tájegységek (Regions)</td><td>Alföld · Alpokalja · Dunántúli-dombság · Dunántúl-középhegység · Északi-középhegység · Kisalföld</td></tr>
</table>

<h2>Budapest</h2>
<ul>
<li>Founded <b>1873. november 17.</b> — uniting Pest + Buda + Óbuda</li>
<li><b>23 kerület</b> (districts) since 1994</li>
<li>Key landmarks: Budavári Palota · Citadella · Gellért Gyógyfürdő · Halászbástya · Hősök tere · Magyar Nemzeti Múzeum · Magyar Zene Háza · Magyar Állami Operaház · Mátyás-templom · <b>Parlament</b> · Szent István Bazilika · <b>Széchenyi Lánchíd</b> · Szépművészeti Múzeum · Vajdahunyad vára</li>
</ul>

<h2>Hungarikumok</h2>
<table>
<tr><th>Category</th><th>Examples</th></tr>
<tr><td><b>Ételek (Food)</b></td><td>gulyásleves · halászlé (bajai / tiszai) · dobostorta · Pick téliszalámi · makói hagyma · kalocsai/szegedi fűszerpaprika</td></tr>
<tr><td><b>Italok (Drinks)</b></td><td>Tokaji aszú · Egri bikavér · pálinka</td></tr>
<tr><td><b>Kulturális</b></td><td>mohácsi busójárás · Pannonhalmi Bencés Főapátság · Hollókő · Füredi Anna-bál</td></tr>
<tr><td><b>Állatok (Animals)</b></td><td>szürke szarvasmarha · puli · komondor · kuvasz · magyar vizsla · erdélyi kopó</td></tr>
<tr><td><b>Nép- és iparművészet</b></td><td>halasi csipke · matyó népművészet · hollóházi porcelán · Zsolnay-porcelán</td></tr>
</table>

<h2>Christianity in Hungary</h2>
<ul>
<li><b>Felekezetek:</b> Katolikus (latin és görög) · Református · Evangélikus</li>
<li><b>Főbb ünnepek:</b> Karácsony (dec. 24–26.) · Húsvét · Augusztus 20. (Szent Jobb Körmenet + tűzijáték)</li>
<li><b>Magyar szentek:</b> István · László · Imre · Gellért · Árpád-házi Margit · Árpád-házi Erzsébet</li>
</ul>

<h2>Hungary and the EU</h2>
<table>
<tr><th>Fact</th><th>Value</th></tr>
<tr><td>EU csatlakozás</td><td><b>2004. május 1.</b></td></tr>
<tr><td>Schengen csatlakozás</td><td><b>2007</b></td></tr>
<tr><td>EU citizens</td><td>450 millió</td></tr>
<tr><td>EU headquarters</td><td>Brüsszel (Brussels)</td></tr>
<tr><td>EU intézmények</td><td>Európai Bizottság · Tanács · Európai Parlament · Európai Tanács</td></tr>
<tr><td>EU elections</td><td>Every <b>5 years</b></td></tr>
<tr><td>Hungarian MEPs</td><td><b>21 fő</b></td></tr>
<tr><td>EU flag</td><td>Kék alap, <b>12 sárga csillag</b> körben</td></tr>
<tr><td>EU anthem</td><td>Beethoven IX. szimfónia — Örömóda</td></tr>
<tr><td>EU member states</td><td><b>27</b></td></tr>
</table>
<p><b>All 27 EU member states:</b> Ausztria · Belgium · Bulgária · Ciprus · Csehország · Dánia · Észtország · Finnország · Franciaország · Görögország · Hollandia · Horvátország · Írország · Lengyelország · Lettország · Litvánia · Luxemburg · <b>Magyarország</b> · Málta · Németország · Olaszország · Portugália · Románia · Spanyolország · Svédország · Szlovákia · Szlovénia</p>
""",
}

# ── HTML helpers ──────────────────────────────────────────────────────────────

def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def xhtml_page(title: str, body: str, css_path: str = "../styles.css") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="hu">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
  <title>{html_escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="{css_path}"/>
</head>
<body>
{body}
</body>
</html>"""

DIFF_LABEL = {1: "★ easy", 2: "★★ medium", 3: "★★★ hard"}
DIFF_CLASS = {1: "easy", 2: "medium", 3: "hard"}

def qa_block(q: dict, num: int) -> str:
    d = q.get("difficulty", 1)
    kw = ", ".join(q.get("keywords_hu", []))
    kw_html = f'<div class="keywords">🔑 {html_escape(kw)}</div>' if kw else ""
    return f"""<div class="qa-block {DIFF_CLASS[d]}">
  <div class="diff">{DIFF_LABEL[d]}</div>
  <div class="q-hu">Q{num}. {html_escape(q["question_hu"])}</div>
  <div class="q-en">{html_escape(q["question_en"])}</div>
  <div class="answer-label">▼ Answer</div>
  <div class="a-hu">{html_escape(q["answer_hu"])}</div>
  <div class="a-en">{html_escape(q["answer_en"])}</div>
  {kw_html}
</div>"""

# ── Page builders ─────────────────────────────────────────────────────────────

def build_cover() -> str:
    body = """
<div class="cover-title">Magyar Kulturális<br/>Ismereti Vizsga</div>
<div class="cover-sub">Complete Kindle Study Guide</div>
<hr/>
<div class="cover-info">
<p><b>Exam format:</b> 12 questions · 2 per topic · 60 minutes</p>
<p><b>Total points:</b> 30 · <b>Pass mark:</b> 16+ points</p>
<p><b>6 Topics</b> · <b>132 Q&amp;As</b> · Practice Test · Quick-Review Cards</p>
<hr/>
<p><i>The exam is conducted in Hungarian.<br/>
Study the Hungarian questions and answers first.</i></p>
</div>
"""
    return xhtml_page("Cover", body, css_path="styles.css")

def build_intro() -> str:
    body = """<div class="chapter">
<h1>How to Use This Guide</h1>

<div class="callout info">
<div class="callout-title">Exam at a Glance</div>
<p><b>Format:</b> 12 oral/written questions — <b>2 per topic</b><br/>
<b>Time:</b> 60 minutes<br/>
<b>Points:</b> 30 total — pass with <b>16 or more</b><br/>
<b>Language:</b> Hungarian (Magyar)<br/>
<b>Topics:</b> 6 (see below)</p>
</div>

<h2>The 6 Topics</h2>
<table>
<tr><th>#</th><th>Magyar</th><th>English</th><th>Questions</th></tr>
<tr><td>1</td><td>Nemzeti Jelképek és Ünnepek</td><td>National Symbols and Holidays</td><td>19</td></tr>
<tr><td>2</td><td>Magyarország Történelme</td><td>History of Hungary</td><td>24</td></tr>
<tr><td>3</td><td>Irodalom és Zenetörténet</td><td>Literature and Music</td><td>22</td></tr>
<tr><td>4</td><td>Az Alaptörvény Alapvető Intézményei</td><td>Fundamental Institutions of the Constitution</td><td>17</td></tr>
<tr><td>5</td><td>Állampolgári Jogok és Kötelezettségek</td><td>Citizens' Rights and Obligations</td><td>14</td></tr>
<tr><td>6</td><td>Európa és Magyarország a Mindennapokban</td><td>Europe and Everyday Hungary</td><td>36</td></tr>
</table>

<h2>How to Study on the Go</h2>
<ol>
<li><b>Read the topic summary</b> — vocabulary + key facts tables first.</li>
<li><b>Work through Q&amp;As</b> — read the Hungarian question aloud, pause, then check the answer.</li>
<li><b>Focus on keywords</b> — highlighted with 🔑. These are the exact words examiners listen for.</li>
<li><b>Do the practice test</b> — all 132 questions without answers. Check the answer key after.</li>
<li><b>Use the quick-review cards</b> — one page per topic. Great for last-minute revision.</li>
</ol>

<h2>Difficulty Guide</h2>
<table>
<tr><td><b>★ Easy</b></td><td>Direct factual recall — know these cold</td></tr>
<tr><td><b>★★ Medium</b></td><td>Requires specific names / dates / numbers</td></tr>
<tr><td><b>★★★ Hard</b></td><td>Nuanced — requires fuller explanation</td></tr>
</table>

<div class="callout tip">
<div class="callout-title">Top Exam Tips</div>
<ul>
<li>Use the <b>exact Hungarian keywords</b> in your answers — examiners listen for them.</li>
<li>Numbers matter: 199 MPs, 4-year terms, 5-year presidential term, 93,000 km², 9.6M people.</li>
<li>Know all <b>3 national holiday dates</b> and what they commemorate.</li>
<li>The exam picks 2 random questions from each topic — all 6 topics will be tested.</li>
<li>Speak in complete sentences, not just single-word answers.</li>
</ul>
</div>
</div>"""
    return xhtml_page("Introduction", body)

def build_topic_chapter(topic_num: int, questions: list) -> str:
    t = TOPICS[topic_num]
    tqs = [q for q in questions if q["topic"] == topic_num]
    content = TOPIC_CONTENT[topic_num]

    qa_html = ""
    for i, q in enumerate(tqs, 1):
        qa_html += qa_block(q, i)

    body = f"""<div class="chapter">
<h1><span class="topic-label">Topic {topic_num}</span><br/>{html_escape(t["hu"])}</h1>
<p><i>{html_escape(t["en"])}</i> &nbsp;·&nbsp; <b>{len(tqs)} questions</b></p>

{content}

<h2>All Questions for This Topic</h2>
<p>★ = easy &nbsp; ★★ = medium &nbsp; ★★★ = hard</p>
{qa_html}
</div>"""
    return xhtml_page(f"Topic {topic_num}: {t['hu']}", body)

def build_master_reference() -> str:
    body = """<div class="chapter">
<h1>Master Quick-Reference</h1>
<p><i>The most-tested facts across all topics.</i></p>

<h2>Critical Numbers</h2>
<table>
<tr><th>Number</th><th>What it means</th></tr>
<tr><td><b>199</b></td><td>MPs in the National Assembly (Képviselők száma)</td></tr>
<tr><td><b>4 years</b></td><td>Parliamentary term (Megbízatás — Képviselők)</td></tr>
<tr><td><b>5 years</b></td><td>Presidential term (max 1× re-election)</td></tr>
<tr><td><b>14</b></td><td>Ministries in the Government</td></tr>
<tr><td><b>19</b></td><td>Vármegyék (counties) in Hungary</td></tr>
<tr><td><b>23</b></td><td>Districts (kerületek) of Budapest (since 1994)</td></tr>
<tr><td><b>27</b></td><td>EU member states</td></tr>
<tr><td><b>21</b></td><td>Hungarian MEPs in the European Parliament</td></tr>
<tr><td><b>5 years</b></td><td>Frequency of EU Parliament elections</td></tr>
<tr><td><b>93 000 km²</b></td><td>Area of Hungary</td></tr>
<tr><td><b>9,6 millió</b></td><td>Population of Hungary</td></tr>
<tr><td><b>450 millió</b></td><td>EU total population</td></tr>
<tr><td><b>16+</b></td><td>Points needed to pass the exam (out of 30)</td></tr>
<tr><td><b>12</b></td><td>Exam questions (2 per topic)</td></tr>
<tr><td><b>7</b></td><td>Hungary's neighbouring countries</td></tr>
</table>

<h2>Critical Dates</h2>
<table>
<tr><th>Date</th><th>Event</th></tr>
<tr><td><b>895–896</b></td><td>Honfoglalás (Conquest) — Árpád</td></tr>
<tr><td><b>1001. jan. 1.</b></td><td>I. István megkoronázása (first Christian king)</td></tr>
<tr><td><b>1215</b></td><td>Magna Carta — England</td></tr>
<tr><td><b>1222</b></td><td>Aranybulla — Hungary (II. András)</td></tr>
<tr><td><b>1823</b></td><td>Himnusz written by Kölcsey Ferenc</td></tr>
<tr><td><b>1836</b></td><td>Szózat written by Vörösmarty Mihály</td></tr>
<tr><td><b>1848. márc. 15.</b></td><td>Revolution — national holiday</td></tr>
<tr><td><b>1849. okt. 6.</b></td><td>13 Aradi vértanú + Batthyány executed</td></tr>
<tr><td><b>1867</b></td><td>Kiegyezés — Deák Ferenc</td></tr>
<tr><td><b>1785</b></td><td>Schiller writes "Ode to Joy" (EU anthem text)</td></tr>
<tr><td><b>1789</b></td><td>French Declaration of Rights</td></tr>
<tr><td><b>1824</b></td><td>Beethoven IX. szimfónia premiere</td></tr>
<tr><td><b>1873. nov. 17.</b></td><td>Budapest unified (Pest + Buda + Óbuda)</td></tr>
<tr><td><b>1920. jún. 4.</b></td><td>Trianoni békeszerződés — Hungary loses 2/3 territory</td></tr>
<tr><td><b>1950</b></td><td>European Convention on Human Rights</td></tr>
<tr><td><b>1956. okt. 23.</b></td><td>Revolution — national holiday</td></tr>
<tr><td><b>1990</b></td><td>Capital punishment abolished (Alkotmánybíróság)</td></tr>
<tr><td><b>2004. május 1.</b></td><td>Hungary joins EU</td></tr>
<tr><td><b>2007</b></td><td>Hungary joins Schengen</td></tr>
<tr><td><b>2011. ápr. 18.</b></td><td>Alaptörvény adopted</td></tr>
<tr><td><b>2012. jan. 1.</b></td><td>Alaptörvény enters into force</td></tr>
<tr><td><b>augusztus 20.</b></td><td>National holiday — Saint Stephen's Day</td></tr>
</table>

<h2>Key People — Who Did What</h2>
<table>
<tr><th>Person</th><th>Why they matter</th></tr>
<tr><td><b>Árpád</b></td><td>Led the 7 tribes in the 895–896 Honfoglalás</td></tr>
<tr><td><b>I. (Szent) István</b></td><td>First Christian king of Hungary (1001); founded state; 10 dioceses</td></tr>
<tr><td><b>IV. Béla</b></td><td>"Második honalapító" — rebuilt after Mongol invasion (1241–42)</td></tr>
<tr><td><b>Hunyadi János</b></td><td>Won Battle of Nándorfehérvár (1456); halted Ottoman advance 70 years</td></tr>
<tr><td><b>Hunyadi Mátyás</b></td><td>Renaissance king (1458–1490) — golden age</td></tr>
<tr><td><b>Széchenyi István</b></td><td>"A legnagyobb magyar" — MTA, Lánchíd</td></tr>
<tr><td><b>Kossuth Lajos</b></td><td>Finance minister 1848; voice of the revolution</td></tr>
<tr><td><b>Batthyány Lajos</b></td><td>First PM; martyr — executed Oct 6, 1849</td></tr>
<tr><td><b>Petőfi Sándor</b></td><td>Poet; led March 15, 1848 revolution; wrote Nemzeti dal</td></tr>
<tr><td><b>Deák Ferenc</b></td><td>"A haza bölcse" — architect of the 1867 Kiegyezés</td></tr>
<tr><td><b>Kölcsey Ferenc</b></td><td>Wrote Himnusz (1823); also Romantic poet</td></tr>
<tr><td><b>Erkel Ferenc</b></td><td>Composed Himnusz music; wrote Bánk bán opera</td></tr>
<tr><td><b>Vörösmarty Mihály</b></td><td>Wrote Szózat (1836)</td></tr>
<tr><td><b>Egressy Béni</b></td><td>Composed Szózat music</td></tr>
<tr><td><b>Liszt Ferenc</b></td><td>Magyar rapszódiák; world-famous pianist</td></tr>
<tr><td><b>Bartók Béla</b></td><td>A kékszakállú herceg vára; folk music researcher</td></tr>
<tr><td><b>Kodály Zoltán</b></td><td>Háry János; folk music researcher</td></tr>
<tr><td><b>Nagy Imre</b></td><td>Revolutionary leader in 1956; later executed by Kádár</td></tr>
<tr><td><b>Orbán Viktor</b></td><td>Current Prime Minister</td></tr>
<tr><td><b>Dr. Sulyok Tamás</b></td><td>Current President of the Republic</td></tr>
</table>

<h2>Flag, Anthem, Szózat — Quick Compare</h2>
<table>
<tr><th></th><th>Himnusz</th><th>Szózat</th></tr>
<tr><td>Written by</td><td>Kölcsey Ferenc</td><td>Vörösmarty Mihály</td></tr>
<tr><td>Year</td><td>1823</td><td>1836</td></tr>
<tr><td>Music by</td><td>Erkel Ferenc</td><td>Egressy Béni</td></tr>
</table>

<h2>Hungary's 7 Neighbours</h2>
<p>Going roughly clockwise from the north:<br/>
<b>Szlovákia → Ukrajna → Románia → Szerbia → Horvátország → Szlovénia → Ausztria</b></p>

<h2>Hungarikumok — Quick List</h2>
<p><b>Food/drink:</b> gulyásleves · halászlé · dobostorta · Pick téliszalámi · Tokaji aszú · Egri bikavér · pálinka · kalocsai paprika · makói hagyma</p>
<p><b>Animals:</b> puli · komondor · kuvasz · magyar vizsla · erdélyi kopó · szürke szarvasmarha</p>
<p><b>Folk arts:</b> halasi csipke · matyó népművészet · Zsolnay-porcelán · hollóházi porcelán</p>
<p><b>Cultural:</b> mohácsi busójárás · Hollókő · Pannonhalmi Bencés Főapátság · Füredi Anna-bál</p>
</div>"""
    return xhtml_page("Master Quick-Reference", body)

def build_practice_test(questions: list) -> str:
    import random
    shuffled = list(questions)
    random.seed(42)
    random.shuffle(shuffled)

    items = ""
    for i, q in enumerate(shuffled, 1):
        t_label = f"T{q['topic']}"
        d_label = DIFF_LABEL[q.get("difficulty", 1)]
        items += f"""<div class="pt-q">
<span class="pt-num">{i}.</span> [{t_label} · {d_label}]<br/>
{html_escape(q["question_hu"])}<br/>
<i style="font-size:0.88em">{html_escape(q["question_en"])}</i>
</div>
"""
    body = f"""<div class="chapter">
<h1>Practice Test — All 132 Questions</h1>
<p>Cover the page below each question and answer aloud in Hungarian before reading further.<br/>
Topic and difficulty shown in brackets. Answers are in the next chapter.</p>
<hr/>
{items}
</div>"""
    return xhtml_page("Practice Test", body), shuffled

def build_answer_key(shuffled: list) -> str:
    items = ""
    for i, q in enumerate(shuffled, 1):
        kw = ", ".join(q.get("keywords_hu", []))
        kw_html = f' <span style="font-size:0.85em;color:#666;">(🔑 {html_escape(kw)})</span>' if kw else ""
        items += f"""<p><b>{i}.</b> {html_escape(q["answer_hu"])}{kw_html}</p>
"""
    body = f"""<div class="chapter">
<h1>Answer Key</h1>
<p><i>Answers listed in the same order as the Practice Test.</i></p>
{items}
</div>"""
    return xhtml_page("Answer Key", body)

def build_quick_review() -> str:
    cards = ""
    for t_num, t in TOPICS.items():
        cards += f"""<div class="chapter">
<h1>Quick-Review Card — Topic {t_num}</h1>
<h2>{html_escape(t["hu"])}</h2>
<p><i>{html_escape(t["en"])}</i></p>
"""
        if t_num == 1:
            cards += """<table>
<tr><th>Symbol</th><th>Key Fact</th></tr>
<tr><td>Zászló</td><td>Piros (erő) · Fehér (hűség) · Zöld (remény) — horizontal</td></tr>
<tr><td>Címer</td><td>Left=4+4 stripes (Árpád) · Right=kettős kereszt / hármas halom · Top=Szent Korona</td></tr>
<tr><td>Himnusz</td><td>Kölcsey Ferenc (1823) · Erkel Ferenc (music)</td></tr>
<tr><td>Szózat</td><td>Vörösmarty Mihály (1836) · Egressy Béni (music)</td></tr>
<tr><td>Márc. 15.</td><td>1848 Revolution — kokárda</td></tr>
<tr><td>Aug. 20.</td><td>Saint Stephen's Day — fireworks</td></tr>
<tr><td>Okt. 23.</td><td>1956 Revolution — lyukas zászló</td></tr>
</table>"""
        elif t_num == 2:
            cards += """<table>
<tr><th>Year</th><th>Event · Person</th></tr>
<tr><td>895–896</td><td>Honfoglalás · Árpád</td></tr>
<tr><td>1001</td><td>I. István – first Christian king</td></tr>
<tr><td>1222</td><td>Aranybulla · II. András</td></tr>
<tr><td>1456</td><td>Nándorfehérvár · Hunyadi János</td></tr>
<tr><td>1526</td><td>Mohácsi csata — defeat</td></tr>
<tr><td>1848. márc. 15.</td><td>Revolution · Petőfi, Jókai · PM: Batthyány</td></tr>
<tr><td>1849. okt. 6.</td><td>13 Aradi vértanú</td></tr>
<tr><td>1867</td><td>Kiegyezés · Deák Ferenc</td></tr>
<tr><td>1920</td><td>Trianon — 2/3 territory lost</td></tr>
<tr><td>1956. okt. 23.</td><td>Revolution · Nagy Imre · lyukas zászló</td></tr>
<tr><td>1989–1990</td><td>Rendszerváltás · PM: Antall · Elnök: Göncz</td></tr>
</table>"""
        elif t_num == 3:
            cards += """<table>
<tr><th>Who</th><th>What</th></tr>
<tr><td>Erkel Ferenc</td><td>Himnusz (music) · Bánk bán (opera)</td></tr>
<tr><td>Liszt Ferenc</td><td>Magyar rapszódiák</td></tr>
<tr><td>Bartók Béla</td><td>A kékszakállú herceg vára · folk researcher</td></tr>
<tr><td>Kodály Zoltán</td><td>Háry János · folk researcher</td></tr>
<tr><td>Petőfi Sándor</td><td>Nemzeti dal (Romantika)</td></tr>
<tr><td>Vörösmarty Mihály</td><td>Szózat (Romantika)</td></tr>
<tr><td>Madách Imre</td><td>Az ember tragédiája</td></tr>
<tr><td>Beethoven</td><td>IX. szimfónia = EU Anthem (Schiller 1785)</td></tr>
</table>"""
        elif t_num == 4:
            cards += """<table>
<tr><th>Item</th><th>Key Facts</th></tr>
<tr><td>Alaptörvény</td><td>Adopted 2011. ápr. 18. · In force 2012. jan. 1.</td></tr>
<tr><td>Országgyűlés</td><td>199 képviselő · 4 éves megbízatás</td></tr>
<tr><td>Miniszterelnök</td><td>Orbán Viktor · elected by Parliament</td></tr>
<tr><td>Elnök</td><td>Dr. Sulyok Tamás · 5 év · max 1× újraválasztható · Commander-in-Chief</td></tr>
<tr><td>Kormány</td><td>PM + 13 ministers · 14 ministries</td></tr>
</table>"""
        elif t_num == 5:
            cards += """<table>
<tr><th>Item</th><th>Key Facts</th></tr>
<tr><td>Magna Carta</td><td>1215 · England</td></tr>
<tr><td>Aranybulla</td><td>1222 · Hungary</td></tr>
<tr><td>French Declaration</td><td>1789 · France</td></tr>
<tr><td>ECHR</td><td>1950 · Europe</td></tr>
<tr><td>1st gen rights</td><td>Life · freedom · assembly · religion · speech</td></tr>
<tr><td>2nd gen rights</td><td>Work · strike · education · social security</td></tr>
<tr><td>3rd gen rights</td><td>Health/environment · children · patients · disabled</td></tr>
<tr><td>Halálbüntetés</td><td>Abolished 1990 — Alkotmánybíróság: unconstitutional</td></tr>
</table>"""
        elif t_num == 6:
            cards += """<table>
<tr><th>Item</th><th>Key Facts</th></tr>
<tr><td>Hungary</td><td>93 000 km² · 9,6M · Forint · 19 vármegyék · 7 neighbours</td></tr>
<tr><td>Budapest</td><td>Founded 1873. nov. 17. · 23 kerület (since 1994)</td></tr>
<tr><td>EU joined</td><td>2004. május 1.</td></tr>
<tr><td>Schengen joined</td><td>2007</td></tr>
<tr><td>EU facts</td><td>27 members · 450M people · Brüsszel · 21 Hungarian MEPs</td></tr>
<tr><td>EU anthem</td><td>Beethoven IX. — Örömóda (Schiller 1785)</td></tr>
<tr><td>Drinks</td><td>Tokaji aszú · Egri bikavér · pálinka</td></tr>
<tr><td>Dogs</td><td>puli · komondor · kuvasz · magyar vizsla</td></tr>
</table>"""
        cards += "</div>\n"
    return xhtml_page("Quick-Review Cards", cards)

# ── EPUB assembly ─────────────────────────────────────────────────────────────

def build_epub(questions: list) -> None:
    # Build all pages
    cover_html  = build_cover()
    intro_html  = build_intro()
    topic_pages = {t: build_topic_chapter(t, questions) for t in range(1, 7)}
    ref_html    = build_master_reference()
    pt_result   = build_practice_test(questions)
    pt_html, shuffled = pt_result
    ak_html     = build_answer_key(shuffled)
    qr_html     = build_quick_review()

    # File manifest
    content_files = [
        ("cover.xhtml",   "Cover",                    cover_html),
        ("intro.xhtml",   "Introduction & Exam Tips", intro_html),
        ("topic1.xhtml",  "Topic 1: Symbols & Holidays",          topic_pages[1]),
        ("topic2.xhtml",  "Topic 2: History of Hungary",          topic_pages[2]),
        ("topic3.xhtml",  "Topic 3: Literature and Music",        topic_pages[3]),
        ("topic4.xhtml",  "Topic 4: Constitution & Institutions", topic_pages[4]),
        ("topic5.xhtml",  "Topic 5: Citizens' Rights",            topic_pages[5]),
        ("topic6.xhtml",  "Topic 6: Europe and Everyday Hungary", topic_pages[6]),
        ("reference.xhtml","Master Quick-Reference",              ref_html),
        ("practice.xhtml","Practice Test (132 Questions)",        pt_html),
        ("answers.xhtml", "Answer Key",                           ak_html),
        ("quickreview.xhtml","Quick-Review Cards (6 Topics)",     qr_html),
    ]

    # OPF manifest items
    manifest_items = "\n".join(
        f'    <item id="{fn.replace(".xhtml","")}" href="OEBPS/{fn}" media-type="application/xhtml+xml"/>'
        for fn, _, _ in content_files
    )
    manifest_items += '\n    <item id="css" href="OEBPS/styles.css" media-type="text/css"/>'
    manifest_items += '\n    <item id="ncx" href="OEBPS/toc.ncx" media-type="application/x-dtbncx+xml"/>'

    spine_items = "\n".join(
        f'    <itemref idref="{fn.replace(".xhtml","")}"/>'
        for fn, _, _ in content_files
    )

    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="book-id">urn:uuid:{BOOK_ID}</dc:identifier>
    <dc:title>{BOOK_TITLE}</dc:title>
    <dc:language>{BOOK_LANG}</dc:language>
    <dc:date>{BOOK_DATE}</dc:date>
    <dc:creator>Magyar Kulturális Vizsga Study Tool</dc:creator>
    <dc:subject>Hungarian Language · Cultural Exam · Study Guide</dc:subject>
    <meta name="cover" content="cover"/>
  </metadata>
  <manifest>
{manifest_items}
  </manifest>
  <spine toc="ncx">
{spine_items}
  </spine>
  <guide>
    <reference type="cover"    title="Cover"        href="OEBPS/cover.xhtml"/>
    <reference type="toc"      title="Introduction" href="OEBPS/intro.xhtml"/>
  </guide>
</package>"""

    # NCX navigation
    nav_points = ""
    for i, (fn, title, _) in enumerate(content_files, 1):
        nav_points += f"""  <navPoint id="np{i}" playOrder="{i}">
    <navLabel><text>{html_escape(title)}</text></navLabel>
    <content src="OEBPS/{fn}"/>
  </navPoint>
"""
    ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
  "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:{BOOK_ID}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{BOOK_TITLE}</text></docTitle>
  <navMap>
{nav_points}  </navMap>
</ncx>"""

    container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

    print(f"Building {OUTPUT_FILE} ...")
    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as z:
        # mimetype must be first, uncompressed
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container)
        z.writestr("content.opf", opf)
        z.writestr("OEBPS/toc.ncx", ncx)
        z.writestr("OEBPS/styles.css", CSS)
        for fn, _, html in content_files:
            z.writestr(f"OEBPS/{fn}", html.encode("utf-8"))

    size_kb = OUTPUT_FILE.stat().st_size // 1024
    print(f"Done! {OUTPUT_FILE.name}  ({size_kb} KB)")
    print()
    print("To send to Kindle:")
    print("  1. Email to your Kindle address (Settings > Your Account > Send-to-Kindle Email)")
    print("  2. Or open with the Kindle app on any device")
    print("  3. Or use USB transfer (Documents folder on Kindle)")

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} questions across 6 topics.")
    build_epub(questions)
