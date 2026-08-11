"""Generate the IRPF HTML guide report."""

from __future__ import annotations

import html
from datetime import date
from decimal import Decimal
from pathlib import Path

from .calculator import CbeCheck, IrpfReport


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


def _section_export_guide(report: IrpfReport, partial_year_note: str) -> str:
    year = report.year
    return f"""
    <p>O <strong>Activity Statement</strong> (extrato de atividades) é o relatório oficial da IBKR
    que lista tudo o que aconteceu na sua conta: compras e vendas, dividendos, saldo em caixa,
    posições abertas e taxas. É o <strong>único arquivo</strong> que este programa aceita.</p>

    <div class="guide-note">
      <strong>Não use o arquivo "Transactions".</strong> A IBKR também oferece exportação de
      transações em CSV, mas esse formato é diferente e <em>não funciona</em> com este programa.
      Procure especificamente o <strong>Activity Statement</strong>.
    </div>

    {partial_year_note}

    <h4>Passo a passo no Client Portal (site da IBKR)</h4>
    <ol class="steps">
      <li data-step="1">Acesse <strong>interactivebrokers.com</strong> e faça login no
        <strong>Client Portal</strong> (portal do cliente).</li>
      <li data-step="2">No menu, vá em <strong>Performance &amp; Reports</strong>
        (Desempenho e Relatórios).</li>
      <li data-step="3">Clique em <strong>Statements</strong> (Extratos) e escolha o tipo
        <strong>Activity</strong> (Atividade).</li>
      <li data-step="4">Selecione sua conta (o número começa com <code>U</code>, por exemplo
        <code>U12345678</code>).</li>
      <li data-step="5">Em <strong>Period</strong> (Período), selecione
        <strong>Custom</strong> (Personalizado) e defina:
        <strong>1º de janeiro de {year}</strong> até <strong>31 de dezembro de {year}</strong>.
        Para uma prévia durante o ano, use a data de hoje como fim — mas reexporte em janeiro
        com o ano completo para o IRPF final.</li>
      <li data-step="6">Em <strong>Format</strong> (Formato), escolha <strong>CSV</strong>.
        Não escolha PDF — o PDF não pode ser lido por este programa.</li>
      <li data-step="7">Clique em <strong>Run</strong> (Executar), aguarde o relatório ser
        gerado e clique em <strong>Download</strong> (Baixar).</li>
      <li data-step="8">Salve o arquivo no seu computador. Ele contém dados pessoais — não
        compartilhe publicamente nem envie para repositórios Git.</li>
    </ol>

    <h4>Alternativa: Trader Workstation (TWS)</h4>
    <p>Se você usa o programa TWS instalado: menu <strong>Account</strong> →
    <strong>Reports</strong> → <strong>Activity</strong>. Configure o mesmo período e formato CSV.</p>

    <h4>Quando exportar?</h4>
    <dl class="term-list">
      <dt>Prévia (a qualquer momento)</dt>
      <dd>Útil para estimar quanto declarar antes do prazo. Os valores ainda podem mudar se você
      comprar ou vender mais ações até 31/12.</dd>
      <dt>Declaração final (recomendado: janeiro do ano seguinte)</dt>
      <dd>Após 31 de dezembro, exporte o extrato com o ano civil completo. Esses são os valores
      oficiais que devem ir no IRPF de {year}.</dd>
    </dl>

    <h4>Seções que o CSV deve conter</h4>
    <p>O extrato padrão da IBKR já inclui as seções necessárias. Se você personaliza o relatório,
    confirme que estas aparecem no arquivo:</p>
    <ul>
      <li><strong>Open Positions</strong> — ações que você ainda tem na carteira</li>
      <li><strong>Trades</strong> — compras e vendas realizadas</li>
      <li><strong>Dividends</strong> — dividendos recebidos</li>
      <li><strong>Withholding Tax</strong> — imposto retido na fonte sobre dividendos</li>
      <li><strong>Cash Report</strong> — movimentação e saldo de caixa</li>
      <li><strong>Net Asset Value</strong> — valor total da conta</li>
      <li><strong>Deposits &amp; Withdrawals</strong> — depósitos e saques (remessas)</li>
    </ul>
    """


def _section_values_guide(
    report: IrpfReport, prior_help: str, is_partial_year: bool
) -> str:
    val_date = report.valuation_date.strftime("%d/%m/%Y")
    year = report.year
    valuation_label = (
        f"data do extrato ({val_date})"
        if is_partial_year
        else f"31/12/{year}"
    )

    prior_block = ""
    if report.is_first_ibkr_year:
        prior_block = """
        <div class="guide-note">
          <strong>Primeiro ano na IBKR:</strong> como você abriu a conta neste ano, a coluna
          &ldquo;valor em 31/12 do ano anterior&rdquo; no IRPF deve ser <strong>R$ 0,00</strong>
          para todos os ativos. O extrato confirma isso quando o campo <em>Prior Total</em> no
          NAV é zero.
        </div>"""
    elif report.prior_year_source == "json":
        prior_block = """
        <div class="guide-note">
          <strong>Valores do ano anterior:</strong> foram carregados automaticamente do arquivo
          JSON gerado na declaração do ano passado. Você não precisa buscar esses números
          manualmente.
        </div>"""
    else:
        prior_block = """
        <div class="guide-note">
          <strong>Atenção — valores do ano anterior não encontrados.</strong> Para preencher a
          coluna &ldquo;valor em 31/12/{prev_year}&rdquo; no IRPF, você pode: (1) exportar o
          Activity Statement de {prev_year} e rodar este programa com
          <code>--prior-statement</code>, ou (2) copiar os valores da sua declaração de IRPF
          de {prev_year}, ou (3) usar o JSON de uma execução anterior com
          <code>--prior-year-json</code>.
        </div>""".format(prev_year=year - 1)

    return f"""
    <p>Esta seção explica <strong>de onde vêm os números</strong> que aparecem na seção 3
    (passo a passo IRPF). Você não precisa calcular nada manualmente — o programa lê o extrato
    da IBKR e busca as taxas de câmbio automaticamente.</p>

    <h4>Termos importantes</h4>
    <dl class="term-list">
      <dt>IRPF</dt>
      <dd>Imposto de Renda da Pessoa Física — a declaração anual que moradores no Brasil
      enviam à Receita Federal, normalmente entre março e maio.</dd>

      <dt>Bens e Direitos</dt>
      <dd>Seção da declaração onde você lista o que possui: imóveis, carros, investimentos.
      Ações na IBKR entram no <strong>Grupo 04</strong> (participações societárias) com
      <strong>Código 03</strong> (ações, inclusive as negociadas em bolsa).</dd>

      <dt>PTAX</dt>
      <dd>Taxa de câmbio oficial do dólar publicada diariamente pelo Banco Central do Brasil.
      Para converter valores em dólar para reais no IRPF, usa-se a PTAX de venda do dia
      relevante (pagamento do dividendo, data da venda, ou 31/12 para posições em carteira).
      Este programa busca a PTAX automaticamente no site do BCB.</dd>

      <dt>Open Positions (posições abertas)</dt>
      <dd>Seção do extrato IBKR que mostra as ações que você <strong>ainda tem</strong> na
      última data do período. Colunas importantes: <em>Symbol</em> (ticker), <em>Quantity</em>
      (quantidade), <em>Close Price</em> (preço de fechamento) e <em>Value</em> (valor total
      em dólar = quantidade × preço).</dd>

      <dt>Cash Report (relatório de caixa)</dt>
      <dd>Seção do extrato que mostra o <strong>saldo em dinheiro</strong> na conta (não
      investido em ações). A linha <em>Ending Cash</em> em USD é o saldo em dólares.</dd>

      <dt>Rendimentos Isentos — Código 05</dt>
      <dd>Seção do IRPF para rendimentos que não pagam imposto no Brasil, como dividendos
      recebidos de empresas no exterior. O valor é o dividendo bruto convertido para reais
      com a PTAX da data do pagamento.</dd>

      <dt>Ganho de capital</dt>
      <dd>Lucro (ou prejuízo) quando você <strong>vende</strong> uma ação por um preço maior
      (ou menor) que o custo de aquisição. No Brasil, pessoa física usa o método de
      <strong>custo médio</strong> para calcular — este programa faz esse cálculo em reais,
      não usa o FIFO da IBKR.</dd>
    </dl>

    <h4>Como cada valor é calculado neste relatório</h4>
    <dl class="term-list">
      <dt>Valor atual ({valuation_label})</dt>
      <dd>Para cada ação em carteira: valor em USD do extrato (Open Positions) multiplicado
      pela PTAX de {val_date}. Para o caixa em USD: saldo do extrato × mesma PTAX.
      Os preços de mercado vêm do próprio extrato — não usamos sites de cotação externos.</dd>

      <dt>Valor em 31/12 do ano anterior</dt>
      <dd>É o que você declarou como valor da posição no IRPF do ano passado. Na ficha de
      Bens e Direitos há duas colunas de valor: a do ano atual e a do ano anterior.
      {prior_help}</dd>

      <dt>Dividendos</dt>
      <dd>Lidos da seção <em>Dividends</em> do extrato. Cada pagamento é convertido com a
      PTAX da data em que o dividendo foi creditado na conta.</dd>

      <dt>Vendas e ganho de capital</dt>
      <dd>Lidas da seção <em>Trades</em>. Para cada venda, o programa calcula o custo médio
      em reais (considerando todas as compras anteriores) e o ganho ou prejuízo em reais.</dd>
    </dl>

    {prior_block}

    <h4>O que você precisa fazer manualmente?</h4>
    <ul>
      <li><strong>Exportar o extrato</strong> da IBKR (seção 1) — o programa não acessa sua
      conta automaticamente.</li>
      <li><strong>Copiar os valores</strong> da seção 3 para o programa da Receita Federal
      (Receita Web ou app Meu Imposto de Renda).</li>
      <li><strong>Conferir</strong> se os números fazem sentido antes de enviar a declaração.
      Em caso de dúvida, consulte um contador.</li>
    </ul>
  """


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
      <strong>R$ 35.000</strong>. Veja a seção 5 deste relatório para a verificação mês a mês.</p>
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
      ganho em reais (seção 3), que servem como base para preencher o GCAP.</p>
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
        <code>python generate.py --year {next_year} --statement extrato.csv</code></li>
      <li data-step="3">O programa encontra <code>output/irpf-{year}.json</code>
        automaticamente e usa os valores salvos como &ldquo;ano anterior&rdquo;.</li>
      <li data-step="4">Se o JSON não existir, use
        <code>--prior-year-json output/irpf-{year}.json</code> para indicar o caminho
        manualmente.</li>
    </ol>

    <h4>Primeiro ano na IBKR?</h4>
    <p>Se {year} foi seu primeiro ano na corretora, todos os valores anteriores são
    <strong>R$ 0,00</strong>. O JSON ainda é gerado, mas na prática a coluna do ano anterior
    ficará zerada — isso é correto.</p>

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

    is_partial_year = report.valuation_date != date(report.year, 12, 31)
    partial_year_note = (
        f"<div class=\"guide-note\"><strong>Período parcial:</strong> este extrato cobre até "
        f"{report.valuation_date.strftime('%d/%m/%Y')}, não o ano completo. Os valores são "
        f"<strong>provisórios</strong> — para o IRPF final, exporte novamente com período de "
        f"1º de janeiro a 31 de dezembro de {report.year}.</div>"
        if is_partial_year
        else ""
    )

    section_export = _section_export_guide(report, partial_year_note)
    section_values = _section_values_guide(report, prior_help, is_partial_year)
    section_obligations = _section_obligations_guide(report, cbe, cbe_status, cbe_reason)
    section_json = _section_json_guide(report)

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
    .guide-note {{
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 0.85rem 1rem;
      margin: 1rem 0;
      color: #1e3a5f;
    }}
    .guide-note strong {{ color: #1e40af; }}
    h4 {{ margin: 1.25rem 0 0.5rem; font-size: 1rem; color: var(--text); }}
    h4:first-child {{ margin-top: 0; }}
    .term-list {{ margin: 0.5rem 0 1rem; }}
    .term-list dt {{
      font-weight: 600;
      margin-top: 0.65rem;
      color: var(--text);
    }}
    .term-list dt:first-child {{ margin-top: 0; }}
    .term-list dd {{
      margin: 0.2rem 0 0 0;
      color: var(--muted);
      padding-left: 0;
    }}
    .steps {{ margin: 0.75rem 0; padding-left: 0; list-style: none; }}
    .steps li {{
      position: relative;
      padding: 0.65rem 0 0.65rem 2.5rem;
      border-bottom: 1px solid var(--border);
    }}
    .steps li:last-child {{ border-bottom: none; }}
    .steps li::before {{
      content: attr(data-step);
      position: absolute;
      left: 0;
      top: 0.65rem;
      width: 1.75rem;
      height: 1.75rem;
      background: var(--accent);
      color: #fff;
      border-radius: 50%;
      font-size: 0.8rem;
      font-weight: 700;
      text-align: center;
      line-height: 1.75rem;
    }}
    .obligation-card {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.15rem;
      margin-bottom: 0.85rem;
      background: #fafbfc;
    }}
    .obligation-card h4 {{ margin-top: 0; }}
    .obligation-card p:last-child {{ margin-bottom: 0; }}
    small {{ color: var(--muted); }}
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
    {section_export}
  </section>

  <section>
    <h2>2. Como obter os valores para o IRPF</h2>
    {section_values}
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
    {section_obligations}
  </section>

  <section>
    <h2>7. Guardar valores para o próximo ano (arquivo JSON)</h2>
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


def write_report(report: IrpfReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_html(report), encoding="utf-8")
