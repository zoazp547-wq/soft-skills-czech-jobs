# Metodika — souhrn pro reviewera

> Tato stránka shrnuje metodiku použitou v práci jazykem srozumitelným i pro
> ne-technického čtenáře. Plné metodologické zdůvodnění a literární kontext
> najdete v kapitole 2 tištěné bakalářské práce.

## Datový sběr

- **Zdroj:** portál Jobs.cz (LMC s.r.o.)
- **Kategorie:** Administrativa
- **Datum sběru:** 8. 3. 2026
- **Nástroj:** Python framework Scrapy (modul `jobs_cz`)
- **Politika:** dodržování `robots.txt`, prodleva mezi requesty 1,5 s, max. 4
  paralelní spojení

## Filtrace a deduplikace

Modul `cleanup` aplikuje:

1. **Required-fields filter** — vyřazení záznamů bez `id`, `title` nebo `url`
2. **Length filter** — vyřazení popisů kratších než 50 znaků
3. **Primary deduplication** — podle `id` (přesná shoda)
4. **Secondary deduplication** — podle kombinace `title + provider + location`
5. **HTML cleanup** — odstranění tagů přes `w3lib.html.remove_tags`

**Výsledek:** 1 046 inzerátů od 808 unikátních zaměstnavatelů.

## NLP zpracování

Modul `nlp` aplikuje na text klasický NLP pipeline:

1. **Lowercase**
2. **Tokenizace** — regex `[^\w']+`
3. **Odstranění stop-slov** — vlastní seznam českých (~130) a anglických (~130)
   stop-slov + možnost custom slov v `config/nlp.yaml`
4. **Lemmatizace** — knihovna `simplemma`, jazyky `cs` a `en`
5. **Filtrace** — odstranění čistě numerických tokenů a tokenů kratších než 2
   znaky

**Výstup:** pro každý inzerát pole `description_tokens` (lemmatizovaný text
oddělený mezerami).

## TF-IDF analýza

Modul `tfidf` (soubor `analyzer.py`) provádí:

- **Vektorizaci** přes `sklearn.feature_extraction.text.TfidfVectorizer`
- **N-gramy:** 1–2 (unigramy + bigramy)
- **Filtry:** `min_df=3` (term musí být alespoň ve 3 dokumentech),
  `max_df=0.90` (term v >90 % dokumentů je vyřazen)
- **Top-N extrakce:** 50 termínů podle průměrného TF-IDF skóre

Výstup: `top_terms_report.json` + bar chart.

## Detekce 18 kompetencí — hybridní přístup

Hlavní příspěvek metodiky práce. Pro každou ze 18 měkkých kompetencí (CDK
rámec) jsou definovány tři typy indikátorů:

| Typ | Co dělá | Kde se aplikuje |
|---|---|---|
| **token_keywords** | Lemmatizovaná klíčová slova | Tokenizovaný text |
| **phrase_patterns** | Víceslovné fráze (substring match) | Původní (nelemmatizovaný) text |
| **exclusion_phrases** | Vylučovací fráze pro disambiguaci | Plný text inzerátu |

**Celkem:** 61 token keywords + 147 phrase patterns + 8 exclusions = **208 indikátorů**.

### Příklad vylučovací fráze

Slovo „vedení" může znamenat:
- *leadership* → kompetence „Vedení lidí" ✅
- *vedení účetnictví* → administrativní úkon, nikoli kompetence ❌

Proto má kompetence „Vedení lidí" 7 vylučovacích frází typu `vedení účetnictví`,
`vedení agendy`, atd. Pokud se některá vyskytne v textu, kompetence se ignoruje.

### Dvourežimová detekce

Detekce běží paralelně ve dvou režimech:

- **`target_sections_only` (hlavní)** — modul `sections.py` rozpozná hlavičky
  sekcí inzerátu (požadavky / náplň / benefity / o firmě) podle regexů a
  detekce se aplikuje **jen na požadavky a náplň práce**. Tím se výrazně
  snižují false positives z benefit-sekcí.
- **`all_text` (kontrolní)** — detekce na celém textu, slouží k vyčíslení míry
  inflace prevalence (Tabulka 6, Příloha F).

## Validace

- **Vzorek:** 50 inzerátů (stratifikovaná náhodná výběr — Praha vs. regiony
  v poměru odpovídajícím celému korpusu)
- **Anotace:** ručně, autorka práce, pro každý inzerát všech 18 kompetencí
- **Metriky:** TP / FP / FN / TN, precision, recall, F1 — pro každou kompetenci
  zvlášť i agregovaně (macro a vážený průměr)
- **Výsledek:** macro F1 = 0,51, vážený F1 = 0,64

Detailní výsledky validace viz Příloha B.

## Tematická analýza (kvalitativní triangulace)

Pro ověření klíčových zjištění (zejména dominance interpersonálních kompetencí
u účetních a absence pečlivosti v CDK) byla provedena tematická analýza:

- **Software:** MAXQDA 24
- **Metoda:** šestifázový postup Braun & Clarke (2006)
- **Vzorek:** 30 inzerátů (15 účetních + 15 asistentů, náhodný výběr)
- **Schéma kódování:** 28 kódů (18 CDK kompetencí + 5 osobnostních vlastností
  + 5 hard skills jako kontext)
- **Výsledek:** 207 kódovaných segmentů

Detaily v kapitole 3.4.6, schéma kódování v Příloze D.

## Co repozitář NEobsahuje

Pro úplnost — práce zahrnuje navíc následující prvky, které **nejsou** v kódu
implementovány a jsou součástí pouze tištěné práce:

- Tematická analýza v MAXQDA 24 (proprietární SW, výstupy v Příloze D)
- Statistické testy (z-test proporcí, Bonferroniho korekce) — provedeny
  manuálně v R / Excel, výpočty v kapitole 3.3.2 a Příloze F
- Srovnání s normativními rámci (CDK/NSP, O\*NET, ESCO) — manuální analýza
  veřejně dostupných databází

## Reprodukovatelnost

| Co lze reprodukovat | Jak |
|---|---|
| Detekční systém na novém datasetu | `python main.py` (konfigurace v `config/`) |
| Výsledky validace | Z Přílohy B + spuštění detektoru |
| Výsledky TF-IDF | Z `tfidf_analysis/*.json` |
| Konkrétní hodnoty z práce | Vyžaduje původní dataset z 8. 3. 2026 (viz `data/README.md`) |

## Limity (stručně)

- **Rule-based přístup** s pevně danými indikátory — nezachytí kompetence
  vyjádřené opisem (viz Gavrilescu et al., 2025).
- **Jeden anotátor** pro validaci — chybí inter-coder reliability (Messum et
  al., 2016).
- **Snapshot v čase** — analýza zachycuje stav trhu k 8. 3. 2026, ne longitudinální vývoj.
- **Jeden portál** (Jobs.cz) — výsledky nemusí být reprezentativní pro celý
  český trh práce.

Plná diskuze limitů v kapitole 4.4 práce.
