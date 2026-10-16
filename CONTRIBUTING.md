# Contributing

Thanks for helping improve Fixzy Marketing Tools.

## Setup

```bash
git clone https://github.com/mohdhafizi83/fixzy-marketing-tools.git
cd fixzy-marketing-tools
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in what you need; see docs/configuration.md
pytest tests -q
python app.py          # http://localhost:5558
```

Or run it in Docker: see [docs/getting-started.md](docs/getting-started.md).

## Before opening a PR

- `pytest tests -q` passes.
- `ruff check .` is clean (CI enforces it).
- Never commit real lead data. `fixzy.db` and `.env` are gitignored — keep
  them that way; anything with personal data stays out of git entirely.
- New outbound channels: add an adapter under `adapters/`, gate sends on the
  consent ledger + suppression list (see `docs/pdpa-compliance.md`), and add
  a test.

## Reporting security issues

Do not open a public issue — see [SECURITY.md](SECURITY.md).
