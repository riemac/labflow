# literature-forensics

`literature-forensics` is a small, local-first command-line helper for building
an inspectable literature dossier. It queries documented public metadata APIs,
normalizes their results into a dossier-local SQLite cache, and only downloads a
PDF when `fetch` is explicitly requested.

Run it from this project directory or point `uv` at it:

```bash
uv run --project /home/hac/labflow/opencode/skills/literature-forensics/scripts \
  literature-forensics init --dossier ./my-dossier --title "Embodied AI" \
  --question "Which representations improve long-horizon manipulation?"

uv run --project /home/hac/labflow/opencode/skills/literature-forensics/scripts \
  literature-forensics search "long-horizon robot manipulation" \
  --sources arxiv,openalex,semantic-scholar,crossref --limit 20 \
  --include-abstracts --dossier ./my-dossier

uv run --project /home/hac/labflow/opencode/skills/literature-forensics/scripts \
  literature-forensics resolve "doi:10.48550/arXiv.1706.03762" \
  --dossier ./my-dossier --json

uv run --project /home/hac/labflow/opencode/skills/literature-forensics/scripts \
  literature-forensics graph "arXiv:1706.03762" --direction references \
  --depth 1 --limit 50 --dossier ./my-dossier

uv run --project /home/hac/labflow/opencode/skills/literature-forensics/scripts \
  literature-forensics fetch "arXiv:1706.03762" --dossier ./my-dossier

uv run --project /home/hac/labflow/opencode/skills/literature-forensics/scripts \
  literature-forensics export --kind bibtex --dossier ./my-dossier \
  --output ./my-dossier/bibliography.bib
```

## Credentials

Credentials are optional and are never written to the dossier or printed by
`doctor`. Set them in the environment when available:

```bash
export OPENALEX_API_KEY="..."
export SEMANTIC_SCHOLAR_API_KEY="..."
export CROSSREF_MAILTO="researcher@example.edu"
```

OpenAlex may require an API key for current service access. Semantic Scholar
also offers higher limits to authenticated requests. arXiv and Crossref can be
used without a key. The tool does not scrape Google Scholar.

## Data and safety

- Cache: `<dossier>/.state/literature-cache.sqlite` (WAL mode).
- Worker registry: `<dossier>/.state/workers.json`, atomically updated under a
  dossier-local lock.
- `fetch` accepts only HTTPS PDF URLs, follows redirects only to HTTPS URLs,
  streams to a temporary file, limits downloads to 100 MiB, requires a
  conservative PDF content type and a `%PDF-` signature near the start, and
  records a SHA-256 digest. HTML, login, error, and empty bodies are rejected.
- Remote fields are treated as untrusted metadata; identifiers and URLs are
  normalized before they enter the cache or form a filesystem path.
- `init --force` only restores missing unchanged skeleton files. It refuses to
  overwrite edited files and always refuses a dossier containing cached SQLite
  evidence or PDFs; it is never a reset command.

## Limits and failures

`--limit` is a global result or edge budget, not a per-provider budget.
Requests are bounded to current provider page caps: OpenAlex 200, Crossref
1,000, and Semantic Scholar 100 search results (1,000 graph relations). An
OpenAlex reference expansion uses batched work lookups rather than one request
per reference.

Search and graph preserve individual backend errors in JSON and write them to
stderr. A partial failure exits successfully when another requested backend
returns usable results or edges. They exit nonzero only if every requested
backend failed and no usable result was produced.

Use `literature-forensics doctor --dossier ./my-dossier` to inspect local
prerequisites and credential presence. `--json` produces compact, stable JSON
for every command that returns structured data.
