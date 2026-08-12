# ibkr-ir

Generate an HTML guide to help Brazilian residents fill **IRPF** fields from an Interactive Brokers **Activity Statement** (CSV).

The report covers **Bens e Direitos**, **Rendimentos Isentos** (dividends), **ganho de capital** (average-cost method in BRL), and informative checks for **DARF**, **GCAP**, and **CBE**. It is **not tax advice** — always review with a qualified accountant.

## Summary

- [License](#license)
- [Recommended folder (especially for non-developers)](#recommended-folder-especially-for-non-developers)
- [Quick start (download — no Python)](#quick-start-download--no-python)
- [Quick start (from source)](#quick-start-from-source)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Try with the sample file (no real data)](#try-with-the-sample-file-no-real-data)
- [Exporting the statement](#exporting-the-statement)
- [Usage](#usage)
  - [Basic command](#basic-command)
  - [Annual workflow](#annual-workflow)
  - [Optional: prior-year values without JSON](#optional-prior-year-values-without-json)
- [Output](#output)
- [What the report includes](#what-the-report-includes)
- [Privacy](#privacy)
- [Development](#development)
  - [Building binaries (maintainers)](#building-binaries-maintainers)
- [Disclaimer](#disclaimer)

## License

[MIT](LICENSE) — permissive open source. You can use, modify, and distribute the code freely, including in commercial projects, as long as the license notice is preserved.

## Recommended folder (especially for non-developers)

Create a **dedicated folder** for this project and keep everything related to your IRPF filing there — not mixed with Downloads or other files.

**Put in that folder:**

- The downloaded **program** (`ibkr-ir.exe` on Windows, or `ibkr-ir-macos-arm64` / `ibkr-ir-linux-x86_64`)
- Your IBKR **Activity Statement** CSV exports
- The generated **reports** and **cache** (created automatically when you run the program)

**Why?** When you run the program, it creates an `output/` folder (HTML report + JSON for next year) and a `cache/` folder (PTAX exchange rates) **in the folder where you run the command**. Keeping the binary, CSVs, output, and cache in one place makes it easier to find your files year after year and avoids clutter elsewhere.

**Example layout** (after your first run):

```text
ibkr-ir/                          ← your dedicated folder
├── ibkr-ir-macos-arm64           ← program (or ibkr-ir.exe on Windows)
├── statement_2025.csv            ← IBKR export
├── output/
│   ├── irpf-2025.html            ← your IRPF guide (open in browser)
│   ├── irpf-2025.json            ← saved for next year's prior values
│   └── guia-ibkr-ir.html         ← usage guide (copied here on first run)
└── cache/
    └── ptax/                     ← cached PTAX rates (reused on later runs)
```

**Tip:** Open the terminal *inside* this folder before running the program (see [Quick start](#quick-start-download--no-python) below).

## Quick start (download — no Python)

If you only want to generate your IRPF guide and do not want to install Python:

1. Create your dedicated folder (see [Recommended folder](#recommended-folder-especially-for-non-developers)) and download the program into it from **[Releases](https://github.com/joaovictornsv/ibkr-ir/releases)**:
   - **Windows:** `ibkr-ir-windows-x86_64` → rename to `ibkr-ir.exe` (optional)
   - **macOS (Apple Silicon):** `ibkr-ir-macos-arm64`
   - **Linux:** `ibkr-ir-linux-x86_64`
2. **Read the usage guide first:** open [`docs/guia-ibkr-ir.html`](docs/guia-ibkr-ir.html) in your browser (also copied to `output/` in your project folder on first run).
3. Export your IBKR **Activity Statement** as CSV and save it in the same folder (see [Exporting the statement](#exporting-the-statement)).
4. Open a terminal **in your project folder** and run (adjust the CSV name if needed):

**Windows (PowerShell or CMD)**

```text
ibkr-ir.exe --year 2025 --statement statement_2025.csv
```

**macOS / Linux**

```bash
chmod +x ibkr-ir-macos-arm64   # once, after download
./ibkr-ir-macos-arm64 --year 2025 --statement statement_2025.csv
```

5. Open `output/irpf-2025.html` in your browser (inside your project folder).

**macOS:** the first run may show a security warning because the binary is not signed. Use **System Settings → Privacy & Security → Open Anyway**, or run `xattr -cr ./ibkr-ir-macos-arm64` once.

**Internet:** required on first run to fetch [PTAX](https://www.bcb.gov.br/estabilidadefinanceira/historicocotacoes) rates; they are cached in `cache/ptax` inside your project folder.

## Quick start (from source)

Developers and contributors can run from Python instead:

### Requirements

- **Python 3.10+**
- Internet access on first run (PTAX; cached locally)

### Installation

```bash
git clone https://github.com/joaovictornsv/ibkr-ir.git
cd ibkr-ir

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

1. Export your IBKR **Activity Statement** as CSV (see [Exporting the statement](#exporting-the-statement)).
2. Run:

```bash
python generate.py \
  --year 2025 \
  --statement /path/to/your/activity_statement.csv
```

3. Open `output/irpf-2025.html` in your browser.

### Try with the sample file (no real data)

```bash
python generate.py \
  --year 2025 \
  --statement examples/sample_statement.csv
```

## Exporting the statement

Use the IBKR **Activity Statement** — not the Transactions export.

1. Log in to **Client Portal** → **Performance & Reports** → **Statements** → **Activity**
2. Select your account
3. **Period:** January 1 – December 31 of the target year
4. **Format:** CSV (not PDF)
5. Download the file

Detailed step-by-step instructions (in Portuguese) are in [`docs/guia-ibkr-ir.html`](docs/guia-ibkr-ir.html) — read that before your first run.

## Usage

### Basic command

```bash
python generate.py --year YEAR --statement PATH_TO_CSV
```

| Argument | Required | Description |
|---|---|---|
| `--year` | Yes | Tax year (e.g. `2025`) |
| `--statement` | Yes | Path to your Activity Statement CSV |
| `--output` | No | HTML output path (default: `output/irpf-{year}.html`) |
| `--prior-statement` | No | Prior-year Activity Statement for 31/12 prior values |
| `--prior-year-json` | No | JSON from a previous run (default: `output/irpf-{year-1}.json`) |
| `--ptax-cache` | No | PTAX cache directory (default: `cache/ptax`) |

### Annual workflow

**First year on IBKR**

```bash
python generate.py --year 2025 --statement ~/Downloads/statement_2025.csv
```

Prior-year values in Bens e Direitos are set to R$ 0 when the statement shows `Prior Total = 0` in Net Asset Value.

**Following years**

Run again for the new year. If `output/irpf-2024.json` exists from last year's run, prior values are loaded automatically:

```bash
python generate.py --year 2025 --statement ~/Downloads/statement_2025.csv
```

**Preview during the year**

You can export and run anytime with a partial period (e.g. Jan 1 – today). Values are provisional — re-export with the full calendar year before filing.

**Final IRPF filing**

In January, export the statement for the complete year (Jan 1 – Dec 31) and run again:

```bash
python generate.py --year 2025 --statement ~/Downloads/statement_2025_final.csv
```

### Optional: prior-year values without JSON

If you do not have last year's JSON sidecar:

```bash
python generate.py \
  --year 2025 \
  --statement ~/Downloads/statement_2025.csv \
  --prior-statement ~/Downloads/statement_2024.csv
```

## Output

| File | Description |
|---|---|
| `output/irpf-{year}.html` | Step-by-step IRPF guide with copy buttons (Portuguese) |
| `output/irpf-{year}.json` | BRL position values for next year's prior-value carry-forward |

Both paths are **gitignored** by default — they may contain personal data.

## What the report includes

- **Bens e Direitos** (Grupo 04 / Código 03) — stocks abroad + USD cash
- **Rendimentos Isentos** (Código 05) — foreign dividends × PTAX
- **Ganho de capital** — average cost in BRL, per sale
- **DARF check** — monthly R$ 35,000 sale-proceeds threshold
- **CBE check** — USD 100k NAV / remittance threshold (informative)
- Export guide and glossary for non-experts (see `docs/guia-ibkr-ir.html`)

## Privacy

- **Never commit** your Activity Statement CSV, `output/`, or `cache/` — they contain account and portfolio data.
- This repository is generic: no real account numbers, names, or user-specific assumptions in versioned files.
- The tool runs **locally**; your statement is not uploaded anywhere (except PTAX rates fetched from BCB).

## Development

```bash
pip install -r requirements.txt pytest
PYTHONPATH=. pytest tests/ -v
```

See [docs/PLAN.md](docs/PLAN.md) for architecture and design constraints.

### Building binaries (maintainers)

```bash
./scripts/build-binary.sh
```

To publish downloads for all platforms, tag a release (GitHub Actions builds Windows, macOS, and Linux):

```bash
git tag v0.1.0
git push origin v0.1.0
```

Artifacts appear under **Releases** on GitHub. Binaries are not committed to the repo (too large; platform-specific).

## Disclaimer

This software is provided for informational purposes only. Tax rules change, individual situations vary, and partial-year values are provisional. The authors are not responsible for filing errors. Consult a qualified tax professional before submitting your IRPF or related obligations (DARF, GCAP, CBE).
