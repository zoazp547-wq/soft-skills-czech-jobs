# Data

Tato složka je v repozitáři **záměrně prázdná**.

## Proč zde nejsou surová data

Bakalářská práce analyzuje **1 046 inzerátů z portálu Jobs.cz** (sběr 8. 3. 2026).
Surový text inzerátů však **není** v tomto repozitáři publikován ze dvou důvodů:

1. **Autorská práva.** Texty inzerátů a popisy zaměstnavatelů jsou autorským
   dílem inzerentů a portálu Jobs.cz (provozovatel: LMC s.r.o.). Jejich
   redistribuce v plné podobě by porušovala podmínky užívání portálu i
   autorský zákon.

2. **Ochrana osobních údajů.** Inzeráty obsahují názvy konkrétních
   zaměstnavatelů, kontaktní informace a v některých případech i osobní údaje.
   Publikování těchto údajů by představovalo zpracování osobních údajů
   ve smyslu GDPR bez právního základu.

## Co je k dispozici

| Zdroj | Co obsahuje | Kde najít |
|---|---|---|
| **Agregované analytické výstupy** | Frekvence kompetencí, TF-IDF skóre, dashboard | [`../output/tfidf_analysis/`](../output/tfidf_analysis/) |
| **Plný seznam ID zařazených inzerátů** | 1 046 ID, kategorizace pozic, lokality | Příloha G tištěné práce |
| **Konfigurace detekčního systému** | Všech 208 indikátorů 18 kompetencí | [`../config/tfidf.yaml`](../config/tfidf.yaml) |
| **Validační dataset** | 50 ručně anotovaných inzerátů + TP/FP/FN/TN | Příloha B tištěné práce |

## Jak data získat pro reprodukci

Datový sběr lze zopakovat spuštěním modulu `jobs_cz`:

```bash
python main.py --module jobs_cz
```

**Pozor:** Výsledný dataset se bude lišit od datasetu použitého v práci, protože
inzeráty na Jobs.cz jsou dynamické (aktivní inzeráty se mění průběžně). Pro
reprodukci konkrétních výsledků z práce by bylo nutné získat snapshot z
8. 3. 2026, který v současnosti není veřejně dostupný.

Pro akademické účely lze autorku kontaktovat ohledně sdílení anonymizované
verze datasetu (kontakt přes vedoucí práce).

## Technická poznámka — formát dat v pipeline

Pokud spustíte pipeline lokálně, vytvoří se v této složce (a budou ignorovány
gitem):

```
data/
├── jobs_cz_administrativa.json        ← surový výstup scraperu
├── jobs_cz_administrativa_clean.json  ← po deduplikaci a filtraci
└── jobs_cz_administrativa_nlp.json    ← s lemmatizovanými tokeny
```

Schema každého inzerátu (po cleanup):

```json
{
  "id": "string",
  "title": "string",
  "provider": "string",
  "location": "string",
  "url": "string",
  "description_text": "string",
  "category": "string"
}
```
