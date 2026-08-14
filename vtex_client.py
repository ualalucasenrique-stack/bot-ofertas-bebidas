"""Cliente genérico para la API pública de VTEX (la plataforma de e-commerce
que usan Carrefour, Vea, Día y Changomas en Argentina).

No hace falta ninguna clave ni login: es la misma API que usa el propio
sitio web para mostrar los productos, así que devuelve JSON directo.
"""

import re
import time
import requests

from thor_common import RetryExhausted, retry_with_backoff

PAGE_SIZE = 50  # máximo que permite la API por página
REQUEST_DELAY_SECONDS = 0.4  # para no bombardear el sitio de pedidos
TIMEOUT_SECONDS = 20
MAX_CREDIBLE_DISCOUNT_PCT = 70
MAX_RETRIES_PER_PAGE = 5

# Muchas promos (2x1, 3x2, "2da unidad al X% off") no cambian el precio de
# lista del producto: viven como texto suelto en las etiquetas de marketing
# del catálogo (clusterHighlights). Este patrón detecta esas etiquetas que
# realmente describen un descuento, y descarta las que son solo nombres de
# marca o códigos internos del sistema (ej. "DISCO_rpainfoexclusivo...").
PROMO_TEXT_PATTERN = re.compile(
    r"(\d+\s*[xX]\s*\d+|\d+\s*%|\boff\b|descuento)", re.IGNORECASE
)


def _get_with_retries(url: str, params: dict) -> requests.Response:
    """Los sitios de los súper a veces devuelven un error de red o un 5xx
    pasajero; reintentamos un par de veces antes de darnos por vencidos.
    Backoff exponencial compartido (thor_common.retry) en vez de la versión
    lineal propia que tenía este archivo antes."""

    def attempt() -> requests.Response:
        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT_SECONDS,
            headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        if response.status_code >= 500:
            raise requests.exceptions.HTTPError(
                f"{response.status_code} del servidor", response=response
            )
        return response

    return retry_with_backoff(
        attempt,
        max_attempts=MAX_RETRIES_PER_PAGE,
        initial_backoff_seconds=1.5,
        backoff_multiplier=2.0,
        retryable_exceptions=(requests.exceptions.RequestException,),
    )


def fetch_category_products(base_url: str, category_id: int) -> list[dict]:
    """Trae todos los productos de una categoría (con paginación) para un sitio VTEX."""
    products = []
    offset = 0

    while True:
        url = f"{base_url}/api/catalog_system/pub/products/search"
        params = {
            "fq": f"C:{category_id}",
            "_from": offset,
            "_to": offset + PAGE_SIZE - 1,
        }
        response = _get_with_retries(url, params)

        if response.status_code == 206 or response.status_code == 200:
            page = response.json()
        elif response.status_code in (400, 416):
            # 416 = "Requested range not satisfiable", 400 = se pasó del límite
            # de paginación que impone VTEX (offset máximo ~2500). En ambos
            # casos significa que ya no hay más páginas.
            break
        else:
            response.raise_for_status()
            page = []

        if not page:
            break

        products.extend(page)
        offset += PAGE_SIZE
        time.sleep(REQUEST_DELAY_SECONDS)

        if len(page) < PAGE_SIZE:
            break

    return products


def _promo_badges_from_cluster_highlights(raw_product: dict) -> list[str]:
    highlights = (raw_product.get("clusterHighlights") or {}).values()
    return sorted(
        {
            text.strip()
            for text in highlights
            if PROMO_TEXT_PATTERN.search(text) and "_" not in text
        }
    )


def extract_offers(raw_product: dict) -> list[dict]:
    """De un producto VTEX crudo, saca las ofertas vigentes (una por 'seller')."""
    offers = []
    product_name = raw_product.get("productName", "").strip()
    cluster_badges = _promo_badges_from_cluster_highlights(raw_product)

    for item in raw_product.get("items", []):
        for seller in item.get("sellers", []):
            offer = seller.get("commertialOffer", {})

            if not offer.get("IsAvailable"):
                continue

            price = offer.get("Price")
            list_price = offer.get("ListPrice")
            if not price or not list_price:
                continue

            offer_badges = sorted(
                {
                    (badge.get("name") or badge.get("Name") or "").strip()
                    for badge in (offer.get("Teasers", []) + offer.get("DiscountHighLight", []))
                    if (badge.get("name") or badge.get("Name"))
                }
            )
            badges = sorted(set(cluster_badges + offer_badges))

            discount_pct = round((1 - price / list_price) * 100) if price < list_price else 0

            # Algunos catálogos tienen un "precio de lista" desactualizado/roto
            # (a veces por un factor fijo en todo el catálogo) que arma
            # descuentos falsos del 90%+. Un descuento real de supermercado
            # casi nunca supera el ~70%: si lo supera, no confiamos en el
            # precio de lista y solo mostramos el producto si tiene una
            # promo explícita (badge) detrás.
            price_discount_is_credible = 0 < discount_pct <= MAX_CREDIBLE_DISCOUNT_PCT
            if not price_discount_is_credible:
                discount_pct = 0

            if not price_discount_is_credible and not badges:
                continue

            offers.append(
                {
                    "product_id": raw_product.get("productId"),
                    "product_name": product_name,
                    "price": price,
                    "list_price": list_price,
                    "discount_pct": discount_pct,
                    "badges": badges,
                }
            )

    return offers


def fetch_offers_for_site(base_url: str, category_ids: list[int]) -> list[dict]:
    """Junta ofertas de varias categorías de un mismo sitio, sin duplicar productos."""
    seen_products = set()
    all_offers = []

    for category_id in category_ids:
        try:
            raw_products = fetch_category_products(base_url, category_id)
        except (requests.exceptions.RequestException, RetryExhausted) as error:
            # Una categoría que falla no debería tirar abajo el reporte
            # entero: seguimos con las demás y el resto del sitio.
            print(f"  Aviso: no se pudo leer {base_url} categoría {category_id}: {error}")
            continue
        for raw_product in raw_products:
            product_id = raw_product.get("productId")
            if product_id in seen_products:
                continue
            seen_products.add(product_id)
            all_offers.extend(extract_offers(raw_product))

    return all_offers
