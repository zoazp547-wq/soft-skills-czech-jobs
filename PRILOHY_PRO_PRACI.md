# Mapování Příloh tištěné práce na soubory v repozitáři

> Pro oponenta a komisi — tento přehled ukazuje, kde v tomto repozitáři
> najdete podklady ke každé z Příloh tištěné bakalářské práce.

| Příloha | Obsah Přílohy | Zdroj v repozitáři |
|---|---|---|
| **A** | Plný seznam 208 detekčních indikátorů (61 token + 147 phrase + 8 exclusion) pro 18 kompetencí | [`config/tfidf.yaml`](config/tfidf.yaml), sekce `competencies:` |
| **B** | Validační dataset (50 inzerátů, ruční anotace, TP/FP/FN/TN) | Příloha B tištěné práce; vstupní data nelze publikovat |
| **C** | TF-IDF top 50 termínů s číselnými hodnotami | [`output/tfidf_analysis/top_terms_report.json`](output/tfidf_analysis/top_terms_report.json) |
| **D** | Schéma kódování MAXQDA (28 kódů) + ilustrativní citace | Příloha D tištěné práce |
| **E** | Plná YAML konfigurace detekčního systému | [`config/tfidf.yaml`](config/tfidf.yaml) (úplný soubor) |
| **F** | Porovnání režimů `all_text` vs. `target_sections_only` + regex hlaviček sekcí | [`output/tfidf_analysis/competency_report.json`](output/tfidf_analysis/competency_report.json), klíč `dual_mode`; regexy v `config/tfidf.yaml`, klíč `sections.header_patterns` |
| **G** | Segmentace korpusu (1 046 ID × role × lokalita × délka) | Vygenerováno přes [`scripts/build_priloha_g.py`](scripts/build_priloha_g.py); plný výpis v Příloze G tištěné práce |
| **H** | Odkaz na repozitář + commit hash | Tato stránka. Hash konkrétního commitu odpovídajícího odevzdané verzi: viz Příloha H tištěné práce |
| **I** | Vyloučené tituly z asistentského podkorpusu | Příloha I tištěné práce |
| **J** | Poznámka k inter-coder reliability | Příloha J tištěné práce |

## Struktura výstupů `output/tfidf_analysis/`

| Soubor | Co obsahuje | Souvisí s |
|---|---|---|
| `competency_dashboard.html` | Interaktivní dashboard se všemi grafy | Celá kapitola 3 |
| `competency_prevalence.png` | Bar chart prevalence 18 kompetencí | Tabulka 5, Obrázek 6 |
| `competency_report.json` | Detailní detekční výsledky pro všech 1 046 inzerátů | Kapitola 3.3, Příloha F |
| `framework_summary.json` | Strukturovaný přehled konfigurace (18 kompetencí, 4 skupiny, indikátory) | Tabulka 3, Příloha A |
| `top_terms_report.json` | Top 50 termínů + TF-IDF skóre + klasifikace (soft/hard/noise) | Obrázek 4, Příloha C |
| `top_terms_tfidf.png` | Vizualizace top 50 termínů | Obrázek 4 |
| `subgroup_comparison.json` | Praha vs. regiony — terminologické rozdíly | Kapitola 3.3.2, Obrázek 5 |
| `subgroup_significance.json` | Statistická významnost rozdílů (z-test, Bonferroni) | Tabulka 6 |
| `subgroup_top_terms.png` | Praha vs. regiony — vizualizace | Obrázek 5 |
