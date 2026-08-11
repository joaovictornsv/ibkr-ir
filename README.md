# ibkr-ir

Generate an HTML guide to help Brazilian residents fill **IRPF** fields from an Interactive Brokers **Activity Statement** (CSV).

The report covers **Bens e Direitos**, **Rendimentos Isentos** (dividends), **ganho de capital** (average-cost method in BRL), and informative checks for **DARF**, **GCAP**, and **CBE**. It is **not tax advice** — always review with a qualified accountant.

## License

[MIT](LICENSE) — permissive open source. You can use, modify, and distribute the code freely, including in commercial projects, as long as the license notice is preserved.

## Quick start (download — no Python)

If you only want to generate your IRPF guide and do not want to install Python:

1. Open **[Releases](https://github.com/joaovictornsv/ibkr-ir/releases)** and download the file for your system:
   - **Windows:** `ibkr-ir-windows-x86_64` → rename to `ibkr-ir.exe` (optional)
   - **macOS (Apple Silicon):** `ibkr-ir-macos-arm64`
   - **Linux:** `ibkr-ir-linux-x86_64`
2. Export your IBKR **Activity Statement** as CSV (see [Exporting the statement](#exporting-the-statement)).
3. Open a terminal in the folder where you saved the file and run (adjust paths):

**Windows (PowerShell or CMD)**

```text
ibkr-ir.exe --year 2025 --statement C:\Users\You\Downloads\activity_statement.csv
```

**macOS / Linux**

```bash
chmod +x ibkr-ir-macos-arm64   # once, after download
./ibkr-ir-macos-arm64 --year 2025 --statement ~/Downloads/activity_statement.csv
```

4. Open `output/irpf-2025.html` in your browser (created in the folder where you ran the command).

**macOS:** the first run may show a security warning because the binary is not signed. Use **System Settings → Privacy & Security → Open Anyway**, or run `xattr -cr ./ibkr-ir-macos-arm64` once.

**Internet:** required on first run to fetch [PTAX](https://www.bcb.gov.br/estabilidadefinanceira/historicocotacoes) rates; they are cached in `cache/ptax` next to where you run the program.

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

Detailed step-by-step instructions (in Portuguese) are also included in the generated HTML report.

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
- Export guide and glossary for non-experts

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
