"""Generate the IRPF HTML guide report."""

from __future__ import annotations

import html
import shutil
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from .calculator import CbeCheck, IrpfReport
from .report_styles import REPORT_CSS

GUIDE_FILENAME = "guia-ibkr-ir.html"


def guide_source_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "docs" / GUIDE_FILENAME
    return Path(__file__).resolve().parent.parent / "docs" / GUIDE_FILENAME


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


def _prior_year_note(report: IrpfReport) -> str:
    year = report.year
    if report.is_first_ibkr_year:
        return """
        <div class="guide-note">
          <strong>Primeiro ano na IBKR:</strong> como você abriu a conta neste ano, a coluna
          &ldquo;valor em 31/12 do ano anterior&rdquo; no IRPF deve ser <strong>R$ 0,00</strong>
          para todos os ativos. O extrato confirma isso quando o campo <em>Prior Total</em> no
          NAV é zero.
        </div>"""
    if report.prior_year_source == "json":
        return """
        <div class="guide-note">
          <strong>Valores do ano anterior:</strong> foram carregados automaticamente do arquivo
          JSON gerado na declaração do ano passado. Você não precisa buscar esses números
          manualmente.
        </div>"""
    return """
        <div class="guide-note">
          <strong>Atenção — valores do ano anterior não encontrados.</strong> Para preencher a
          coluna &ldquo;valor em 31/12/{prev_year}&rdquo; no IRPF, você pode: (1) exportar o
          Activity Statement de {prev_year} e rodar este programa com
          <code>--prior-statement</code>, ou (2) copiar os valores da sua declaração de IRPF
          de {prev_year}, ou (3) usar o JSON de uma execução anterior com
          <code>--prior-year-json</code>.
        </div>""".format(prev_year=year - 1)


def _section_situation_notes(report: IrpfReport) -> str:
    is_partial_year = report.valuation_date != date(report.year, 12, 31)
    notes: list[str] = []

    if is_partial_year:
        notes.append(
            f"<div class=\"guide-note\"><strong>Período parcial:</strong> este extrato cobre até "
            f"{report.valuation_date.strftime('%d/%m/%Y')}, não o ano completo. Os valores são "
            f"<strong>provisórios</strong> — para o IRPF final, exporte novamente com período de "
            f"1º de janeiro a 31 de dezembro de {report.year}.</div>"
        )

    notes.append(_prior_year_note(report))
    return "\n".join(notes)


def _section_obligations_guide(
    report: IrpfReport,
    cbe: CbeCheck | None,
    cbe_status: str,
    cbe_reason: str,
) -> str:
    badge_class = "warn" if cbe and cbe.cbe_required else "ok"
    nav_usd = _fmt_usd(cbe.nav_usd) if cbe else "—"
    deposits_usd = _fmt_usd(cbe.deposits_usd) if cbe else "—"

    return f"""
    <p>Além de preencher o IRPF, investidores no exterior podem ter <strong>outras obrigações
    legais</strong>. Este relatório ajuda a identificar se você precisa se preocupar com cada
    uma, mas <strong>não substitui</strong> o envio oficial dessas declarações.</p>

    <div class="obligation-card">
      <h4>DARF — Documento de Arrecadação de Receitas Federais</h4>
      <p><strong>O que é:</strong> o boleto/guia para pagar imposto de renda sobre ganho de
      capital na venda de ações. É diferente do IRPF anual — é um pagamento
      <strong>mensal</strong> quando você vende ações com lucro.</p>
      <p><strong>Quando pode ser necessário:</strong> se no mesmo mês civil você vende ações
      com lucro <strong>e</strong> o total vendido (em reais) ultrapassa
      <strong>R$ 35.000</strong>. Veja a seção 3 deste relatório para a verificação mês a mês.</p>
      <p><strong>O que este relatório faz:</strong> calcula o total de vendas por mês em reais
      e indica &ldquo;Precisa DARF? Sim/Não&rdquo;.</p>
      <p><strong>O que este relatório <em>não</em> faz:</strong> emitir a DARF, calcular o
      imposto exato (15% sobre o ganho) ou efetuar o pagamento. Isso é feito no site da
      Receita Federal ou com ajuda de um contador.</p>
    </div>

    <div class="obligation-card">
      <h4>GCAP — Programa de Apuração de Ganhos de Capital</h4>
      <p><strong>O que é:</strong> programa da Receita Federal usado para declarar e calcular
      o imposto sobre <strong>ganhos de capital</strong> (lucro na venda de ações). É
      necessário quando você tem vendas com lucro que exigem pagamento via DARF.</p>
      <p><strong>Quando pode ser necessário:</strong> quando há vendas com ganho de capital
      tributável no mês — geralmente junto com a DARF do mesmo mês.</p>
      <p><strong>O que este relatório faz:</strong> lista cada venda com proventos, custo e
      ganho em reais (seção 1), que servem como base para preencher o GCAP.</p>
      <p><strong>O que este relatório <em>não</em> faz:</strong> preencher ou transmitir o
      GCAP. Você deve usar o programa GCAP disponível no site da Receita Federal.</p>
    </div>

    <div class="obligation-card">
      <h4>CBE — Capitais Brasileiros no Exterior</h4>
      <p><strong>O que é:</strong> declaração anual ao Banco Central (Bacen) informando
      investimentos e ativos mantidos fora do Brasil. É separada do IRPF — enviada ao Bacen,
      não à Receita Federal.</p>
      <p><strong>Quando pode ser necessário:</strong> se no 31 de dezembro você tem mais de
      <strong>USD 100.000</strong> investidos no exterior, ou se enviou mais de
      <strong>USD 100.000</strong> ao exterior no ano (remessas). Há também obrigação
      trimestral para valores acima de USD 1 milhão.</p>
      <p><strong>Sua situação neste extrato:</strong><br>
      <span class="badge {badge_class}">CBE necessária? {cbe_status}</span><br>
      <small>{cbe_reason}</small><br>
      <small>Patrimônio estimado: {nav_usd} · Remessas no ano: {deposits_usd}</small></p>
      <p><strong>O que este relatório faz:</strong> estima se você pode precisar declarar a
      CBE, usando o valor total da conta e os depósitos do extrato.</p>
      <p><strong>O que este relatório <em>não</em> faz:</strong> gerar o arquivo XML da CBE
      nem enviar ao Bacen. A declaração é feita no sistema SISCOSERV do Banco Central.</p>
    </div>

    <div class="guide-note">
      <strong>Resumo:</strong> IRPF (anual, Receita Federal) · DARF + GCAP (mensal, quando há
      vendas com lucro acima do limite) · CBE (anual ao Bacen, quando patrimônio ou remessas
      ultrapassam USD 100 mil). São obrigações diferentes — consulte um contador se tiver
      dúvidas sobre qual se aplica ao seu caso.
    </div>
    """


def _section_json_guide(report: IrpfReport) -> str:
    year = report.year
    next_year = year + 1
    val_date = report.valuation_date.strftime("%d/%m/%Y")
    return f"""
    <p>Quando você roda este programa, ele salva um arquivo <code>irpf-{year}.json</code>
    junto com o HTML. Esse arquivo guarda os valores em reais das suas posições para
    facilitar a declaração do <strong>próximo ano</strong>.</p>

    <h4>Por que isso é importante?</h4>
    <p>No IRPF, a ficha <strong>Bens e Direitos</strong> pede dois valores para cada ativo:</p>
    <ul>
      <li><strong>Valor em {val_date}</strong> (ano atual) — o que você tem hoje</li>
      <li><strong>Valor em 31/12/{year}</strong> (ano anterior, na declaração de {next_year})
      — o que você tinha no fim do ano passado</li>
    </ul>
    <p>O JSON guarda os valores de <strong>{val_date}</strong> em reais. Na declaração de
    {next_year}, o programa lê esse arquivo automaticamente e preenche a coluna
    &ldquo;valor em 31/12/{year}&rdquo; — você não precisa anotar manualmente.</p>

    <h4>Onde o arquivo fica?</h4>
    <p><code>output/irpf-{year}.json</code> — na mesma pasta do relatório HTML.</p>

    <h4>Como usar no ano que vem</h4>
    <ol class="steps">
      <li data-step="1">Em janeiro de {next_year}, exporte o Activity Statement de {year}
        completo (1º de janeiro a 31 de dezembro de {year}).</li>
      <li data-step="2">Rode o programa normalmente:
        <code>ibkr-ir --year {next_year} --statement extrato.csv</code></li>
      <li data-step="3">O programa encontra <code>output/irpf-{year}.json</code>
        automaticamente e usa os valores salvos como &ldquo;ano anterior&rdquo;.</li>
      <li data-step="4">Se o JSON não existir, use
        <code>--prior-year-json output/irpf-{year}.json</code> para indicar o caminho
        manualmente.</li>
    </ol>

    <div class="disclaimer">
      <strong>Privacidade:</strong> o arquivo JSON contém valores das suas posições e pode
      incluir dados da sua conta. <strong>Não commite</strong> em repositórios Git públicos,
      não envie por e-mail e não compartilhe. Mantenha apenas no seu computador, na pasta
      <code>output/</code> (que já está configurada para ser ignorada pelo Git neste projeto).
    </div>
    """


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

    situation_notes = _section_situation_notes(report)
    section_obligations = _section_obligations_guide(report, cbe, cbe_status, cbe_reason)
    section_json = _section_json_guide(report)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IRPF {report.year} — Guia IBKR</title>
  <style>{REPORT_CSS}</style>
</head>
<body>
<main>
  <h1>IRPF {report.year} — Guia a partir do Activity Statement IBKR</h1>
  <p class="subtitle">Data de valoração: {report.valuation_date.strftime('%d/%m/%Y')} · {prior_help}</p>

  <div class="guide-link">
    <strong>Primeira vez usando o programa?</strong> Leia o
    <a href="{GUIDE_FILENAME}">guia de uso ({GUIDE_FILENAME})</a> — ele explica como exportar
    o extrato da IBKR, rodar o programa e entender os termos. Este relatório contém apenas os
    valores calculados a partir do seu extrato.
  </div>

  <section class="disclaimer">
    <p><strong>Aviso:</strong> este relatório é apenas informativo e não constitui assessoria fiscal.
    Regras mudam; valores parciais do ano são provisórios. Confira tudo com um contador.</p>
  </section>

  {situation_notes}

  <section>
    <h2>1. Passo a passo IRPF</h2>
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
    <h2>2. Tabelas de auditoria</h2>
    {f'<ul>{validation}</ul>' if validation else '<p>Nenhuma divergência detectada.</p>'}
  </section>

  <section>
    <h2>3. Ganho de capital — verificação mensal DARF (R$ 35.000)</h2>
    <table>
      <thead><tr><th>Mês</th><th>Proventos de venda (BRL)</th><th>Precisa DARF?</th></tr></thead>
      <tbody>
        {''.join(monthly_rows) if monthly_rows else '<tr><td colspan="3">Sem vendas no ano.</td></tr>'}
      </tbody>
    </table>
  </section>

  <section>
    <h2>4. Obrigações relacionadas: DARF, GCAP e CBE</h2>
    {section_obligations}
  </section>

  <section>
    <h2>5. Guardar valores para o próximo ano (arquivo JSON)</h2>
    {section_json}
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


def write_guide_copy(output_dir: Path) -> None:
    source = guide_source_path()
    if not source.exists():
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output_dir / GUIDE_FILENAME)


def write_report(report: IrpfReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_guide_copy(output_path.parent)
    output_path.write_text(generate_html(report), encoding="utf-8")
