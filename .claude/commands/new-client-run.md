Start a full primer generation run for a new client.

## Steps

1. Ask the user: "Nome del cliente (come appare su HubSpot)?"
2. Run the HubSpot fetch to create the lead input:
   ```
   uv run python run.py create-input --from-hubspot "<COMPANY_NAME>"
   ```
   If the command fails because HUBSPOT_TOKEN is not set, fall back to the manual wizard:
   ```
   uv run python run.py create-input --company-name "<COMPANY_NAME>"
   ```
3. Show the user the contents of the generated `lead_input.json` and ask for confirmation: "I dati sono corretti? (y/n)"
   - If no, ask which fields to correct and re-run the wizard manually.
4. Once confirmed, generate the primer:
   ```
   uv run python run.py generate-primer
   ```
5. When generation completes, report:
   - Path to `primer.docx`
   - Path to `primer.md`
   - Path to `sources.json`
   - Any errors or warnings encountered
