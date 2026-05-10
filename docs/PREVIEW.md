# Preview — jak pipeline funguje, krok za krokem

> Tento dokument ukazuje, **jak kód zpracovává jeden inzerát**, od surového
> textu až po detekci kompetencí. Není potřeba nic spouštět — všechny mezi-
> výstupy jsou zde uvedeny.

Pro názornost používáme **fiktivní inzerát** sestavený z typických formulací,
aby nedocházelo k reprodukci skutečného obsahu z Jobs.cz.

---

## Vstup — surový inzerát

Tak vypadá inzerát po stažení Scrapy spiderem (modul `jobs_cz`):

```json
{
  "id": "2099999999",
  "title": "Účetní/Účetní s perspektivou seniorské pozice",
  "provider": "Příklad s.r.o.",
  "location": "Praha – Nové Město",
  "url": "https://www.jobs.cz/rpd/2099999999/",
  "category": "Administrativa",
  "description_text": "Hledáme novou kolegyni nebo kolegu na pozici účetní.\n\nCo budete dělat:\n- vedení účetnictví menších a středních firem\n- zpracování DPH a daňových přiznání\n- komunikace s klienty a finančním úřadem\n\nKoho hledáme:\n- pečlivého a samostatného člověka\n- praxe v účetnictví výhodou\n- znalost MS Office, Pohoda nebo Money S3\n- ochota se dále vzdělávat\n\nCo nabízíme:\n- 5 týdnů dovolené\n- stravenky\n- flexibilní pracovní dobu\n- přátelský kolektiv"
}
```

## Krok 1 — Cleanup (`modules/cleanup/`)

Cleanup modul provádí:

- **Filtraci povinných polí** — inzeráty bez `id`, `title` nebo `url` jsou vyřazeny
- **Filtraci krátkých popisů** — pod 50 znaků (často placeholder data)
- **Deduplikaci** — primárně podle `id`, sekundárně podle kombinace `title` + dalších polí
- **Vyčištění HTML** — přes `w3lib.html.remove_tags`
- **Odstranění popisu zaměstnavatele** — pole `description_html` se ze záznamu zahodí

V našem případě inzerát projde beze změn (struktura je validní).

**Po cleanup zůstávají jen tato pole:**

```json
{
  "id": "2099999999",
  "title": "Účetní/Účetní s perspektivou seniorské pozice",
  "provider": "Příklad s.r.o.",
  "location": "Praha – Nové Město",
  "url": "https://www.jobs.cz/rpd/2099999999/",
  "description_text": "Hledáme novou kolegyni...",
  "category": "Administrativa"
}
```

## Krok 2 — NLP (`modules/nlp/`)

NLP modul aplikuje na pole `description_text` čtyřkrokový pipeline:

```
Lowercase  →  Tokenizace  →  Odstranění stop-slov  →  Lemmatizace
```

### 2.1 Lowercase + tokenizace

```
"Hledáme novou kolegyni..." → ["hledáme", "novou", "kolegyni", "nebo", "kolegu", ...]
```

Tokenizace pomocí regexu `[^\w']+` — rozdělí text na jakémkoli znaku, který
není písmeno nebo apostrof.

### 2.2 Odstranění stop-slov

Modul má vlastní seznam **českých** (cca 130 slov) a **anglických** (cca 130
slov) stop-slov. Tato slova jsou z tokenů odstraněna:

| Před | Po |
|---|---|
| `["hledáme", "novou", "kolegyni", "nebo", "kolegu", "na", "pozici"]` | `["hledáme", "novou", "kolegyni", "kolegu", "pozici"]` |

(Slova `nebo`, `na` jsou stop-words a vypadnou.)

### 2.3 Lemmatizace přes `simplemma`

Každé slovo je převedeno na svůj základní tvar:

| Tokenizovaný tvar | Lemmatizovaný tvar |
|---|---|
| `účetní` | `účetní` |
| `vedení` | `vedení` |
| `účetnictví` | `účetnictví` |
| `středních` | `střední` |
| `daňových` | `daňový` |
| `přiznání` | `přiznání` |
| `pečlivého` | `pečlivý` |
| `samostatného` | `samostatný` |
| `vzdělávat` | `vzdělávat` |

**Výstup po NLP** (pole `description_tokens`):

```
"hledáme novou kolegyně kolegu pozice účetní vedení účetnictví menší střední
firma zpracování dph daňový přiznání komunikace klient finanční úřad pečlivý
samostatný člověk praxe účetnictví výhoda znalost ms office pohoda money s3
ochota dále vzdělávat ..."
```

## Krok 3 — Detekce kompetencí (`modules/tfidf/analyzer.py`)

Toto je jádro analýzy. Detekce probíhá ve dvou režimech:

### Režim `target_sections_only` (hlavní)

1. Modul `sections.py` rozezná v textu **hlavičky sekcí** (regex):
   - `Co budete dělat` → `responsibilities`
   - `Koho hledáme` → `requirements`
   - `Co nabízíme` → `benefits`
2. Detekce se aplikuje **jen na sekce** `requirements` a `responsibilities`.
   Sekce `benefits` (kde se objevují slova jako „flexibilní" — což by jinak
   spadlo pod kompetenci *Flexibilita*) je vyloučena.

### Režim `all_text` (pro kontrolu)

Detekce na celém textu — používá se v Tabulce 6 práce pro porovnání míry
inflace prevalence způsobené benefit/company-pitch sekcemi.

### Detekční mechanismus — kompetence „Celoživotní vzdělávání"

V konfiguraci [`config/tfidf.yaml`](../config/tfidf.yaml) je tato kompetence
definována takto:

```yaml
celozivotni_vzdelavani:
  label: "Celoživotní vzdělávání"
  group: "Osobnostní"
  token_keywords:                  # → matchují se proti tokenům po NLP
    - "učení"
    - "kurz"
    - "mentoring"
    - "školení"
  phrase_patterns:                 # → matchují se proti původnímu textu
    - "ochota se vzdělávat"
    - "chuť učit se"
    - "profesní rozvoj"
    - "průběžné vzdělávání"
    - "ochota učit se"
    - "sebevzdělávání"
    - ... (celkem 10 frází)
```

V našem inzerátu sekce `requirements` obsahuje frázi **„ochota se dále vzdělávat"**.
Po lemmatizaci se z `vzdělávat` stane lemma `vzdělávat`, takže:

- **Token match:** žádné z token-keywords (`učení`, `kurz`, `mentoring`, `školení`)
  v této sekci není.
- **Phrase match:** fráze „ochota se vzdělávat" odpovídá patternu
  `"ochota se vzdělávat"` ✅

→ Kompetence **Celoživotní vzdělávání** je **detekována**.

### Co bude detekováno v našem příkladu

| Kompetence | Token match | Phrase match | Detekce |
|---|---|---|---|
| Celoživotní vzdělávání | — | „ochota se ... vzdělávat" | ✅ |
| Efektivní komunikace | „komunikace" | — | ✅ |
| Orientace na zákazníka | „klient" | — | ✅ |
| Samostatnost | „samostatný" | — | ✅ |
| Flexibilita | — | (jen v sekci `benefits` — ignorováno) | ❌ |

**Pokud by detekce běžela v režimu `all_text`**, byla by detekována i
*Flexibilita* (slovo „flexibilní" v sekci „Co nabízíme"). Tento rozdíl
ilustruje, proč práce používá `target_sections_only` jako hlavní režim —
viz Tabulka 6 v práci a Příloha F.

## Krok 4 — Agregace a výstupy

Po zpracování všech 1 046 inzerátů se výsledky agregují. V `competency_report.json`
najdete pro každou kompetenci:

```json
"celozivotni_vzdelavani": {
  "label": "Celoživotní vzdělávání",
  "count": 124,                      // počet inzerátů, kde detekována
  "prevalence_pct": 12.0,             // 124 / 1046 × 100
  "matched_indicators": {             // které indikátory zafungovaly
    "tokens": {"školení": 67, "kurz": 23, ...},
    "phrases": {"profesní rozvoj": 41, "ochota se vzdělávat": 18, ...}
  }
}
```

A vizualizace:

| Soubor | Co ukazuje |
|---|---|
| `competency_dashboard.html` | Interaktivní dashboard se všemi výsledky |
| `competency_prevalence.png` | Bar chart prevalence 18 kompetencí |
| `top_terms_tfidf.png` | Top 50 termínů podle TF-IDF skóre |
| `subgroup_top_terms.png` | Porovnání Praha vs. regiony |

## Shrnutí — proč hybridní přístup

Práce používá **dvojitý mechanismus** (token + phrase) z těchto důvodů:

- **Tokenový matching** je robustní vůči tvaroslovným variacím („komunikační",
  „komunikace", „komunikovat" → po lemmatizaci stejný základ).
- **Phrase matching** zachytí víceslovné indikátory, které by tokenizace rozbila
  (např. „práce pod tlakem" → po tokenizaci `["práce", "tlak"]` ztratí smysl).
- **Sekční filtrace** snižuje false positives z benefit/company-pitch sekcí.

Detaily v kapitole 2.4 tištěné práce.
