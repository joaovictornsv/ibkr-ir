# ibkr-ir

Generate an HTML guide to help Brazilian residents fill **IRPF** fields from an Interactive Brokers **Activity Statement** (CSV).

## Status

Implementation complete for core workflow. Run against your private Activity Statement export locally.

## Quick start (once implemented)

```bash
python generate.py \
  --year 2026 \
  --statement /path/to/your/activity_statement.csv \
  --output output/irpf-2026.html
```

**Do not commit your Activity Statement CSV** — it contains personal and account data. Keep exports outside the repo or in a gitignored path.

## Input

One file only: IBKR **Activity Statement** exported as CSV (Jan 1 – Dec 31 of the target year).

Export steps are documented in the generated HTML report and in `docs/PLAN.md`.

## Output

- `output/irpf-{year}.html` — step-by-step IRPF copy-paste guide
- `output/irpf-{year}.json` — machine-readable snapshot for next year's prior-value carry-forward (gitignored by default)

## Privacy & public repo

This project is generic and open source. It must not ship personal account numbers, names, or user-specific tax assumptions in versioned files. All real statements stay on your machine.

## License

TBD
