"""Genera un panel visual (HTML autocontenido) a partir de offers_snapshot.json.
No depende de nada externo: se puede abrir el .html directo en el navegador,
o publicarlo donde se quiera.

Uso: python export_data.py && python build_dashboard.py
"""

import html
import json
from datetime import datetime

SNAPSHOT_PATH = "offers_snapshot.json"
OUTPUT_PATH = "dashboard.html"
TOP_OFFERS_PER_SITE = 12

SITE_MARKS = {
    "Carrefour": "CA",
    "Vea": "VE",
    "Día": "DI",
    "Changomas": "CH",
    "Vital": "VI",
}


def format_price(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def pill_for(discount_pct: int) -> str:
    if discount_pct >= 35:
        cls, label = "pill-good", f"-{discount_pct}%"
    elif discount_pct >= 15:
        cls, label = "pill-warn", f"-{discount_pct}%"
    elif discount_pct > 0:
        cls, label = "pill-info", f"-{discount_pct}%"
    else:
        cls, label = "pill-info", "PROMO"
    return f'<span class="pill {cls}">{label}</span>'


def render_badges(badges: list[str]) -> str:
    if not badges:
        return ""
    chips = "".join(f'<span class="badge">{html.escape(b)}</span>' for b in badges[:3])
    return f'<div class="badges">{chips}</div>'


def render_offer_row(offer: dict) -> str:
    name = html.escape(offer["product_name"])
    discount_pct = offer["discount_pct"]
    price_new = format_price(offer["price"])
    new_tag = '<span class="new-tag">NUEVO</span>' if offer.get("is_new") else ""

    if discount_pct > 0:
        price_old = format_price(offer["list_price"])
        price_html = (
            f'<span class="price-old">{price_old}</span>'
            f'<span class="price-new">{price_new}</span>'
        )
    else:
        price_html = f'<span class="price-new price-new-solo">{price_new}</span>'

    return f"""
        <li class="offer-row">
          <div class="offer-name">{new_tag}{name}{render_badges(offer["badges"])}</div>
          <div class="offer-price">{price_html}</div>
          {pill_for(discount_pct)}
        </li>"""


def render_site_card(site: dict) -> str:
    name = site["name"]
    offers = site["offers"][:TOP_OFFERS_PER_SITE]
    mark = SITE_MARKS.get(name, name[:2].upper())
    rows = "".join(render_offer_row(o) for o in offers) if offers else (
        '<li class="offer-empty">Sin ofertas detectadas hoy.</li>'
    )
    warning = site.get("source_warning")
    warning_html = f'<p class="source-warning">⚠ {html.escape(warning)}</p>' if warning else ""

    return f"""
      <article class="site-card">
        <header class="site-card-head">
          <span class="site-mark">{mark}</span>
          <h2>{html.escape(name)}</h2>
          <span class="site-count">{len(site["offers"])} ofertas</span>
        </header>
        {warning_html}
        <ul class="offer-list">{rows}
        </ul>
      </article>"""


def render_vital_section(flyers: list[dict]) -> str:
    if not flyers:
        chips = '<p class="muted">Sin folletos publicados esta semana.</p>'
    else:
        chip_parts = []
        for f in flyers:
            new_tag = '<span class="new-tag">NUEVO</span>' if f.get("is_new") else ""
            chip_parts.append(
                f'<a class="flyer-chip" href="{html.escape(f["pdf_url"])}" target="_blank" rel="noopener">'
                f'{new_tag}{html.escape(f["title"])}<span class="chip-tag">PDF</span></a>'
            )
        chips = f'<div class="flyer-grid">{"".join(chip_parts)}</div>'

    return f"""
      <section class="vital-card" aria-label="Vital">
        <header class="vital-head">
          <span class="site-mark site-mark-alt">VI</span>
          <div>
            <h2>Vital <span class="muted">— La Plata</span></h2>
            <p class="muted">Folletos PDF por sucursal, sin filtrar por bebidas (no tiene tienda online)</p>
          </div>
        </header>
        {chips}
      </section>"""


def render_stats(sites: list[dict], vital_count: int) -> str:
    total = sum(len(s["offers"]) for s in sites)
    tiles = "".join(
        f'<div class="stat"><span class="stat-value">{len(s["offers"])}</span>'
        f'<span class="stat-label">{html.escape(s["name"])}</span></div>'
        for s in sites
    )
    tiles += (
        f'<div class="stat"><span class="stat-value">{vital_count}</span>'
        f'<span class="stat-label">Vital (folletos)</span></div>'
    )
    return f"""
      <section class="stats" aria-label="Resumen">
        <div class="stat stat-total">
          <span class="stat-value">{total}</span>
          <span class="stat-label">ofertas de bebidas hoy</span>
        </div>
        {tiles}
      </section>"""


def main() -> None:
    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    generated_at = datetime.fromisoformat(snapshot["generated_at"])
    timestamp = generated_at.strftime("%d/%m/%Y — %H:%M")

    sites_html = "".join(render_site_card(s) for s in snapshot["sites"])
    stats_html = render_stats(snapshot["sites"], len(snapshot["vital_flyers"]))
    vital_html = render_vital_section(snapshot["vital_flyers"])

    page = TEMPLATE.format(
        timestamp=timestamp,
        stats=stats_html,
        sites=sites_html,
        vital=vital_html,
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"Panel generado en {OUTPUT_PATH}")


TEMPLATE = """<title>Panel de Bebidas</title>
<style>
:root {{
  --bg: #edf0ea;
  --surface: #ffffff;
  --surface-alt: #f4f6f0;
  --ink: #181b15;
  --ink-muted: #5c6355;
  --accent: #8c1f3b;
  --accent-ink: #ffffff;
  --line: #d8ddcf;
  --good: #3f7d4f;
  --good-bg: #e3efe3;
  --warn: #8a6118;
  --warn-bg: #f3e8d2;
  --info: #46536a;
  --info-bg: #e6e9ef;
  --shadow: 0 1px 2px rgba(24, 27, 21, 0.06), 0 8px 24px -12px rgba(24, 27, 21, 0.18);
}}

@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #14100f;
    --surface: #1d1714;
    --surface-alt: #241c18;
    --ink: #f2ede6;
    --ink-muted: #a99c8e;
    --accent: #d3557a;
    --accent-ink: #1a0d10;
    --line: #33291f;
    --good: #6fbf85;
    --good-bg: #223126;
    --warn: #e4b565;
    --warn-bg: #372b18;
    --info: #9fb0c9;
    --info-bg: #232a35;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px -12px rgba(0, 0, 0, 0.6);
  }}
}}

:root[data-theme="dark"] {{
  --bg: #14100f;
  --surface: #1d1714;
  --surface-alt: #241c18;
  --ink: #f2ede6;
  --ink-muted: #a99c8e;
  --accent: #d3557a;
  --accent-ink: #1a0d10;
  --line: #33291f;
  --good: #6fbf85;
  --good-bg: #223126;
  --warn: #e4b565;
  --warn-bg: #372b18;
  --info: #9fb0c9;
  --info-bg: #232a35;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px -12px rgba(0, 0, 0, 0.6);
}}

* {{ box-sizing: border-box; }}

body {{
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}}

.wrap {{
  max-width: 920px;
  margin: 0 auto;
  padding: 2.5rem 1.25rem 4rem;
}}

.masthead {{
  border-bottom: 2px solid var(--ink);
  padding-bottom: 1.25rem;
  margin-bottom: 1.75rem;
}}

.eyebrow {{
  margin: 0 0 0.4rem;
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  color: var(--accent);
  font-weight: 600;
}}

.masthead h1 {{
  margin: 0 0 0.35rem;
  font-family: "Iowan Old Style", "Palatino Linotype", Georgia, ui-serif, serif;
  font-size: clamp(2rem, 5vw, 2.75rem);
  font-weight: 600;
  text-wrap: balance;
  letter-spacing: -0.01em;
}}

.masthead .meta {{
  margin: 0 0 0.15rem;
  color: var(--ink-muted);
  font-size: 0.98rem;
}}

.masthead .timestamp {{
  margin: 0;
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.82rem;
  color: var(--ink-muted);
}}

.stats {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-bottom: 2.25rem;
}}

.stat {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.7rem 1rem;
  min-width: 6.5rem;
  box-shadow: var(--shadow);
}}

.stat-total {{
  background: var(--ink);
  border-color: var(--ink);
}}

.stat-total .stat-value,
.stat-total .stat-label {{
  color: var(--bg);
}}

.stat-value {{
  display: block;
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.1;
}}

.stat-label {{
  display: block;
  margin-top: 0.15rem;
  font-size: 0.72rem;
  letter-spacing: 0.03em;
  color: var(--ink-muted);
}}

.sites {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.1rem;
  margin-bottom: 1.1rem;
}}

.site-card {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 1.1rem 1.2rem 0.6rem;
  box-shadow: var(--shadow);
}}

.site-card-head, .vital-head {{
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  margin-bottom: 0.5rem;
}}

.vital-head {{ align-items: flex-start; }}

.site-mark {{
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  background: var(--accent);
  color: var(--accent-ink);
  border-radius: 6px;
  padding: 0.2rem 0.4rem;
  flex-shrink: 0;
}}

.site-mark-alt {{
  background: var(--info);
  color: var(--surface);
}}

.site-card h2, .vital-card h2 {{
  margin: 0;
  font-family: "Iowan Old Style", "Palatino Linotype", Georgia, ui-serif, serif;
  font-size: 1.2rem;
  font-weight: 600;
}}

.site-count {{
  margin-left: auto;
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.75rem;
  color: var(--ink-muted);
  white-space: nowrap;
}}

.offer-list {{
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--line);
}}

.offer-row {{
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: start;
  gap: 0.6rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid var(--line);
}}

.offer-empty {{
  padding: 0.75rem 0;
  color: var(--ink-muted);
  font-size: 0.9rem;
}}

.offer-name {{
  font-size: 0.88rem;
  line-height: 1.35;
}}

.badges {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.3rem;
}}

.badge {{
  font-size: 0.68rem;
  color: var(--ink-muted);
  background: var(--surface-alt);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0.1rem 0.5rem;
  line-height: 1.5;
}}

.new-tag {{
  display: inline-block;
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  background: var(--accent);
  color: var(--accent-ink);
  border-radius: 4px;
  padding: 0.05rem 0.35rem;
  margin-right: 0.4rem;
  vertical-align: middle;
}}

.source-warning {{
  margin: 0 0 0.5rem;
  font-size: 0.78rem;
  color: var(--warn);
  background: var(--warn-bg);
  border-radius: 8px;
  padding: 0.5rem 0.7rem;
}}

.offer-price {{
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}}

.price-old {{
  font-size: 0.72rem;
  color: var(--ink-muted);
  text-decoration: line-through;
}}

.price-new {{
  font-size: 0.92rem;
  font-weight: 700;
}}

.price-new-solo {{ margin-top: 0.15rem; }}

.pill {{
  align-self: center;
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 0.22rem 0.55rem;
  white-space: nowrap;
}}

.pill-good {{ background: var(--good-bg); color: var(--good); }}
.pill-warn {{ background: var(--warn-bg); color: var(--warn); }}
.pill-info {{ background: var(--info-bg); color: var(--info); }}

.vital-card {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 1.1rem 1.2rem;
  box-shadow: var(--shadow);
  margin-bottom: 2rem;
}}

.muted {{ color: var(--ink-muted); font-weight: 400; font-size: 0.85rem; }}

.flyer-grid {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}}

.flyer-chip {{
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: var(--surface-alt);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0.35rem 0.55rem 0.35rem 0.8rem;
  font-size: 0.8rem;
  color: var(--ink);
  text-decoration: none;
}}

.flyer-chip:hover {{
  border-color: var(--accent);
  color: var(--accent);
}}

.chip-tag {{
  font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  font-size: 0.65rem;
  font-weight: 700;
  background: var(--accent);
  color: var(--accent-ink);
  border-radius: 4px;
  padding: 0.1rem 0.3rem;
}}

.notes {{
  border-top: 1px dashed var(--line);
  padding-top: 1rem;
  font-size: 0.78rem;
  color: var(--ink-muted);
  line-height: 1.6;
}}

.notes p {{ margin: 0 0 0.4rem; }}

@media (max-width: 520px) {{
  .offer-row {{ grid-template-columns: 1fr auto; }}
  .pill {{ grid-column: 2; justify-self: end; }}
}}
</style>
<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">PANEL DIARIO · BEBIDAS</p>
    <h1>Ofertas de bebidas</h1>
    <p class="meta">Carrefour · Vea · Día · Changomas · Vital — La Plata / Berisso</p>
    <p class="timestamp">Generado {timestamp}</p>
  </header>

  {stats}

  <section class="sites" aria-label="Ofertas por cadena">
    {sites}
  </section>

  {vital}

  <footer class="notes">
    <p><strong>Cómo leer esto:</strong> el precio tachado es el precio de lista y el precio en negrita es el precio actual. Cuando no hay un precio tachado, la oferta viene de una promo (2x1, 3x2, "2da unidad al X% off") que no cambia el precio unitario sino que se aplica al pagar. La etiqueta <strong>NUEVO</strong> marca lo que apareció o mejoró desde la corrida anterior — en la primera corrida todo aparece como nuevo, porque no hay una corrida previa con la que comparar.</p>
    <p><strong>Notas de datos:</strong> se descartan descuentos por encima del 70% (suelen ser precios de lista mal cargados, no ofertas reales). Vital no tiene tienda online: se listan los folletos PDF vigentes de la sucursal La Plata sin filtrar por categoría. Un aviso ⚠ en una cadena indica que trajo muchas menos ofertas que su máximo histórico — probable falla de la fuente, no ausencia real de ofertas.</p>
  </footer>
</div>
"""


if __name__ == "__main__":
    main()
