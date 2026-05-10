# Soft Skills v českých administrativních inzerátech — NLP analýza

[![Licence: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

Doprovodné repository k bakalářské práci **„Aktuální požadavky na měkké
dovednosti u administrativních pozic v ČR: Analýza pracovních inzerátů
metodami NLP"** (VŠE Praha, 2026).

> **Pro oponenta a komisi** — pro přečtení a posouzení této práce **není
> potřeba nic spouštět**. Všechny výsledky, grafy a interaktivní dashboard
> jsou již předgenerovány ve složce [`output/tfidf_analysis/`](output/tfidf_analysis/).
> Pro rychlou orientaci v repozitáři čtěte [`docs/PREVIEW.md`](docs/PREVIEW.md).

---

## O čem je tato práce

Práce identifikuje, jaké měkké kompetence skutečně poptávají čeští
zaměstnavatelé u administrativních pozic, a porovnává tyto požadavky se
třemi normativními rámci: českým CDK/NSP, americkým O\*NET a evropským
ESCO.

Datový základ: **1 046 inzerátů z portálu Jobs.cz**, sběr 8. 3. 2026,
kategorie *Administrativa*. Detekce 18 měkkých kompetencí provedena
hybridní metodou kombinující TF-IDF (scikit-learn) s rule-based matchingem
208 indikátorů na lemmatizovaném textu.

## Hlavní zjištění (zkráceně)

- **Komunikace, kooperace a samostatnost** dominují napříč všemi
  administrativními pozicemi (>34 % inzerátů), bez ohledu na to, co
  předepisují normativní rámce.
- **Pražské vs. regionální inzeráty** vykazují podobnou strukturu poptávky;
  nejvýraznější rozdíl je terminologický: Praha „klient", regiony „zákazník".
- U **účetních pozic** se v inzerátech systematicky objevují interpersonální
  kompetence (komunikace 46,9 %), ačkoli žádný ze tří analyzovaných
  normativních rámců je u této pozice neuvádí.
- **Pečlivost a odpovědnost** — vlastnosti, které český CDK neřadí mezi
  měkké kompetence — se v textech inzerátů objevují častěji než nejvyšší
  CDK kompetence (pečlivost u účetních: 65,3 %).

Plné znění viz tištěná bakalářská práce, kapitoly 3 a 4.

## Jak je tento repozitář uspořádán

```
├── README.md                     ← tento soubor
├── LICENSE                       ← licence MIT (kód) — viz disclaimer níže
├── CITATION.cff                  ← jak práci citovat
├── requirements.txt              ← závislosti Pythonu
├── main.py                       ← vstupní bod (orchestruje 4 moduly)
│
├── config/                       ← veškerá konfigurace v YAML
│   ├── settings.yaml             ← globální nastavení
│   ├── jobs_cz.yaml              ← parametry scraperu
│   ├── cleanup.yaml              ← deduplikace a filtrace
│   ├── nlp.yaml                  ← stopwords, lemmatizace
│   └── tfidf.yaml                ← 18 kompetencí, 208 indikátorů
│
├── modules/                      ← Python kód pipeline
│   ├── jobs_cz/                  ← Scrapy spider (sběr dat)
│   ├── cleanup/                  ← čištění a deduplikace
│   ├── nlp/                      ← tokenizace + lemmatizace
│   └── tfidf/                    ← TF-IDF + detekce kompetencí
│
├── output/tfidf_analysis/        ← PŘEDGENEROVANÉ výsledky ★
│   ├── competency_dashboard.html ←  interaktivní dashboard
│   ├── competency_prevalence.png ←  graf prevalence kompetencí
│   ├── top_terms_tfidf.png       ←  top 50 termínů
│   ├── subgroup_top_terms.png    ←  Praha vs. regiony
│   ├── competency_report.json    ←  detailní výsledky detekce
│   ├── framework_summary.json    ←  konfigurační přehled
│   └── ... (další JSON reporty)
│
├── data/                         ← viz data/README.md
├── docs/
│   ├── PREVIEW.md                ← walkthrough kódu BEZ spouštění
│   └── METHODOLOGY.md            ← shrnutí metodiky pro reviewera
└── scripts/
    └── build_priloha_g.py        ← generuje segmentaci korpusu
```

### Co je kde — pro různé čtenáře

| Pokud chcete… | Otevřete… |
|---|---|
| Vidět výsledky detekce **vizuálně** | `output/tfidf_analysis/competency_dashboard.html` |
| Pochopit, **jak detekce funguje** bez čtení Pythonu | `docs/PREVIEW.md` |
| Vidět **úplnou definici** všech 18 kompetencí | `config/tfidf.yaml` |
| Pochopit, **jaká data jsou použita** | `data/README.md` |
| Reprodukovat analýzu | `docs/METHODOLOGY.md` + `requirements.txt` |
| **Citovat tuto práci** | `CITATION.cff` |

## Pipeline (architektonický přehled)

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  jobs_cz     │ →  │  cleanup     │ →  │  nlp         │ →  │  tfidf       │
│ (Scrapy)     │    │ (filtr+dedup)│    │ (lemma)      │    │ (analýza)    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
   1 500+ raw         1 046 ad           1 046 ad +            agregované
   inzerátů           po deduplikaci     description_tokens    výsledky
```

Každý modul:
- má vlastní YAML konfiguraci v `config/`
- má krátký `README.md` ve své složce
- lze spustit samostatně přes `python main.py --module <jméno>`

Detaily v [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Rychlé spuštění (pro technické čtenáře)

> Pro posouzení práce **nepotřebujete spouštět nic**. Tato sekce je pro
> ty, kdo chtějí kód reprodukovat nebo upravit.

```bash
# 1) prostředí
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

# 2) závislosti
pip install -r requirements.txt

# 3) spuštění
python main.py                # všechny moduly
python main.py --module tfidf # jen analýza
```

## Data — důležité upozornění

Surová data (úplné texty 1 046 inzerátů včetně názvů zaměstnavatelů a URL)
**nejsou** v tomto repozitáři uložena. Důvody jsou autorskoprávní (obsah
patří provozovateli portálu Jobs.cz, společnosti LMC s.r.o.) a ochrana
osobních údajů (zaměstnavatelé jsou identifikovatelnými subjekty).

Repozitář obsahuje pouze **agregované analytické výstupy** ve složce
`output/tfidf_analysis/`, ze kterých nelze rekonstruovat původní text
inzerátů. Plný seznam ID inzerátů zařazených do analýzy je v Příloze G
tištěné práce. Detaily v [`data/README.md`](data/README.md).

## Závislosti

Python 3.10+, hlavní knihovny:

| Knihovna | Účel |
|---|---|
| [scrapy](https://scrapy.org/) | Web scraping framework |
| [scikit-learn](https://scikit-learn.org/) | TF-IDF vektorizace |
| [simplemma](https://github.com/adbar/simplemma) | Multilingual lemmatizer |
| [matplotlib](https://matplotlib.org/) | Vizualizace |
| [pyyaml](https://pyyaml.org/) | Parsování konfigurace |
| [w3lib](https://github.com/scrapy/w3lib) | HTML utilities |

## Citování

Pokud na tuto práci odkazujete, použijte:

> Bobanych, S. (2026). *Aktuální požadavky na měkké dovednosti u administrativních
> pozic v ČR: Analýza pracovních inzerátů metodami NLP* (Bakalářská práce).
> Vysoká škola ekonomická v Praze, Fakulta podnikohospodářská.

Strojově čitelná verze citace v [`CITATION.cff`](CITATION.cff).

## Licence

Kód je publikován pod licencí [MIT](LICENSE). To znamená, že kód můžete
volně používat, upravovat i ve svých vlastních projektech, pokud zachováte
autorskou citaci.

**Upozornění:** Licence MIT se vztahuje pouze na zdrojový kód. Analytické
výsledky a metodika v `output/` a `docs/` jsou součástí akademické práce —
při jejich použití uveďte citaci výše.

---

*Autorka: Sofiia Bobanych • Vedoucí: Mgr. Marie Hořáková • VŠE Praha, květen 2026*
