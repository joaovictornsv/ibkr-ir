# IBKR Activity Statement → IRPF Annual Report

## Public repository constraints

This project is **public and generic**. Versioned code and docs must not include:

- Real account IDs, names, or broker exports
- Hard-coded paths to a specific user's machine
- Assumptions tied to one person's portfolio ("your Aug sells", etc.)

**Rules for implementation:**

| Area | Rule |
|---|---|
| Sample data | Optional anonymized fixtures under `examples/` only; real CSVs stay local and gitignored |
| CLI defaults | No default `--statement` path; user must pass their file |
| HTML output | Uses data from the user's run only; never embed repo author PII |
| JSON sidecar | Written to gitignored `output/`; may contain user data — never commit |
| Tests | Use synthetic/minimal CSV snippets in tests, not real statements |
| Docs | Generic account placeholder (e.g. `U12345678`) in export instructions |

---

## Single input: Activity Statement only

The script accepts **one file type only**: IBKR **Activity Statement** (CSV).

| Input | Supported? |
|---|---|
| Activity Statement CSV | **Yes — required** |
| Transactions CSV | **No** |
| External price APIs | **No** — market values from Open Positions in the statement |
| Prior-year Activity Statement | Optional (`--prior-statement`) when prior-year JSON is missing |

**Annual workflow:**

1. Export Activity Statement from IBKR (see below)
2. Run: `python generate.py --year YYYY --statement /path/to/statement.csv`
3. Open `output/irpf-YYYY.html` and copy values into IRPF

---

## How to export the Activity Statement (README + HTML report)

Step-by-step (Portuguese in generated HTML):

1. Log in to **IBKR Client Portal** or **Trader Workstation → Reports**
2. **Performance & Reports** → **Statements** → **Activity**
3. Select your account
4. **Period:** January 1 – December 31 of the target year
5. **Format:** CSV (not PDF)
6. Download and pass to `--statement`

**When to export:**

- **Preview:** anytime during the year (provisional values)
- **Final IRPF:** re-export in January with period through Dec 31

**Required sections in the CSV:** `Open Positions`, `Trades`, `Dividends`, `Withholding Tax`, `Cash Report`, `Net Asset Value`, `Change in NAV`

---

## Activity Statement sections used

| Section | IRPF use |
|---|---|
| **Open Positions** | Bens e Direitos — `Quantity`, `Close Price`, `Value` |
| **Trades** | Ganho de capital — proceeds, fees, basis |
| **Dividends** | Rendimentos isentos |
| **Withholding Tax** | Informative (paired with dividends) |
| **Deposits & Withdrawals** | Remessas / CBE threshold check |
| **Cash Report** | USD cash in Bens e Direitos |
| **Net Asset Value** | `Prior Total = 0` → first-year prior values R$ 0 |
| **Change in NAV** | Validation cross-check |
| **Financial Instrument Information** | ISIN for discriminação |

**External (automatic):** PTAX from [BCB Olinda API](https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/swagger-ui3)

---

## Automatic vs manual (prior-year & year-end)

### Automatic (default)

- **Current year values:** `Open Positions → Value × PTAX` on statement end date
- **Prior year (first IBKR year):** `Net Asset Value → Prior Total = 0` → R$ 0
- **Prior year (later):** `output/irpf-{year-1}.json` from previous run

### Manual (documented in HTML when needed)

- **Year-end values:** re-export Activity Statement with full calendar year — no manual price entry in the script
- **Prior year:** `--prior-statement` (prior-year Activity Statement) or copy from last IRPF declaration (instructions only; not stored in repo)

---

## IRPF sections computed

### 1. Bens e Direitos

- Grupo 04 / Código 03 — ações no exterior + cash USD
- Discriminação: `Interactive Brokers LLC - {country} - {TICKER} - {N} ações` (+ ISIN when available)

### 2. Rendimentos Isentos e Não Tributáveis

- Código 05 — lucros/dividendos do exterior (gross × PTAX on payment date)

### 3. Ganho de capital

- Custo médio in BRL per Brazilian PF rules
- Monthly R$ 35,000 sale-proceeds check → "Precisa DARF? Sim/Não"

### 4. Informative

- CBE threshold check (USD 100k / USD 1M rules)
- DARF / GCAP / CBE disclaimers (see below)

---

## HTML report structure

1. Capa + link para o guia de uso (`docs/guia-ibkr-ir.html`)
2. Avisos dinâmicos (período parcial, primeiro ano na IBKR, valores do ano anterior)
3. Passo a passo IRPF (copy buttons)
4. Audit tables (USD, PTAX, BRL)
5. Ganho de capital worksheet
6. **Obrigações relacionadas: DARF, GCAP e CBE**
7. JSON sidecar note (next-year carry-forward)

Static usage instructions (export guide, glossary, how to run) live in **`docs/guia-ibkr-ir.html`** so users can read them before the first run.

---

## DARF, GCAP, CBE disclaimers (always in HTML)

| Obrigação | Report does | Report does NOT |
|---|---|---|
| **DARF** | Monthly R$35k check + estimated tax | Issue or pay DARF |
| **GCAP** | Per-sale gains + suggested fields | Fill or transmit GCAP |
| **CBE** | "CBE necessária? Sim/Não" from NAV/deposits | Generate Bacen XML |

General: not tax advice; rules change; PTAX-dependent; partial-year values provisional.

---

## Project layout

```
ibkr-ir/
├── docs/
│   └── PLAN.md
├── src/
│   ├── parser.py
│   ├── ptax.py
│   ├── calculator.py
│   ├── prices.py
│   └── report.py
├── examples/          # optional anonymized samples only
├── cache/             # gitignored PTAX cache
├── output/            # gitignored HTML + JSON
├── generate.py
├── README.md
└── .gitignore
```

**CLI:**

```bash
python generate.py \
  --year 2026 \
  --statement /path/to/statement.csv \
  --output output/irpf-2026.html
```

Optional: `--prior-statement`, `--prior-year-json`, `--ptax-cache`

---

## Parser rules

- Parse by section name (first CSV column)
- Trades: `DataDiscriminator = Order` only; custo médio for BRL gains (not IBKR FIFO)
- Open Positions: `Summary` stock rows + Forex Balances for cash
- Skip Forex category in Trades for stock gains
- Filter trades/dividends by calendar year; positions use statement end date
- Validate against Change in NAV

---

## Dependencies

- Python 3 + `requests` (PTAX)
- No API keys

---

## Validation (local only — do not commit real CSV)

Run against a **local** Activity Statement (gitignored):

- Open Positions + Cash Report reconcile with Change in NAV
- Prior Total = 0 handled for new accounts
- PTAX on all dates + statement end date
- HTML includes export guide + DARF/GCAP/CBE disclaimers

---

## Implementation todos

- [x] Activity Statement parser + year filter
- [x] PTAX module + cache
- [x] Calculator (custo médio, dividends, Bens e Direitos, cash)
- [x] Prior-year resolver (Prior Total / JSON / optional prior statement)
- [x] HTML report generator
- [ ] Local validation with user's private export (outside repo)
