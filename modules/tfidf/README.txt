TF-IDF Analysis & Competency Detection Module
===============================================

Analyzes tokenized job descriptions using TF-IDF to find important terms,
then detects soft-skill competencies using a hybrid matching approach.
Run: python main.py --module tfidf


Part 1 — TF-IDF Analysis:
--------------------------

1. Builds a term-document matrix using scikit-learn TfidfVectorizer.
2. Extracts top 30 terms ranked by mean TF-IDF score.
3. Counts document frequency (how many jobs mention each term).
4. Classifies top terms as soft skill / hard skill / noise.
5. Generates a colour-coded horizontal bar chart.


Part 2 — Competency Detection (Hybrid):
-----------------------------------------

Detects 18 competencies from a structured framework across 4 groups:

  Osobnostní (Personal):
    - Celoživotní vzdělávání, Flexibilita, Kreativita, Zvládání stresu

  Interpersonální (Interpersonal):
    - Efektivní komunikace, Kooperace, Orientace na zákazníka,
      Ovlivňování a rozvíjení ostatních, Sebepoznání, Vedení lidí

  Kognitivní (Cognitive):
    - Analytické myšlení, Koncepční myšlení, Orientace v informacích

  Výkonové (Performance):
    - Aktivní přístup, Plánování a organizování, Podnikavost,
      Řešení problémů, Samostatnost

Detection method (hybrid):
  - Token keywords: matched against lemmatized tokens from the NLP module.
  - Phrase patterns: matched as substrings against cleaned description text.
  A competency is detected if ANY indicator (keyword or phrase) matches.

Output per job: which competencies detected, which indicators fired, count.
Output aggregate: prevalence (% of jobs mentioning each competency).


Outputs:
--------
  output/tfidf_analysis/top_terms_report.json       -- TF-IDF top terms
  output/tfidf_analysis/top_terms_tfidf.png          -- TF-IDF bar chart
  output/tfidf_analysis/competency_report.json       -- per-job + aggregate
  output/tfidf_analysis/competency_prevalence.png    -- prevalence bar chart

Config: config/tfidf.yaml
