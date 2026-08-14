"""Vital (supermayorista) es distinto a los otros 4: no tiene tienda online
con precios, sino que publica folletos semanales en PDF por sucursal.

Como esos PDF son imágenes escaneadas (no tienen texto seleccionable), no se
puede sacar automáticamente "qué productos de bebidas están en oferta" sin
usar OCR, que es bastante más frágil. Por ahora este módulo junta los
folletos vigentes de la sucursal indicada y los manda como links directos.
"""

import re
import requests

BRANCH_SLUG = "la-plata"
TIMEOUT_SECONDS = 20


def fetch_vital_flyers(branch_slug: str = BRANCH_SLUG) -> list[dict]:
    url = f"https://www.vital.com.ar/ofertas/{branch_slug}/"
    response = requests.get(
        url, timeout=TIMEOUT_SECONDS, headers={"User-Agent": "Mozilla/5.0"}
    )
    response.raise_for_status()
    html = response.text

    flyers = []
    seen_urls = set()

    # cada folleto vive en un bloque <figure> con título en <h6> y el link de
    # descarga del PDF más abajo
    for figure_html in re.findall(r"<figure.*?</figure>", html, flags=re.DOTALL):
        title_match = re.search(r"<h6[^>]*>(.*?)</h6>", figure_html, flags=re.DOTALL)
        pdf_match = re.search(
            r'href="(https://www\.vital\.com\.ar/wp-content/uploads/folletos/[^"]+\.pdf)',
            figure_html,
        )
        if not title_match or not pdf_match:
            continue

        pdf_url = pdf_match.group(1)
        if pdf_url in seen_urls:
            continue
        seen_urls.add(pdf_url)

        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        flyers.append({"title": title, "pdf_url": pdf_url})

    return flyers
