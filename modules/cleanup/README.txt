Cleanup Module
==============

Takes raw scraped CSV output and produces a cleaned version.
Run: python main.py --module cleanup


Pipeline stages (executed in order):
-------------------------------------

1. REQUIRED FIELDS FILTER
   Drops rows where id, title, or url are empty/missing.

2. SHORT DESCRIPTION FILTER
   Drops rows with description_text shorter than 50 characters (configurable).
   This removes entries from JS-rendered pages that couldn't be scraped.

3. DEDUPLICATION
   - Primary: exact match on job id.
   - Secondary: exact match on title + provider (catches same job under different ids).

4. TEXT CLEANUP (description_text)
   - Replaces non-breaking spaces with regular spaces.
   - Decodes leftover HTML entities (&amp; -> &, etc.).
   - Inserts newline separators between sections that were merged during HTML tag stripping.
   - Collapses multiple whitespace into single spaces per line.

5. PRIVACY REDACTION
   Replaces personal information with [REDACTED]:
   - Phone numbers (Czech +420 and international formats).
   - Email addresses.
   - Contact names following "Kontakt:" / "Kontaktní osoba:" labels.

6. FIELD NORMALIZATION
   - Trims whitespace from all fields.
   - Normalizes provider legal suffixes (s. r. o. -> s.r.o., a. s. -> a.s.).
   - Normalizes location: strips street addresses, keeps city/district.
   - Validates that URLs start with https://.

7. COLUMN SELECTION
   Drops description_html (reduces file size significantly).
   Output columns: id, title, provider, location, url, description_text, category.


Configuration: config/cleanup.yaml
Output:        output/jobs_cz_administrativa_clean.csv
