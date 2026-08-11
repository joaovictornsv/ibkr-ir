"""Generate the IRPF HTML guide report."""

from __future__ import annotations

import html
from decimal import Decimal
from pathlib import Path

from .calculator import IrpfReport


def _fmt_brl(value: Decimal) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_usd(value: Decimal) -> str:
    return f"USD {value:,.2f}"


def _copy_button(text: str, button_id: str) -> str:
    escaped = html.escape(text)
    return (
        f'<button type="button" class="copy" data-copy="{escaped}" '
        f'id="{button_id}">Copiar</button>'
    )


def generate_html(report: IrpfReport) -> str:
    bens_rows = []
    for i, item in enumerate(report.bens_direitos):
        bens_rows.append(
            "<tr>"
            f"<td>{html.escape(item.symbol)}</td>"
            f"<td>{html.escape(item.country)}</td>"
            f"<td>{item.quantity}</td>"
            f"<td>{_fmt_usd(item.value_usd)}</td>"
            f"<td>{_fmt_brl(item.value_brl)}</td>"
            f"<td>{_fmt_brl(item.prior_brl)}</td>"
            f"<td>{html.escape(item.description)} {_copy_button(item.description, f'bd-{i}')}</td>"
            "</tr>"
        )

    div_rows = []
    for i, item in enumerate(report.dividends):
        div_rows.append(
            "<tr>"
            f"<td>{html.escape(item.symbol)}</td>"
            f"<td>{item.date.isoformat()}</td>"
            f"<td>{_fmt_usd(item.amount_usd)}</td>"
            f"<td>{item.ptax}</td>"
            f"<td>{_fmt_brl(item.amount_brl)}</td>"
            f"<td>{_copy_button(_fmt_brl(item.amount_brl), f'div-{i}')}</td>"
            "</tr>"
        )

    gain_rows = []
    for sale in report.capital_gains:
        gain_rows.append(
            "<tr>"
            f"<td>{html.escape(sale.symbol)}</td>"
            f"<td>{sale.date.isoformat()}</td>"
            f"<td>{sale.quantity}</td>"
            f"<td>{_fmt_usd(sale.proceeds_usd)}</td>"
            f"<td>{_fmt_brl(sale.proceeds_brl)}</td>"
            f"<td>{_fmt_brl(sale.cost_brl)}</td>"
            f"<td>{_fmt_brl(sale.gain_brl)}</td>"
            "</tr>"
        )

    monthly_rows = []
    for check in report.monthly_sales:
        status = "Sim" if check.needs_darf else "Não"
        monthly_rows.append(
            "<tr>"
            f"<td>{check.year_month}</td>"
            f"<td>{_fmt_brl(check.proceeds_brl)}</td>"
            f"<td><strong>{status}</strong></td>"
            "</tr>"
        )

    validation = "".join(f"<li>{html.escape(n)}</li>" for n in report.validation_notes)
    cbe = report.cbe
    cbe_status = "Sim" if cbe and cbe.cbe_required else "Não"
    cbe_reason = html.escape(cbe.reason if cbe else "")

    prior_help = (
        "Valores de 31/12 do ano anterior carregados automaticamente do JSON da execução anterior."
        if report.prior_year_source == "json"
        else "Primeiro ano na IBKR — valores anteriores zerados (Prior Total = 0 no extrato)."
        if report.is_first_ibkr_year
        else "Valores anteriores não encontrados — use --prior-statement ou --prior-year-json."
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IRPF {report.year} — Guia IBKR</title>
  <style>
    :root {{
      --bg: #f4f6f9;
      --card: #ffffff;
      --text: #1a2332;
      --muted: #5c6578;
      --accent: #2563eb;
      --accent-hover: #1d4ed8;
      --border: #e2e8f0;
      --warn: #b45309;
      --warn-bg: #fef3c7;
      --ok: #15803d;
      --ok-bg: #dcfce7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
    h1, h2, h3 {{ line-height: 1.2; }}
    h1 {{ font-size: 1.9rem; margin-bottom: 0.25rem; }}
    .subtitle {{ color: var(--muted); margin-bottom: 2rem; }}
    section {{
      background: var(--card);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.25rem;
      border: 1px solid var(--border);
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ padding: 0.55rem 0.45rem; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    ol, ul {{ padding-left: 1.25rem; }}
    .disclaimer {{ border-left: 4px solid var(--warn); padding-left: 1rem; color: var(--muted); background: var(--warn-bg); border-radius: 0 8px 8px 0; padding: 0.75rem 1rem; }}
    .badge {{ display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px; font-size: 0.85rem; }}
    .badge.warn {{ background: var(--warn-bg); color: var(--warn); }}
    .badge.ok {{ background: var(--ok-bg); color: var(--ok); }}
    button.copy {{
      background: #f1f5f9;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.2rem 0.55rem;
      cursor: pointer;
      font-size: 0.8rem;
    }}
    button.copy:hover {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
    code {{ background: #f1f5f9; padding: 0.1rem 0.35rem; border-radius: 4px; border: 1px solid var(--border); font-size: 0.9em; }}
  </style>
</head>
<body>
<main>
  <h1>IRPF {report.year} — Guia a partir do Activity Statement IBKR</h1>
  <p class="subtitle">Data de valoração: {report.valuation_date.strftime('%d/%m/%Y')} · {prior_help}</p>

  <section class="disclaimer">
    <p><strong>Aviso:</strong> este relatório é apenas informativo e não constitui assessoria fiscal.
    Regras mudam; valores parciais do ano são provisórios. Confira tudo com um contador.</p>
  </section>

  <section>
    <h2>1. Como exportar o Activity Statement na IBKR</h2>
    <ol>
      <li>Acesse o <strong>Client Portal</strong> ou <strong>Trader Workstation → Reports</strong></li>
      <li><strong>Performance &amp; Reports</strong> → <strong>Statements</strong> → <strong>Activity</strong></li>
      <li>Selecione a conta (ex.: <code>U12345678</code>)</li>
      <li><strong>Período:</strong> 1º de janeiro a 31 de dezembro de {report.year}</li>
      <li><strong>Formato:</strong> CSV (não PDF)</li>
      <li>Baixe o arquivo e execute: <code>python generate.py --year {report.year} --statement /caminho/statement.csv</code></li>
    </ol>
    <p><strong>Prévia:</strong> pode exportar a qualquer momento durante o ano. <strong>IRPF final:</strong> reexporte em janeiro com o ano completo.</p>
  </section>

  <section>
    <h2>2. Como obter os valores</h2>
    <ul>
      <li><strong>Valores atuais:</strong> Open Positions + Cash Report × PTAX de {report.valuation_date.strftime('%d/%m/%Y')}</li>
      <li><strong>Ano anterior:</strong> JSON da execução anterior, ou Prior Total = 0 no NAV (primeiro ano)</li>
      <li><strong>Preços de mercado:</strong> vêm do próprio extrato — sem API externa de cotações</li>
    </ul>
  </section>

  <section>
    <h2>3. Passo a passo IRPF</h2>
    <h3>Bens e Direitos — Grupo 04 / Código 03</h3>
    <p>Declare ações no exterior e caixa em USD. Copie a discriminação de cada linha.</p>
    <table>
      <thead>
        <tr><th>Ativo</th><th>País</th><th>Qtd</th><th>USD</th><th>BRL 31/12</th><th>BRL ano ant.</th><th>Discriminação</th></tr>
      </thead>
      <tbody>
        {''.join(bens_rows) if bens_rows else '<tr><td colspan="7">Nenhuma posição em ações.</td></tr>'}
        <tr>
          <td colspan="4"><strong>Caixa USD</strong></td>
          <td colspan="2">{_fmt_brl(report.cash_brl)}</td>
          <td>Interactive Brokers LLC - EUA - Saldo em conta USD {_copy_button(f'Interactive Brokers LLC - EUA - Saldo em conta USD - {_fmt_brl(report.cash_brl)}', 'cash')}</td>
        </tr>
      </tbody>
    </table>

    <h3>Rendimentos Isentos — Código 05 (lucros/dividendos do exterior)</h3>
    <table>
      <thead>
        <tr><th>Ativo</th><th>Data</th><th>USD</th><th>PTAX</th><th>BRL</th><th></th></tr>
      </thead>
      <tbody>
        {''.join(div_rows) if div_rows else '<tr><td colspan="6">Nenhum dividendo no ano.</td></tr>'}
        <tr><td colspan="4"><strong>Total</strong></td><td>{_fmt_brl(report.total_dividends_brl)}</td><td></td></tr>
      </tbody>
    </table>

    <h3>Ganho de capital (custo médio em BRL)</h3>
    <table>
      <thead>
        <tr><th>Ativo</th><th>Data</th><th>Qtd</th><th>Proventos USD</th><th>Proventos BRL</th><th>Custo BRL</th><th>Ganho BRL</th></tr>
      </thead>
      <tbody>
        {''.join(gain_rows) if gain_rows else '<tr><td colspan="7">Nenhuma venda no ano.</td></tr>'}
        <tr><td colspan="6"><strong>Total ganho</strong></td><td>{_fmt_brl(report.total_capital_gain_brl)}</td></tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>4. Tabelas de auditoria</h2>
    {f'<ul>{validation}</ul>' if validation else '<p>Nenhuma divergência detectada.</p>'}
  </section>

  <section>
    <h2>5. Ganho de capital — verificação mensal DARF (R$ 35.000)</h2>
    <table>
      <thead><tr><th>Mês</th><th>Proventos de venda (BRL)</th><th>Precisa DARF?</th></tr></thead>
      <tbody>
        {''.join(monthly_rows) if monthly_rows else '<tr><td colspan="3">Sem vendas no ano.</td></tr>'}
      </tbody>
    </table>
  </section>

  <section>
    <h2>6. Obrigações relacionadas: DARF, GCAP e CBE</h2>
    <table>
      <thead><tr><th>Obrigação</th><th>Este relatório</th><th>Não faz</th></tr></thead>
      <tbody>
        <tr>
          <td><strong>DARF</strong></td>
          <td>Verifica limite mensal de R$ 35.000 em vendas</td>
          <td>Emitir ou pagar DARF</td>
        </tr>
        <tr>
          <td><strong>GCAP</strong></td>
          <td>Lista ganhos por venda com campos sugeridos</td>
          <td>Preencher ou transmitir GCAP</td>
        </tr>
        <tr>
          <td><strong>CBE</strong></td>
          <td>
            <span class="badge {'warn' if cbe and cbe.cbe_required else 'ok'}">CBE necessária? {cbe_status}</span>
            <br><small>{cbe_reason}</small>
          </td>
          <td>Gerar XML Bacen</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section>
    <h2>7. JSON para o próximo ano</h2>
    <p>Um arquivo <code>irpf-{report.year}.json</code> foi salvo em <code>output/</code> com os valores em BRL de 31/12 para carregar automaticamente no IRPF de {report.year + 1}.</p>
    <p class="disclaimer">Não commite esse arquivo — pode conter dados pessoais.</p>
  </section>
</main>
<script>
document.querySelectorAll('button.copy').forEach((btn) => {{
  btn.addEventListener('click', async () => {{
    const text = btn.getAttribute('data-copy') || '';
    await navigator.clipboard.writeText(text);
    const original = btn.textContent;
    btn.textContent = 'Copiado!';
    setTimeout(() => {{ btn.textContent = original; }}, 1200);
  }});
}});
</script>
</body>
</html>
"""


def write_report(report: IrpfReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_html(report), encoding="utf-8")
