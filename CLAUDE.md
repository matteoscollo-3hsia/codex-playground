# CLAUDE.md — sales-ops-automation

## Project Purpose

Generates **commercial primer** documents (Word/DOCX) from an Excel prompt library using the OpenAI API. The package is `primer_ops` (src layout). Users run a two-step CLI: create a lead input JSON, then generate the primer.

## Development Environment

- **Package manager:** `uv` exclusively — never `pip` or `pip install`
- **Linter/formatter:** `ruff`
- **Test runner:** `pytest`
- **Python:** 3.10+

### Common Commands

```bash
uv run pytest                        # run all tests
uv run pytest tests/unit/            # unit tests only
uv run ruff check src/ tests/        # lint
uv run ruff format src/ tests/       # format
uv run python run.py create-input                        # interactive lead input wizard
uv run python run.py create-input --from-hubspot "ACME" # fetch lead data from HubSpot
uv run python run.py generate-primer                     # generate primer from Excel + lead JSON
uv run python run.py generate-primer --resume            # resume from existing sources.json
```

### Claude Slash Commands

- `/project:new-client-run` — guided end-to-end run for a new client (HubSpot fetch → confirm → generate)

## Architecture

```
run.py / src/primer_ops/cli.py       ← CLI entry points (argparse)
src/primer_ops/
  config.py         ← env var helpers (OUTPUT_BASE_DIR, LEAD_INPUT_PATH, INCLUDE_HEADINGS)
  lead_input.py     ← Pydantic LeadInput model + interactive wizard + run_create_input_from_hubspot()
  hubspot_client.py ← HubSpot API client: search_companies, get_associated_contacts, fetch_lead_from_hubspot
  client_repo.py    ← company folder structure: latest/ + runs/<date>_<uuid>/
  primer.py         ← main orchestrator: generate_primer() (~620 lines — intentionally monolithic for now)
  excel_helpers.py  ← anchor parsing, placeholder replacement (4 syntaxes: {{k}}, {k}, #k#, << k >>)
  openai_helpers.py ← API calls, exponential backoff retry, citation extraction
  io_helpers.py     ← atomic writes (.tmp → rename), multi-path output
  render_docx.py    ← Markdown → DOCX via markdown-it-py + python-docx
  progress.py       ← LiveTimer, print_sheet_bar, spinner (with elapsed time), format_seconds
.claude/commands/
  new-client-run.md ← /project:new-client-run slash command
```

### Data Flow

```
Lead JSON + Excel prompt library
    → sheet filtering (include/exclude)
    → per-sheet: parse anchors → replace placeholders → call OpenAI → save to sources.json
    → accumulate markdown → render primer.docx
    → write to: latest/ AND runs/<date>_<uuid>/
```

Resume logic: if `sources.json` exists, completed steps are skipped automatically.

## Code Conventions

Follow the coding standards in [skills/coding-standards/SKILL.md](skills/coding-standards/SKILL.md). Key rules:

- Type hints with native Python 3.10+ syntax: `str | None`, `list[str]`, `dict[str, int]`
- No `Optional`, `List`, `Dict` from `typing` — use native types
- f-strings for string formatting
- `pathlib.Path` for all path operations, never `os.path`
- Specific exception handling — never bare `except Exception: pass`
- `logger = logging.getLogger(__name__)` — never `print()` for logging
- Descriptive snake_case names; verb-noun for functions (`fetch_user_data`, not `data`)
- No mutable default arguments
- Early returns over deep nesting

## Known Issues & Active Constraints

1. **`generate_primer()` is monolithic** (~620 lines in `primer.py`) — this is a known debt, not a bug. Do not refactor it unless explicitly asked.
2. **No context window enforcement** — accumulated sheet context is not token-counted before API calls. Do not silently add truncation; flag it as a known limitation.
3. **Silent file I/O failures** — `_safe_write_text()` and `_safe_write_json()` swallow `OSError`. Adding `logging.warning()` calls is welcome.
4. **Hardcoded model names** — `gpt-5.2`, `o4-mini-deep-research` are in `primer.py`. They belong in `config.py` (pending refactor).
5. **4 placeholder syntaxes** — `{{k}}`, `{k}`, `#k#`, `<< k >>` all work. Do not add a fifth; do not remove any without explicit instruction.

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI authentication | required |
| `OPENAI_MODEL` | Base model name | `gpt-5.2` |
| `OPENAI_DEEP_RESEARCH_MODEL` | Deep research model | `o4-mini-deep-research` |
| `OPENAI_MAX_RETRIES` | Max retry attempts | `6` |
| `OPENAI_RETRY_BASE_SECONDS` | Exponential backoff base | `0.5` |
| `OUTPUT_BASE_DIR` | Base directory for primer output | required |
| `LEAD_INPUT_PATH` | Path to lead JSON file | `./lead_input.json` |
| `INCLUDE_HEADINGS` | Add section headings to output | `false` |
| `PROMPT_LIBRARY_PATH` | Path to Excel prompt library | required |
| `PRIMER_WORD_TEMPLATE_PATH` | Word template for DOCX rendering | optional — uses default styles if unset |
| `HUBSPOT_TOKEN` | HubSpot Private App token for `--from-hubspot` | optional |

See `.env.example` for a complete reference. **Never commit `.env`.**

### HubSpot setup (for `--from-hubspot`)
1. HubSpot → Settings → Integrations → **Private Apps** → create app
2. Required scopes: `crm.objects.companies.read`, `crm.objects.contacts.read`
3. Set the generated token as `HUBSPOT_TOKEN` in `.env`

## Testing

Tests live in `tests/`. Unit tests in `tests/unit/`. Pytest config is in `pyproject.toml`.

Current gaps (do not assume these are covered):
- OpenAI retry logic / exponential backoff
- Resume functionality with partial `sources.json`
- Sheet filtering (regex + comma-separated)
- Citation extraction from OpenAI response
- Deep research model fallback behavior

When adding new functionality, add tests. Prefer small, focused tests with descriptive names (`test_returns_empty_list_when_no_match`, not `test_search`).

## What NOT to Do

- Never use `pip` — always `uv`
- Never commit `.env` — only `.env.example`
- Never add placeholder syntaxes beyond the existing 4
- Never swallow exceptions silently without at minimum a `logging.warning()`
- Never use `os.path` — use `pathlib.Path`
- Never add backwards-compatibility shims or `_unused` variable renames
- Do not refactor `generate_primer()` into sub-functions unless explicitly requested
- Do not add features or abstractions not directly requested (YAGNI)
