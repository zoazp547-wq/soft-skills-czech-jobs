NLP Module
==========

Takes the cleaned CSV and produces tokenized, lemmatized text columns
ready for downstream analysis (TF-IDF, topic modelling, classification, etc.).
Run: python main.py --module nlp


Pipeline stages (applied per configured text field):
-----------------------------------------------------

1. LOWERCASE
   Converts all text to lowercase for uniform matching.

2. TOKENIZATION
   Splits text on non-word characters (whitespace, punctuation, symbols).
   Filters out:
     - Tokens shorter than 2 characters (configurable).
     - Purely numeric tokens (e.g. "2026", "1000").
     - Punctuation-only tokens.

3. STOP-WORD REMOVAL
   Removes common function words that carry little meaning:
     - Czech stop words (~200 words: pronouns, prepositions, conjunctions).
     - English stop words (~170 words).
     - Custom domain-specific stop words (e.g. "nabídka", "pozice", "firma").
   Applied both before and after lemmatization to catch inflected forms.

4. LEMMATIZATION (simplemma)
   Reduces each token to its dictionary base form.
   Uses Czech as the primary language, English as fallback.
   Examples: "zaměstnanců" -> "zaměstnanec", "running" -> "run".


Output columns:
  - All original columns are preserved.
  - New *_tokens columns are appended (e.g. description_tokens, title_tokens).
  - Tokens are space-separated strings.

Input:  output/jobs_cz_administrativa_clean.csv
Output: output/jobs_cz_administrativa_nlp.csv
Config: config/nlp.yaml
