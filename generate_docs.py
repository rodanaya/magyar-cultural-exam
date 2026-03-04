import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

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

# Key Hungarian vocabulary per topic: (magyar szó, English gloss)
VOCAB = {
    1: [
        ("zászló / lobogó", "flag"),
        ("sáv", "stripe"),
        ("piros", "red"),
        ("fehér", "white"),
        ("zöld", "green"),
        ("erő", "strength"),
        ("hűség", "loyalty"),
        ("remény", "hope"),
        ("címer", "coat of arms"),
        ("kettős kereszt", "double cross"),
        ("hármas halom", "triple hill"),
        ("Szent Korona", "Holy Crown"),
        ("koronázási jelvények", "coronation insignia"),
        ("jogar", "sceptre"),
        ("országalma", "orb"),
        ("palást", "coronation mantle"),
        ("Himnusz", "national anthem"),
        ("Szózat", "appeal / second anthem"),
        ("nemzeti ünnep", "national holiday"),
        ("forradalom", "revolution"),
        ("szabadságharc", "war of independence"),
        ("kokárda", "rosette / cockade"),
        ("lyukas zászló", "flag with a hole (1956 symbol)"),
    ],
    2: [
        ("honfoglalás", "conquest / settling of the homeland"),
        ("törzs", "tribe"),
        ("fejedelem", "prince / chieftain"),
        ("Kárpát-medence", "Carpathian Basin"),
        ("államalapítás", "foundation of the state"),
        ("koronázás", "coronation"),
        ("király", "king"),
        ("Aranybulla", "Golden Bull (1222)"),
        ("tatárjárás", "Mongol invasion"),
        ("ostrom", "siege"),
        ("török hódoltság", "Ottoman occupation"),
        ("vereség", "defeat"),
        ("győzelem", "victory"),
        ("forradalom", "revolution"),
        ("szabadságharc", "war of independence"),
        ("vértanú", "martyr"),
        ("honvéd", "homeland defender"),
        ("kiegyezés", "Compromise / Ausgleich"),
        ("Monarchia", "Austro-Hungarian Monarchy"),
        ("rendszerváltás", "regime change"),
        ("békediktátum / békeszerződés", "peace treaty / diktat"),
        ("miniszterelnök", "Prime Minister"),
        ("köztársasági elnök", "President of the Republic"),
        ("megtorlás", "retaliation / retribution"),
        ("egypártrendszer", "one-party system"),
        ("újratemetés", "ceremonial reburial"),
    ],
    3: [
        ("népzene", "folk music"),
        ("népdal", "folk song"),
        ("zenész / zeneszerző", "musician / composer"),
        ("opera", "opera"),
        ("szimfónia", "symphony"),
        ("rapszódia", "rhapsody"),
        ("korszak", "era / period"),
        ("reneszánsz", "Renaissance"),
        ("barokk", "Baroque"),
        ("felvilágosodás", "Enlightenment"),
        ("klasszicizmus", "Classicism"),
        ("romantika", "Romanticism"),
        ("költő", "poet"),
        ("író", "writer"),
        ("költemény / vers", "poem"),
        ("regény", "novel"),
        ("dráma", "drama / play"),
        ("eposz", "epic poem"),
        ("nyelvújítás", "language reform"),
        ("népzenekutató", "folk music researcher"),
    ],
    4: [
        ("Alaptörvény", "Fundamental Law / Constitution"),
        ("alkotmány", "constitution"),
        ("jogrend", "legal system"),
        ("Országgyűlés", "National Assembly / Parliament"),
        ("képviselő", "MP / representative"),
        ("megbízatás", "mandate / term of office"),
        ("törvényhozás", "legislation / law-making"),
        ("költségvetés", "budget"),
        ("Kormány", "Government"),
        ("miniszterelnök", "Prime Minister"),
        ("minisztérium", "ministry"),
        ("végrehajtó hatalom", "executive power"),
        ("köztársasági elnök", "President of the Republic"),
        ("államfő", "head of state"),
        ("titkos szavazás", "secret ballot"),
        ("főparancsnok", "Commander-in-Chief"),
        ("feloszlatás", "dissolution (of Parliament)"),
    ],
    5: [
        ("alapjog", "fundamental right"),
        ("állampolgár", "citizen"),
        ("jogegyenlőség", "legal equality"),
        ("szabadság", "freedom / liberty"),
        ("gyülekezési szabadság", "freedom of assembly"),
        ("szólásszabadság / véleménynyilvánítás szabadsága", "freedom of speech / expression"),
        ("lelkiismereti és vallásszabadság", "freedom of conscience and religion"),
        ("sajtószabadság", "freedom of the press"),
        ("emberi méltóság", "human dignity"),
        ("halálbüntetés", "capital punishment"),
        ("Alkotmánybíróság", "Constitutional Court"),
        ("alkotmányellenes", "unconstitutional"),
        ("polgári jog", "civil right"),
        ("szociális jog", "social right"),
        ("kollektív jog", "collective right"),
        ("sérthetetlen", "inviolable"),
        ("elidegeníthetetlen", "inalienable"),
    ],
    6: [
        ("főváros", "capital city"),
        ("vármegye", "county"),
        ("kerület", "district"),
        ("szomszédos ország", "neighbouring country"),
        ("tájegység", "geographical region"),
        ("pénznem", "currency"),
        ("folyó", "river"),
        ("tó", "lake"),
        ("hungarikum", "a uniquely Hungarian thing/tradition"),
        ("felekezet", "religious denomination"),
        ("kereszténység", "Christianity"),
        ("tagállam", "member state"),
        ("csatlakozás", "joining / accession"),
        ("schengeni övezet", "Schengen Area"),
        ("Európai Parlament", "European Parliament"),
        ("képviselő", "MEP / representative"),
        ("alapanyag", "ingredient / raw material"),
        ("nép- és iparművészet", "folk and applied arts"),
    ],
}

# Extra vocabulary to blank in fill-in-the-blank (in addition to keywords_hu)
EXTRA_BLANK = {
    1: ["zászló", "lobogó", "piros", "fehér", "zöld", "erő", "hűség", "remény",
        "címer", "kettős kereszt", "hármas halom", "jogar", "országalma", "palást",
        "Himnusz", "Szózat", "kokárda", "lyukas"],
    2: ["honfoglalás", "törzs", "Kárpát-medence", "Aranybulla", "tatárjárás",
        "kiegyezés", "rendszerváltás", "vértanú", "honvéd", "szabadságharc",
        "forradalom", "Monarchia", "békediktátum", "megtorlás"],
    3: ["népzene", "népdal", "reneszánsz", "barokk", "felvilágosodás",
        "klasszicizmus", "romantika", "nyelvújítás", "szimfónia", "rapszódia"],
    4: ["Alaptörvény", "Országgyűlés", "képviselő", "miniszterelnök",
        "köztársasági elnök", "minisztérium", "titkos szavazás", "főparancsnok"],
    5: ["alapjog", "jogegyenlőség", "halálbüntetés", "Alkotmánybíróság",
        "alkotmányellenes", "sérthetetlen", "elidegeníthetetlen", "gyülekezési"],
    6: ["vármegye", "főváros", "hungarikum", "felekezet", "tagállam",
        "schengeni", "csatlakozás"],
}

# ─────────────────────────────────────────
# HELPER: vocab box for a topic
# ─────────────────────────────────────────
def vocab_box(t):
    lines = []
    lines.append(f"### Kulcsszavak — Téma {t}\n\n")
    lines.append("| Magyar kifejezés | Jelentés (angolul) |\n")
    lines.append("|-----------------|-------------------|\n")
    for hu, en in VOCAB[t]:
        lines.append(f"| **{hu}** | {en} |\n")
    lines.append("\n")
    return "".join(lines)

# ─────────────────────────────────────────
# 1. FLASHCARDS
# ─────────────────────────────────────────
# Format: vocabulary glossary per topic, then cut-able Q|A table
lines = []
lines.append("# Flashcards — Magyar Kulturális Ismereti Vizsga\n\n")
lines.append("> **A vizsga magyarul van! Tanuld meg a magyar kifejezéseket!**\n")
lines.append("> Nyomtasd ki · Vágd szét a sorok mentén · Hajtsd félbe a vonal mentén: bal = kérdés, jobb = válasz\n\n")
lines.append("---\n\n")

for t in sorted(by_topic):
    lines.append(f"## Téma {t} · {TOPIC_NAMES[t]}\n\n")
    # Vocab glossary first
    lines.append(vocab_box(t))
    lines.append("### Kérdés-Válasz kártyák\n\n")
    lines.append("| # | ✏️ KÉRDÉS (hajtsd ide) | ✅ VÁLASZ (hajtsd el) |\n")
    lines.append("|---|----------------------|---------------------|\n")
    for i, q in enumerate(by_topic[t], 1):
        qtext = q['question_hu'].replace('\n', ' ').replace('|', '/')
        atext = q['answer_hu'].replace('\n', ' ').replace('|', '/')
        lines.append(f"| {i} | {qtext} | {atext} |\n")
    lines.append("\n---\n\n")

with open('flashcards.md', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("flashcards.md done")

# ─────────────────────────────────────────
# 2. PRACTICE TEST
# ─────────────────────────────────────────
practice = {
    1: [by_topic[1][0], by_topic[1][7]],
    2: [by_topic[2][2], by_topic[2][9]],
    3: [by_topic[3][3], by_topic[3][12]],
    4: [by_topic[4][0], by_topic[4][2]],
    5: [by_topic[5][0], by_topic[5][3]],
    6: [by_topic[6][0], by_topic[6][5]],
}
pts_schedule = [3, 2, 3, 2, 2, 3, 3, 2, 3, 2, 2, 3]

# Hints: key Hungarian words the answer should contain
HINTS = {
    1: [
        ["piros", "fehér", "zöld", "vízszintes sávok"],
        ["március 15.", "augusztus 20.", "október 23.", "forradalom", "szabadságharc", "államalapítás"],
    ],
    2: [
        ["Szent István", "1001. január 1.", "keresztény", "király", "koronázás"],
        ["forradalom", "1848. március 15.", "Pilvax", "12 pont", "Petőfi Sándor"],
    ],
    3: [
        ["Zrínyi Miklós", "Szigeti veszedelem", "barokk"],
        ["Petőfi Sándor", "Nemzeti dal", "romantika"],
    ],
    4: [
        ["Alaptörvény", "alkotmány", "2012. január 1.", "jogrend"],
        ["Országgyűlés", "199 képviselő", "4 év", "törvényhozás"],
    ],
    5: [
        ["első generáció", "élethez való jog", "szólásszabadság", "vallásszabadság", "gyülekezési szabadság"],
        ["törvény előtti egyenlőség", "emberi méltóság", "véleménynyilvánítás", "gyülekezési szabadság"],
    ],
    6: [
        ["Budapest", "Duna", "1873", "Pest", "Buda", "Óbuda"],
        ["2004. május 1.", "Európai Unió", "csatlakozás"],
    ],
}

lines = []
lines.append("# Mintavizsga — Magyar Kulturális Ismereti Vizsga\n\n")
lines.append("> **A vizsga magyarul van! Írj magyarul!**\n")
lines.append("> 12 kérdés · 6 témakör · 2 kérdés/témakör · 30 pont · Átmenő: 16 pont\n\n")
lines.append("**Dátum:** _________________________  **Pontszám:** _____ / 30\n\n")
lines.append("---\n\n")

q_num = 0
for t in sorted(practice):
    lines.append(f"## Témakör {t} · {TOPIC_NAMES[t]}\n\n")
    for qi, q in enumerate(practice[t]):
        pts = pts_schedule[q_num]
        q_num += 1
        hints = HINTS[t][qi]
        lines.append(f"**{q_num}.** ({pts} pont)\n\n")
        lines.append(f"**{q['question_hu']}**\n\n")
        lines.append(f"> 💡 *Kulcsszavak a válaszhoz: {' · '.join(hints)}*\n\n")
        lines.append("_" * 72 + "\n\n")
        lines.append("_" * 72 + "\n\n")

lines.append("---\n\n")
lines.append("## Megoldókulcs\n\n")
q_num = 0
for t in sorted(practice):
    lines.append(f"**Témakör {t} · {TOPIC_NAMES[t]}**\n\n")
    for q in practice[t]:
        q_num += 1
        lines.append(f"**{q_num}.** {q['answer_hu']}\n\n")
    lines.append("\n")

with open('practice-test.md', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("practice-test.md done")

# ─────────────────────────────────────────
# 3. FILL-IN-THE-BLANK
# ─────────────────────────────────────────
def cloze(answer, keywords, extra):
    result = answer
    # Combine and deduplicate, longer phrases first to avoid partial replacements
    all_kw = sorted(set(keywords + extra), key=lambda x: -len(x))
    for kw in all_kw:
        if kw and kw.lower() in result.lower():
            idx = result.lower().find(kw.lower())
            blank = "_" * max(len(kw), 6)
            result = result[:idx] + blank + result[idx + len(kw):]
    return result

lines = []
lines.append("# Hiánypótló Feladatok — Magyar Kulturális Ismereti Vizsga\n\n")
lines.append("> **A vizsga magyarul van — gyakorold a magyar szavakat!**\n")
lines.append("> Töltsd ki a hiányzó magyar kifejezéseket! Megoldókulcs a lap alján.\n\n")
lines.append("---\n\n")

all_cloze = []
for t in sorted(by_topic):
    lines.append(f"## Témakör {t} · {TOPIC_NAMES[t]}\n\n")
    # Show vocab reminder for this topic
    lines.append("> **Emlékeztető szavak:** ")
    vocab_str = " · ".join(f"**{hu}**" for hu, en in VOCAB[t])
    lines.append(vocab_str + "\n\n")
    q_num = 0
    extra = EXTRA_BLANK.get(t, [])
    for q in by_topic[t]:
        keywords = q.get('keywords_hu', [])
        clozed = cloze(q['answer_hu'], keywords, extra)
        if clozed == q['answer_hu']:
            continue
        q_num += 1
        lines.append(f"**{q_num}.** _{q['question_hu']}_\n\n")
        lines.append(f"{clozed}\n\n")
        all_cloze.append((t, q_num, q['answer_hu']))
    lines.append("\n")

lines.append("---\n\n")
lines.append("## Megoldókulcs\n\n")
for (t, n, ans) in all_cloze:
    lines.append(f"**T{t}-{n}.** {ans}\n\n")

with open('fill-in-the-blank.md', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("fill-in-the-blank.md done")

# ─────────────────────────────────────────
# 4. CHEAT SHEETS — Hungarian-first, vocab box on every page
# ─────────────────────────────────────────
cheatsheets = {}

cheatsheets[1] = """\
## Téma 1 · Nemzeti Jelképek és Ünnepek

| Magyar kifejezés | Jelentés |
|-----------------|----------|
| **zászló / lobogó** | flag | **sáv** | stripe |
| **erő** | strength | **hűség** | loyalty | **remény** | hope |
| **címer** | coat of arms | **kettős kereszt** | double cross |
| **hármas halom** | triple hill | **jogar** | sceptre |
| **országalma** | orb | **palást** | mantle |
| **Himnusz** | national anthem | **Szózat** | appeal |
| **kokárda** | cockade/rosette | **lyukas zászló** | flag with hole |
| **nemzeti ünnep** | national holiday | **forradalom** | revolution |
| **szabadságharc** | war of independence | **államalapítás** | foundation of state |

### Nemzeti jelképek
| Jelkép | Részletek |
|--------|-----------|
| **Zászló** | Piros (erő) · Fehér (hűség) · Zöld (remény) — vízszintes sávok |
| **Címer** | Bal: 4 ezüst + 4 piros sáv (Árpádok) · Jobb: kettős kereszt hármas halmon · Tetején: Szent Korona |
| **Szent Korona** | Az Országházban látható · az alkotmányos folytonosság jelképe |
| **Koronázási jelvények** | Korona · Jogar · Országalma · Kard · Palást |
| **Koronázó városok** | Buda · Esztergom · Pozsony · Sopron · Székesfehérvár |

### Himnusz és Szózat
| | Himnusz | Szózat |
|--|---------|--------|
| **Szerző** | Kölcsey Ferenc | Vörösmarty Mihály |
| **Év** | 1823 | 1836 |
| **Zene** | Erkel Ferenc | Egressy Béni |

### Nemzeti ünnepek
| Dátum | Esemény |
|-------|---------|
| **Március 15.** | az 1848–49-es forradalom és szabadságharc emlékére |
| **Augusztus 20.** | az államalapítás és Szent István király emlékére |
| **Október 23.** | az 1956. évi forradalom és szabadságharc emlékére |
"""

cheatsheets[2] = """\
## Téma 2 · Magyarország Történelme

| Magyar kifejezés | Jelentés |
|-----------------|----------|
| **honfoglalás** | conquest of homeland | **törzs** | tribe |
| **Kárpát-medence** | Carpathian Basin | **fejedelem** | chieftain/prince |
| **államalapítás** | foundation of state | **koronázás** | coronation |
| **Aranybulla** | Golden Bull | **tatárjárás** | Mongol invasion |
| **ostrom** | siege | **török hódoltság** | Ottoman occupation |
| **forradalom** | revolution | **szabadságharc** | war of independence |
| **vértanú** | martyr | **honvéd** | homeland defender |
| **kiegyezés** | Compromise/Ausgleich | **Monarchia** | Austro-Hungarian Monarchy |
| **békediktátum** | peace diktat | **rendszerváltás** | regime change |
| **megtorlás** | retaliation | **egypártrendszer** | one-party system |

### Történelmi időrend
| Év | Esemény |
|----|---------|
| **895–896** | Honfoglalás — Árpád vezette 7 törzs a Kárpát-medencébe |
| **1001. jan. 1.** | I. Szent István megkoronázása — első keresztény király |
| **1222** | Aranybulla — II. András (nemesek jogai) |
| **1241–42** | Tatárjárás · IV. Béla „második honalapító" újjáépíti az országot |
| **1456** | Nándorfehérvári csata — Hunyadi János (70 év haladék a törököknek) |
| **1458–1490** | Hunyadi Mátyás — reneszánsz fénykor |
| **1526. aug. 29.** | Mohácsi csata — vereség az oszmánoktól |
| **1541** | Törökök elfoglalják Budát — ország 3 részre szakad (~150 év) |
| **1686. szept. 2.** | Habsburgok visszafoglalják Budát |
| **1703–1711** | II. Rákóczi Ferenc szabadságharca |
| **1848. márc. 15.** | Forradalom — Pilvax · 12 pont · Petőfi, Jókai, Vasvári |
| **1848. ápr. 11.** | Első felelős kormány — miniszterelnök: Batthyány Lajos |
| **1849. aug. 13.** | Görgei megadja magát Világosnál |
| **1849. okt. 6.** | 13 aradi vértanú + Batthyány kivégzése |
| **1867** | Kiegyezés — Deák Ferenc · Osztrák–Magyar Monarchia |
| **1914. jún. 28.** | Ferenc Ferdinánd meggyilkolása Szarajevóban |
| **1920. jún. 4.** | Trianoni békeszerződés — 2/3 terület elveszítve; 3,3M magyar külföldön |
| **1944. márc. 19.** | Németek megszállják Magyarországot · holokauszt: ~500–600 ezer áldozat |
| **1956. okt. 23.** | Forradalom — Nagy Imre · Corvin köz · lyukas zászló |
| **1956. nov. 4.** | Szovjet csapatok leverik · Kádár János vezető |
| **1989. jún. 16.** | Nagy Imre ünnepélyes újratemetése |
| **1990** | Szabad választások — miniszterelnök: Antall József · elnök: Göncz Árpád |
| **1991** | Szovjet csapatok végleg elhagyják Magyarországot |
"""

cheatsheets[3] = """\
## Téma 3 · Irodalom és Zenetörténet

| Magyar kifejezés | Jelentés |
|-----------------|----------|
| **népzene** | folk music | **népdal** | folk song |
| **zenész / zeneszerző** | musician / composer | **opera** | opera |
| **szimfónia** | symphony | **rapszódia** | rhapsody |
| **korszak** | era/period | **reneszánsz** | Renaissance |
| **barokk** | Baroque | **felvilágosodás** | Enlightenment |
| **klasszicizmus** | Classicism | **romantika** | Romanticism |
| **költő** | poet | **író** | writer |
| **költemény / vers** | poem | **regény** | novel |
| **dráma** | drama/play | **eposz** | epic poem |
| **nyelvújítás** | language reform | **népzenekutató** | folk music researcher |

### Magyar zene
| Zenész | Mű |
|--------|----|
| Erkel Ferenc | Himnusz (zenéje) · Bánk bán (opera) |
| Liszt Ferenc | Magyar rapszódiák |
| Bartók Béla | A kékszakállú herceg vára · népzenekutató |
| Kodály Zoltán | Háry János · népzenekutató |

### Magyar irodalom korszakonként
| Korszak | Szerző | Mű |
|---------|--------|-----|
| **Reneszánsz** | Janus Pannonius | Pannónia dicsérete |
| | Balassi Bálint | Hogy Júliára talála… |
| **Barokk** | Zrínyi Miklós | Szigeti veszedelem |
| **Felvilágosodás** | Csokonai Vitéz Mihály | A reményhez |
| | Batsányi János | A franciaországi változásokra |
| **Klasszicizmus** | Kazinczy Ferenc | (nyelvújítás vezéralakja) |
| | Berzsenyi Dániel | Az első szerelem |
| **Romantika** | Kölcsey Ferenc | Himnusz |
| | Vörösmarty Mihály | Szózat |
| | Petőfi Sándor | Nemzeti dal |
| | Jókai Mór | A kőszívű ember fiai |
| | Arany János | A walesi bárdok |
| | Katona József | Bánk bán |
| | Madách Imre | Az ember tragédiája |
| **XX. század** | Ady Endre | Elbocsátó, szép üzenet |
| | Móricz Zsigmond | Rokonok |
| | Kosztolányi Dezső | Édes Anna |
| | Karinthy Frigyes | Így írtok ti |
| | József Attila | Tiszta szívvel |
| | Radnóti Miklós | Nem tudhatom… |
| | Márai Sándor | Egy polgár vallomása |

### Európai irodalom és zene
| Alkotó | Mű |
|--------|----|
| William Shakespeare | Rómeó és Júlia |
| Voltaire | Candide |
| J. W. von Goethe | Faust |
| Beethoven | IX. szimfónia — **EU himnusz** (Örömóda · Schiller 1785 · bemutató: 1824) |
| Mozart | A varázsfuvola |
| Csajkovszkij | A hattyúk tava |
"""

cheatsheets[4] = """\
## Téma 4 · Az Alaptörvény Alapvető Intézményei

| Magyar kifejezés | Jelentés |
|-----------------|----------|
| **Alaptörvény** | Fundamental Law / Constitution |
| **alkotmány** | constitution | **jogrend** | legal system |
| **Országgyűlés** | National Assembly / Parliament |
| **képviselő** | MP / representative | **megbízatás** | term of office |
| **törvényhozás** | legislation | **költségvetés** | budget |
| **Kormány** | Government | **miniszterelnök** | Prime Minister |
| **minisztérium** | ministry | **végrehajtó hatalom** | executive power |
| **köztársasági elnök** | President of the Republic | **államfő** | head of state |
| **titkos szavazás** | secret ballot | **főparancsnok** | Commander-in-Chief |
| **feloszlatás** | dissolution (of Parliament) |

### Az Alaptörvény
- Elfogadva: **2011. április 18.** · Hatályba lépett: **2012. január 1.**
- Magyarország alkotmánya — a jogrend alapja, legmagasabb jogi erővel bír

### Az Országgyűlés
| Adat | Érték |
|------|-------|
| Szerep | Magyarország legfőbb népképviseleti szerve |
| Képviselők száma | **199 fő** |
| Megbízatás | **4 év** |
| Főbb feladatok | Alaptörvény megalkotása/módosítása · törvényhozás · költségvetés elfogadása · miniszterelnök megválasztása |

### A Kormány
| Adat | Érték |
|------|-------|
| Miniszterelnök | **Orbán Viktor** |
| Megválasztja | Az Országgyűlés |
| Főbb feladatok | Közigazgatás irányítása · jogszabályalkotás · állami ellátórendszerek működtetése |
| EU-képviselet | A miniszterelnök képviseli Magyarországot az Európai Tanácsban |

**14 minisztérium:** Agrár · Belügy · Energiaügy · Építési és Közlekedési · EU-ügyek · Honvédelmi · Igazságügyi · Közigazgatási és Területfejlesztési · Kulturális és Innovációs · Külgazdasági és Külügy · Miniszterelnöki Kabinetiroda · Miniszterelnökség · Nemzetgazdasági

### A Köztársasági Elnök
| Adat | Érték |
|------|-------|
| Jelenlegi elnök | **Dr. Sulyok Tamás** |
| Megválasztja | Az Országgyűlés — titkos szavazással |
| Megbízatás | **5 év** · legfeljebb 1× újraválasztható |
| Jogkörök | Honvédség főparancsnoka · összehívja az alakuló ülést · feloszlathatja az Országgyűlést |
"""

cheatsheets[5] = """\
## Téma 5 · Állampolgári Jogok és Kötelezettségek

| Magyar kifejezés | Jelentés |
|-----------------|----------|
| **alapjog** | fundamental right | **állampolgár** | citizen |
| **jogegyenlőség** | legal equality | **szabadság** | freedom/liberty |
| **gyülekezési szabadság** | freedom of assembly |
| **szólásszabadság** | freedom of speech |
| **sajtószabadság** | freedom of the press |
| **lelkiismereti és vallásszabadság** | freedom of conscience and religion |
| **emberi méltóság** | human dignity |
| **halálbüntetés** | capital punishment |
| **Alkotmánybíróság** | Constitutional Court |
| **alkotmányellenes** | unconstitutional |
| **sérthetetlen** | inviolable | **elidegeníthetetlen** | inalienable |

### Az emberi jogok fejlődése
| Dokumentum | Év | Ország |
|------------|----|--------|
| Magna Carta Libertatum | 1215 | Anglia |
| Aranybulla | 1222 | Magyarország |
| Emberi és Polgári Jogok Nyilatkozata | 1789 | Franciaország |
| Emberi Jogok Európai Egyezménye | 1950 | Európa |

### Az alapjogok három generációja
| Generáció | Tartalom |
|-----------|----------|
| **1. generáció** (polgári és politikai jogok) | élethez való jog · személyi szabadság · egyesülési és gyülekezési szabadság · lelkiismereti és vallásszabadság · szólás- és sajtószabadság |
| **2. generáció** (szociális és gazdasági jogok) | munkához való jog · sztrájkhoz való jog · oktatáshoz való jog · szociális biztonsághoz való jog |
| **3. generáció** (kollektív jogok) | egészséghez és környezethez való jog · gyermekek jogai · betegjogok · fogyatékkal élők jogai |

### Az Alaptörvényben biztosított alapjogok
- Törvény előtti egyenlőség
- Élethez és emberi méltósághoz való jog
- Tisztességes eljáráshoz való jog
- Gondolat, lelkiismeret és vallásszabadság
- Véleménynyilvánítás szabadsága
- Gyülekezési szabadság
- Tulajdonjog és örökléshez való jog
- Személyes adatok védelméhez való jog

> **Halálbüntetés:** 1990-ben törölték el — az Alkotmánybíróság alkotmányellenesnek nyilvánította
> **Alapelv:** Alapvető jogot korlátozni csak másik alapvető jog vagy alkotmányos érték védelme érdekében lehet.
"""

cheatsheets[6] = """\
## Téma 6 · Európa és Magyarország a Mindennapokban

| Magyar kifejezés | Jelentés |
|-----------------|----------|
| **főváros** | capital city | **vármegye** | county |
| **kerület** | district | **szomszédos ország** | neighbouring country |
| **tájegység** | geographical region | **pénznem** | currency |
| **hungarikum** | uniquely Hungarian thing |
| **felekezet** | religious denomination | **kereszténység** | Christianity |
| **tagállam** | member state | **csatlakozás** | accession/joining |
| **schengeni övezet** | Schengen Area |
| **Európai Parlament** | European Parliament |
| **nép- és iparművészet** | folk and applied arts |

### Magyarország alapadatai
| Adat | Érték |
|------|-------|
| Államforma | Köztársaság |
| Terület | 93 000 km² |
| Népesség | 9,6 millió fő |
| Főváros | Budapest |
| Pénznem | Forint |
| Hivatalos nyelv | Magyar |
| Vármegyék száma | 19 |
| Szomszédos országok | Szlovákia · Ukrajna · Románia · Szerbia · Horvátország · Szlovénia · Ausztria |
| Legnagyobb tavak | Balaton · Fertő tó · Velencei-tó |
| Legnagyobb folyók | Duna · Tisza · Dráva · Rába |
| Tájegységek | Alföld · Alpokalja · Dunántúli-dombság · Dunántúl-középhegység · Északi-középhegység · Kisalföld |

### Budapest
- Alapítva: **1873. november 17.** (Pest + Buda + Óbuda egyesítése)
- **23 kerület** (1994 óta)
- Főbb nevezetességek: Budavári Palota · Citadella · Gellért Gyógyfürdő · Halászbástya · Hősök tere · Magyar Nemzeti Múzeum · Magyar Zene Háza · Magyar Állami Operaház · Mátyás-templom · Parlament · Szent István Bazilika · Széchenyi Lánchíd · Szépművészeti Múzeum · Vajdahunyad vára

### Hungarikumok
| Kategória | Példák |
|-----------|--------|
| Ételek | gulyásleves · halászlé (bajai/tiszai) · dobostorta · Pick téliszalámi |
| Alapanyagok | makói hagyma · kalocsai/szegedi fűszerpaprika |
| Italok | Tokaji aszú · Egri bikavér · pálinka |
| Kulturális | mohácsi busójárás · Pannonhalmi Bencés Főapátság · Hollókő · Füredi Anna-bál |
| Állatok | szürke szarvasmarha · puli · komondor · kuvasz · magyar vizsla · erdélyi kopó |
| Nép- és iparművészet | halasi csipke · matyó népművészet · hollóházi porcelán · Zsolnay-porcelán |

### Kereszténység Magyarországon
- Felekezetek: **Katolikus** (latin és görög) · **Református** · **Evangélikus**
- Ünnepek: Karácsony (dec. 24–26.) · Húsvét · Augusztus 20. (Szent Jobb Körmenet + tűzijáték)
- Magyar szentek: **István · László · Imre · Gellért · Árpád-házi Margit · Árpád-házi Erzsébet**

### Magyarország és az Európai Unió
| Adat | Érték |
|------|-------|
| EU-csatlakozás | **2004. május 1.** |
| Schengen-csatlakozás | **2007** |
| EU polgárainak száma | 450 millió |
| EU székhelye | Brüsszel |
| EU intézményei | Európai Bizottság · Tanács · Európai Parlament · Európai Tanács |
| EU-választások | Ötévente |
| Magyar EP-képviselők | **21 fő** |
| EU zászló | Kék · 12 sárga csillag körben |
| EU himnusz | Beethoven IX. szimfónia — Örömóda (Schiller, 1785) |

### Az EU 27 tagállama
Ausztria · Belgium · Bulgária · Ciprus · Csehország · Dánia · Észtország · Finnország · Franciaország · Görögország · Hollandia · Horvátország · Írország · Lengyelország · Lettország · Litvánia · Luxemburg · **Magyarország** · Málta · Németország · Olaszország · Portugália · Románia · Spanyolország · Svédország · Szlovákia · Szlovénia
"""

lines = []
lines.append("# Gyors Összefoglalók — Magyar Kulturális Ismereti Vizsga\n\n")
lines.append("> **A vizsga magyarul van! Minden oldal elején megtalálod a legfontosabb magyar szavakat.**\n")
lines.append("> Nyomtasd ki mind a hat lapot — egy-egy témakör minden oldalon!\n\n")
lines.append("---\n\n")
for t in sorted(cheatsheets):
    lines.append(cheatsheets[t])
    lines.append("\n---\n\n")

with open('cheat-sheets.md', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("cheat-sheets.md done")

print("\nAll files created:")
for fn in ['flashcards.md', 'practice-test.md', 'fill-in-the-blank.md', 'cheat-sheets.md']:
    size = os.path.getsize(fn)
    print(f"  {fn} — {size:,} bytes")
