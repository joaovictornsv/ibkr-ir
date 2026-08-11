"""Shared CSS for HTML reports and the usage guide."""

REPORT_CSS = """
    :root {
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
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }
    main { max-width: 1100px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
    h1, h2, h3 { line-height: 1.2; }
    h1 { font-size: 1.9rem; margin-bottom: 0.25rem; }
    .subtitle { color: var(--muted); margin-bottom: 2rem; }
    section {
      background: var(--card);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.25rem;
      border: 1px solid var(--border);
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
    th, td { padding: 0.55rem 0.45rem; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-weight: 600; }
    ol, ul { padding-left: 1.25rem; }
    .disclaimer { border-left: 4px solid var(--warn); padding-left: 1rem; color: var(--muted); background: var(--warn-bg); border-radius: 0 8px 8px 0; padding: 0.75rem 1rem; }
    .guide-link {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 0.85rem 1rem;
      margin-bottom: 1.25rem;
    }
    .guide-link a { color: var(--accent); font-weight: 600; }
    .badge { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px; font-size: 0.85rem; }
    .badge.warn { background: var(--warn-bg); color: var(--warn); }
    .badge.ok { background: var(--ok-bg); color: var(--ok); }
    button.copy {
      background: #f1f5f9;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.2rem 0.55rem;
      cursor: pointer;
      font-size: 0.8rem;
    }
    button.copy:hover { background: var(--accent); border-color: var(--accent); color: #fff; }
    code { background: #f1f5f9; padding: 0.1rem 0.35rem; border-radius: 4px; border: 1px solid var(--border); font-size: 0.9em; }
    .guide-note {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 0.85rem 1rem;
      margin: 1rem 0;
      color: #1e3a5f;
    }
    .guide-note strong { color: #1e40af; }
    h4 { margin: 1.25rem 0 0.5rem; font-size: 1rem; color: var(--text); }
    h4:first-child { margin-top: 0; }
    .term-list { margin: 0.5rem 0 1rem; }
    .term-list dt {
      font-weight: 600;
      margin-top: 0.65rem;
      color: var(--text);
    }
    .term-list dt:first-child { margin-top: 0; }
    .term-list dd {
      margin: 0.2rem 0 0 0;
      color: var(--muted);
      padding-left: 0;
    }
    .steps { margin: 0.75rem 0; padding-left: 0; list-style: none; }
    .steps li {
      position: relative;
      padding: 0.65rem 0 0.65rem 2.5rem;
      border-bottom: 1px solid var(--border);
    }
    .steps li:last-child { border-bottom: none; }
    .steps li::before {
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
    }
    .obligation-card {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.15rem;
      margin-bottom: 0.85rem;
      background: #fafbfc;
    }
    .obligation-card h4 { margin-top: 0; }
    .obligation-card p:last-child { margin-bottom: 0; }
    small { color: var(--muted); }
"""
