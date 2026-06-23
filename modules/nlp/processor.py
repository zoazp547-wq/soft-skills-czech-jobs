"""NLP text processing pipeline for scraped job listings.

Stages (applied per configured text field):
  1. Lowercase
  2. Tokenization (regex-based word splitting)
  3. Stop-word removal (Czech + English + custom)
  4. Lemmatization via simplemma
"""

import logging
import re
import unicodedata

import simplemma

logger = logging.getLogger("[nlp.processor]")

# ---------------------------------------------------------------------------
# Czech stop words — common function words, pronouns, prepositions, conjunctions
# ---------------------------------------------------------------------------
_CZECH_STOPWORDS: set[str] = {
    "a", "aby", "aj", "ale", "ani", "asi", "az", "až", "bez", "bude",
    "budem", "budeme", "budes", "budeš", "budou", "budu", "by", "byl",
    "byla", "byli", "bylo", "být", "co", "což", "či", "článek",
    "další", "do", "ho", "i", "jak", "jako", "je", "jeho", "jej",
    "její", "jejich", "jen", "ještě", "ji", "jiné", "již", "jsem",
    "jsi", "jsme", "jsou", "jste", "já", "k", "kam", "kde", "kdo",
    "kdy", "když", "ke", "která", "které", "který", "kteří", "let",
    "má", "mají", "máme", "máte", "mám", "mě", "mezi", "mi", "mít",
    "mne", "mnou", "moc", "moje", "mu", "může", "my", "má", "místo",
    "na", "nad", "nám", "námi", "nás", "naše", "ne", "nebo", "ně",
    "nebyl", "nebyla", "nebyly", "neboť", "něco", "nedělá", "nej",
    "nejsou", "není", "než", "nic", "nich", "ním", "no", "nové",
    "nový", "nás", "ná", "o", "od", "ode", "on", "ona", "oni", "ono",
    "ony", "pak", "pan", "po", "pod", "podle", "pokud", "pouze",
    "potom", "pro", "proč", "proto", "protože", "první", "před",
    "přes", "přese", "při", "přitom", "což", "re", "rok", "roku",
    "s", "se", "si", "sice", "skrz", "smí", "jsou", "sta", "sté",
    "své", "svůj", "svých", "svým", "svými", "ta", "tak", "také",
    "tato", "tedy", "ten", "tenhleten", "tento", "teto", "ti", "tím",
    "to", "tobě", "toho", "tohle", "tom", "tomu", "tomuto", "tu",
    "tuto", "tvůj", "ty", "tyto", "této", "těch", "těm", "těma",
    "u", "už", "v", "ve", "více", "však", "váš", "vy", "vám", "vás",
    "váš", "všechen", "z", "za", "zatímco", "ze", "že",
}

# ---------------------------------------------------------------------------
# English stop words — common function words
# ---------------------------------------------------------------------------
_ENGLISH_STOPWORDS: set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "get", "got", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "just", "let's", "me", "might", "more",
    "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
    "out", "over", "own", "same", "shan't", "she", "should", "shouldn't",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "were", "weren't", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "won't", "would",
    "wouldn't", "you", "your", "yours", "yourself", "yourselves",
}

# Tokenizer: splits on anything that is not a letter or an apostrophe
_TOKEN_SPLIT = re.compile(r"[^\w']+", re.UNICODE)

# Pattern that matches purely numeric strings
_NUMERIC = re.compile(r"^\d+$")


def build_stopwords(config: dict) -> set[str]:
    """Assemble the combined stop-word set from config flags."""
    sw_cfg = config.get("stopwords", {})
    combined: set[str] = set()

    if sw_cfg.get("czech", True):
        combined |= _CZECH_STOPWORDS

    if sw_cfg.get("english", True):
        combined |= _ENGLISH_STOPWORDS

    for word in sw_cfg.get("custom", []):
        combined.add(word.lower())

    logger.info(
        "Stop-word set built: %d words (cs=%s, en=%s, custom=%d)",
        len(combined),
        sw_cfg.get("czech", True),
        sw_cfg.get("english", True),
        len(sw_cfg.get("custom", [])),
    )
    return combined


def process_text(
    text: str,
    stopwords: set[str],
    lemma_langs: tuple[str, ...],
    min_length: int,
    remove_numbers: bool,
    remove_punct: bool,
) -> list[str]:
    """Run the full NLP pipeline on a single text string.

    Returns a list of cleaned, lemmatized tokens.
    """
    if not text:
        return []

    lowered = text.lower()
    raw_tokens = _TOKEN_SPLIT.split(lowered)

    result: list[str] = []
    for token in raw_tokens:
        token = token.strip("'")

        if len(token) < min_length:
            continue

        if remove_numbers and _NUMERIC.match(token):
            continue

        if remove_punct and _is_punctuation(token):
            continue

        if token in stopwords:
            continue

        lemma = simplemma.lemmatize(token, lang=lemma_langs)

        if lemma in stopwords:
            continue

        if len(lemma) < min_length:
            continue

        result.append(lemma)

    return result


def process_rows(rows: list[dict], config: dict) -> list[dict]:
    """Apply the NLP pipeline to all configured text fields in every row.

    For each field listed in config -> processing -> fields, a new column
    named {field}_tokens is added containing the processed token string.
    """
    proc_cfg = config.get("processing", {})
    fields = proc_cfg.get("fields", ["description_text"])
    lemma_langs = tuple(proc_cfg.get("lemma_languages", ["cs", "en"]))

    tok_cfg = config.get("tokenization", {})
    min_length = tok_cfg.get("min_token_length", 2)
    remove_numbers = tok_cfg.get("remove_numbers", True)
    remove_punct = tok_cfg.get("remove_punctuation", True)
    separator = tok_cfg.get("output_separator", " ")

    stopwords = build_stopwords(config)

    for field in fields:
        token_col = _token_column_name(field)
        processed_count = 0

        for row in rows:
            text = row.get(field, "")
            tokens = process_text(
                text, stopwords, lemma_langs, min_length, remove_numbers, remove_punct
            )
            row[token_col] = separator.join(tokens)
            processed_count += 1

        logger.info(
            "Field '%s' -> '%s': processed %d rows, langs=%s",
            field,
            token_col,
            processed_count,
            lemma_langs,
        )

    return rows


def _token_column_name(field: str) -> str:
    """Derive the output column name from the source field.

    "description_text" -> "description_tokens"
    "title"            -> "title_tokens"
    """
    if field.endswith("_text"):
        return field.rsplit("_text", 1)[0] + "_tokens"
    return field + "_tokens"


def _is_punctuation(token: str) -> bool:
    """Return True if every character in the token is a Unicode punctuation mark."""
    return all(unicodedata.category(ch).startswith("P") for ch in token)
