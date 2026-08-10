# Volapük Accuracy-First MT v4

Accuracy-first, long-text, multilingual-to-Volapük translation workbench.

## Why the full Midgley dictionary is not bundled

The source site identifies the English–Volapük and Volapük–English dictionaries as works by Ralph Midgley and displays a copyright notice. This repository therefore **does not redistribute the complete dictionary text**.

Instead, v4 includes a local importer. If you have legitimately obtained the dictionary PDF/DOCX files, import them on your own machine. The resulting SQLite database stays local unless you choose to publish it.

Recommended import uses **both directions**:

- English–Volapük Dictionary, revised 2010-08-30
- Volapük–English Dictionary, revised 2010-08-30

Entries seen in both directions are marked `X2` (cross-confirmed). One-direction or structurally ambiguous entries remain indexed as `X1/HOLD`; they are searchable but are not automatically trusted for publication-grade translation.

## Architecture

```text
source text (many languages)
  -> language detection
  -> source -> English semantic bridge (Argos Translate, optional)
  -> sentence segmentation + English dependency parse (spaCy)
  -> full local dictionary index
  -> conservative sense/POS selection
  -> Volapük morphology and syntax
  -> per-sentence READY / REVIEW / HOLD
```

The engine deliberately refuses unsupported syntax instead of inventing fluent-looking Volapük.

## Install

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Run:

```bash
python app.py
```

Then open `http://127.0.0.1:5000`.

## Import the complete dictionaries locally

Place your downloaded dictionary files anywhere on your computer, then:

```bash
python scripts/import_dictionary.py \
  --envo "C:\path\EnVoDictionary-20100830.pdf" \
  --voen "C:\path\VoEnDictionary-20100830.pdf" \
  --db data/volapuk.sqlite3
```

DOCX is also supported.

The importer keeps every non-empty dictionary line in `raw_lines`, so **nothing is silently discarded**. Parsed entries are stored separately. Ambiguous lines remain available for review instead of being forced into a wrong lexical mapping.

## Multilingual input

Argos Translate is optional. English works without it.

Install a source -> English package, for example Japanese -> English:

```bash
python scripts/install_argos.py ja en
```

List available models:

```bash
python scripts/install_argos.py --list
```

Argos can pivot through intermediate languages if installed. v4 marks a pivoted source normalization as `REVIEW`, not `READY`, because an extra MT step can alter meaning.

## Publication-grade rule

A sentence is `READY` only if:

1. source normalization did not require an unverified pivot;
2. the English parse is supported;
3. every content lemma resolves to a unique high-confidence dictionary entry;
4. all generated case/person/tense/voice rules are supported;
5. no proper-name or sense ambiguity remains.

`REVIEW` means the sentence may be good but contains an uncertainty worth checking.

`HOLD` means v4 will not certify it for direct Vükiped posting.

A long pasted paragraph is globally `READY` only when **every sentence is READY**.

## Dictionary grades

- `A`: small manually curated grammar/core vocabulary shipped with the program.
- `X2`: locally imported dictionary relation cross-confirmed from both dictionary directions.
- `X1`: parsed from one direction only.
- `HOLD`: raw or ambiguous entry not safe for automatic use.
- `W-LEMMA`: optional runtime concept evidence from Wikidata/Vükiped, when used by a future extension.

## Important limitation

“Paste any language and receive Vükiped-ready text” cannot be guaranteed by a rule engine. Natural-language translation has genuine ambiguity. v4 is designed to maximize **precision**, so increased coverage often appears as fewer HOLDs after you import the full dictionary, not as a promise that every arbitrary sentence becomes READY.

## Wikimedia API etiquette

If you extend the app to call Wikimedia APIs from a deployed service, identify your client according to Wikimedia API etiquette and cache results rather than repeatedly requesting identical data.


## GitHub + Render deployment

GitHub Pages cannot execute this application because Pages does not support
server-side Python. Keep the source code on GitHub and deploy the repository as
a Python Web Service on Render.

This repository includes `render.yaml`.

### Quick deploy

1. Create a GitHub repository and push this folder.
2. In Render, create a new Web Service from the GitHub repository, or use the
   repository's `render.yaml`.
3. Build command: `bash build.sh`
4. Start command:
   `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 app:app`
5. Health check: `/healthz`

`ARGOS_SOURCE_LANGS` controls which source-to-English Argos packages are
installed at build time. The supplied Render config uses `ja`. To support more
languages, use a comma-separated list such as:

```text
ja,de,fr,es,ru
```

Installing many models makes builds and memory/storage requirements much
larger. Add languages deliberately and test them.

### Important: dictionary persistence on Render

Render's default filesystem is ephemeral. On a Free web service, a dictionary
uploaded through the web UI and its generated SQLite database can disappear
when the service spins down, restarts, or redeploys.

For a durable private/full-dictionary installation, use a paid Render Web
Service with a persistent disk, for example mount `/var/data`, then set:

```text
VOLAPUK_DB_PATH=/var/data/volapuk.sqlite3
VOLAPUK_UPLOAD_DIR=/var/data/uploads
```

Do not commit the imported complete dictionary database or source dictionary
PDFs to a public GitHub repository unless you have confirmed redistribution
rights.

### GitHub repository contents

Safe to publish as source code:

- Python application code
- templates
- importer
- core lexicon
- `render.yaml`
- `.python-version`
- MIT `LICENSE`

Excluded by `.gitignore`:

- imported PDF/DOCX dictionaries
- generated SQLite dictionary databases
- uploaded files

## License

The code in this repository is MIT licensed. Imported dictionary content is **not** covered by the code license; its rights remain with its source rights-holders.
