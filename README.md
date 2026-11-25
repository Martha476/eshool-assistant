# eSchool Search Assistant

A small Python prototype that converts a parent's natural-language school request
into explicit search filters, queries eSchool Manager's public school-search page,
and explains which listing details support each requested preference.

## Requirements

- Python 3.10 or newer
- An OpenAI API key for live natural-language interpretation
- Network access to the OpenAI API and `eschool.ug` for live searches

The offline demo and automated tests require no API key or network access.

## Install

From the project directory, create and activate a virtual environment, then install
the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` in the project-root `.env`. The file is ignored by git; do
not commit keys. `OPENAI_MODEL` is optional and defaults to `gpt-4o-mini`.

## Run

### Web UI

```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. The page submits the parent's request as JSON to the
same-origin `POST /search` endpoint and renders its structured response. Since the
browser and API share an origin, no CORS configuration is needed.

### CLI

```powershell
python -m app.cli "Girls' boarding school in Kampala under UGX 1 million per term"
```

Or run interactively with `python -m app.cli`.

### HTTP API

```powershell
uvicorn app.main:app --reload
```

Send a JSON request to `POST http://127.0.0.1:8000/search`:

```json
{"request":"Girls' boarding school in Kampala under UGX 1 million per term"}
```

`GET /health` returns `{"status":"ok"}`. The search response includes the criteria,
eSchool URL, result details, confirmed match reasons, and any unverified details.

### Demonstration

```powershell
python demo.py --offline
```

This writes `DEMO.md` using clearly synthetic HTML fixtures and fixed example
interpretations; it demonstrates the pipeline, not live eSchool data or AI accuracy.
Omit `--offline` to interpret the sample prompts with OpenAI and search the live site.

## Tests

```powershell
python -m pytest
```

Tests mock the AI and HTTP calls. They do not require credentials, internet access,
or real school records.

## Project layout

- `app/`: validated criteria, AI interpreter, retrieval grounding, eSchool client,
  deterministic matcher, orchestration, API, and CLI.
- `knowledge/`: Uganda education glossary and the live site's filter-option snapshot.
  This is reference data only, not a school dataset.
- `tests/fixtures/`: synthetic HTML used to test parsing and edge cases.
- `inspect_site.py`: helper to inspect the public search form and export current options.
- `DESIGN.md`: design decisions, integration details, assumptions, and limitations.
- `DEMO.md`: three representative sample requests and outputs.

## eSchool integration limitations

The client uses the public search URL. The example parameters
(`location`, `county`, `min_fees`, `max_fees`, `gender`) and the current public
form also expose school-name, level, accommodation, admission-status, curriculum,
facility, and affiliation filters. The app maps these to the observed form names
(`q`, `levels[]`, `accomadation`, `admission_status`, `curriculums[]`,
`facilities[]`, and `religions[]`). It does not access private APIs or reproduce
eSchool's search engine. Run
`python inspect_site.py` to inspect current public form fields and
`python inspect_site.py --export-options knowledge/eschool_options.json` to refresh
the option snapshot. The county/area options are populated dynamically by the live
page and therefore may not be present in the exported static HTML; unknown county
wording is left unchanged rather than guessed.

The public page's result markup may change; the parser supports both the synthetic
`.school-card` fixtures and observed `article.card` listings, with selectors in
`app/eschool_client.py`. A missing results section is reported as an error rather
than misrepresented as no matches. Admission class is not a public search filter
and is checked against visible listing text when available. The current result
cards expose school name, location, level, admissions status, and rating, but do not
show all details (for example fees, gender, or accommodation); absence
of evidence is reported as unverified, not as a match. The sample fixture results
are not real schools.
