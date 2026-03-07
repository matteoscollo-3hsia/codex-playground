# sales-ops-automation

Automated commercial primer generation from Excel prompt libraries using OpenAI, with Word (DOCX) output.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (package manager)
- OpenAI API key

## Quickstart

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env: set OPENAI_API_KEY, PROMPT_LIBRARY_PATH, OUTPUT_BASE_DIR, PRIMER_WORD_TEMPLATE_PATH, HUBSPOT_TOKEN

# Core pipeline entrypoint: create lead input from HubSpot Private App
uv run python run.py create-input --from-hubspot "ACME"

# Start the primer generation from the saved lead_input.json
uv run python run.py generate-primer

# Or create a lead input interactively
uv run python run.py create-input

# Or generate a primer from an explicit lead_input path
uv run python run.py generate-primer --lead-input path/to/lead_input.json
```

## CLI Reference

### `create-input`

Create a lead input file interactively or fetch it from HubSpot. For real runs, `--from-hubspot` is the primary pipeline entrypoint.

```
uv run python run.py create-input [--lead-output PATH] [--company-name NAME] [--from-hubspot QUERY]
```

| Flag | Description |
|------|-------------|
| `--lead-output` | Path to write `lead_input.json` (overrides default placement) |
| `--company-name` | Company name used to place file under client repo layout |
| `--from-hubspot` | Fetch lead data from HubSpot by company name (requires `HUBSPOT_TOKEN`) |

### `generate-primer`

Generate a commercial primer from an Excel prompt library.

```
uv run python run.py generate-primer [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `--output-dir` | Override output directory (used as final output folder) |
| `--lead-input` | Path to `lead_input.json` (default: `LEAD_INPUT_PATH` or `./lead_input.json`) |
| `--sheet` | Run a single Excel sheet by name |
| `--include` | Regex or comma-separated list of sheet names to include |
| `--exclude` | Regex or comma-separated list of sheet names to exclude |
| `--resume` / `--no-resume` | Resume from existing `sources.json` (default: enabled) |
| `--include-headings` | Include sheet/step headings in `primer.md` (default: disabled) |

## Lead Input Fields

`lead_input.json` can now include:

| Field | Description |
|------|-------------|
| `deal_notes` | Concatenated HubSpot Notes (`hs_note_body`) associated with the selected deal |

When using `create-input --from-hubspot`, the tool fetches company data, primary contact data, and `deal_notes` from the real HubSpot Notes associated with the selected deal.

## Prompting With `deal_notes`

For a subsection such as `### 1.2 What we know so far`, use `{{deal_notes}}` directly and constrain the prompt explicitly so the model rewrites those notes without mixing them with website research.

Recommended rule block:

```text
### SPECIAL RULE FOR SECTION 1.2 WHAT WE KNOW SO FAR
- Section 1.2 must be based only on the content of `{{deal_notes}}`.
- Rewrite the notes into a clean, concise, consultant-style synthesis.
- Do not copy the notes verbatim unless strictly necessary.
- Remove duplicates, meeting logistics, greetings, and CRM artefacts.
- Do not add facts from website research to section 1.2.
- Do not infer facts that are not explicitly supported by `{{deal_notes}}`.
- If `{{deal_notes}}` is empty, missing, or not informative enough, write exactly: N/A
```

## Output Resolution

1. `--output-dir` flag (if provided, used as final output folder)
2. `client_output_dir` key in `lead_input.json`
3. `OUTPUT_BASE_DIR/<company_folder>` (client repo layout with `latest/` and `runs/`)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model to use (default: `gpt-5.2`) |
| `OPENAI_DEEP_RESEARCH_MODEL` | Deep research model (default: `o4-mini-deep-research`) |
| `PROMPT_LIBRARY_PATH` | Path to the Excel prompt library |
| `OUTPUT_BASE_DIR` | Base directory for per-client output repos |
| `LEAD_INPUT_PATH` | Default lead input path (fallback when `--lead-input` not passed) |
| `PRIMER_WORD_TEMPLATE_PATH` | Path to the Word template for DOCX output |
| `HUBSPOT_TOKEN` | HubSpot Private App token used by `create-input --from-hubspot` |
| `INCLUDE_HEADINGS` | Include headings in output (`1`/`true` to enable) |

## Scripts

Standalone utility scripts in `scripts/`:

| Script | Description |
|--------|-------------|
| `compare_docx_structure.py` | Compare two DOCX files and report structural differences |
| `extract_docx_spec.py` | Extract style/structure spec from a DOCX template as JSON |

## Project Structure

```
sales-ops-automation/
├── run.py                          # CLI entry point
├── pyproject.toml                  # Project config and dependencies
├── src/
│   └── primer_ops/
│       ├── __init__.py
│       ├── cli.py                  # Argument parsing and subcommands
│       ├── client_repo.py          # Client directory layout management
│       ├── config.py               # Environment variable helpers
│       ├── excel_helpers.py        # Excel/worksheet anchor and cell utilities
│       ├── io_helpers.py           # Atomic file write utilities
│       ├── lead_input.py           # Lead input model, deal_notes field, and interactive wizard
│       ├── hubspot_client.py       # HubSpot company/contact/deal/note retrieval
│       ├── openai_helpers.py       # OpenAI API calls, retries, response parsing
│       ├── primer.py               # Core primer generation orchestration
│       ├── progress.py             # Spinner and time formatting
│       └── render_docx.py          # Markdown → DOCX rendering engine
├── scripts/
│   ├── compare_docx_structure.py
│   └── extract_docx_spec.py
├── tests/
│   ├── test_docx_rendering.py      # DOCX heading/inline/normalization tests
│   ├── test_output_resolution.py   # Output path resolution tests
│   ├── test_primer_headings.py     # End-to-end primer generation test
│   └── unit/
│       ├── test_hubspot_client.py
│       ├── test_lead_input_hubspot.py
│       └── test_markdown_normalize.py
└── docs/
    └── review.md                   # Code review cleanup plan
```

## Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

## Known Limitations

- **Pattern-matching based sourcing.** Prompt extraction from Excel relies on rigid anchor patterns (`"Instructions"`, `"Prompts"`, `"Step N"`, `"Suggested Prompt"`). Sheets that deviate from the expected layout — extra rows, merged cells, renamed anchors — will silently produce incomplete prompts or fail at runtime. This should be paired with an LLM-as-a-judge validation step that evaluates whether the extracted prompts are coherent and complete.

- **No output quality validation.** Generated primer content is written as-is from the OpenAI response. There is no automated check for hallucinated facts, off-topic sections, missing coverage of requested topics, or tone/style consistency. A post-generation review step (human or LLM-based) is needed for production use.

- **Single-threaded, sequential sheet processing.** Sheets are processed one at a time because each sheet's output becomes the context for the next. This means a 10-sheet prompt library with deep research enabled can take 30+ minutes. Sheets that don't depend on each other could in principle be parallelized.

- **Brittle DOCX template coupling.** The Word renderer assumes specific style names exist in the template (`Heading 1`, `Heading 2`, `Normal`, etc.). If the template is modified or a different template is used, the output may silently fall back to default styles or produce misformatted documents.

- **Context window limits not enforced.** The accumulated context from previous sheets is injected into each prompt without checking whether it exceeds the model's context window. For large prompt libraries, later sheets may silently receive truncated context. Only a problem if ~1M tokens are reached (approx ~4M characters).
