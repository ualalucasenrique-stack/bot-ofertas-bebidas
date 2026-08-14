"""Compara la corrida de hoy contra el estado guardado de corridas anteriores
para resolver dos preguntas que el scraping por sí solo no puede responder:

1. ¿Esta cifra de ofertas es baja porque hoy no hay ofertas, o porque la
   fuente se rompió (cambio de API, categoría movida, etc.)?
2. ¿Cuáles de estas ofertas son nuevas o mejoraron desde la última corrida?

Usa thor_common.state (JSONFileStateStore) para persistir entre corridas —
mismo patrón que el resto de los agentes de Negocio Personal.
"""

from thor_common import JSONFileStateStore

STATE_PATH = "estado_ofertas.json"

# Si alguna vez vimos al menos esta cantidad de ofertas en un sitio, ya hay
# suficiente historia como para confiar en la comparación.
MIN_BASELINE_FOR_ALERT = 20
# Por debajo de este porcentaje del máximo histórico, se marca como
# sospechoso en vez de mostrarlo como "hoy no hay ofertas".
BROKEN_SOURCE_RATIO = 0.15


def load_state() -> JSONFileStateStore:
    return JSONFileStateStore(STATE_PATH)


def apply_freshness(snapshot: dict, state: JSONFileStateStore) -> None:
    """Modifica snapshot in-place: agrega `source_warning` por sitio y
    `is_new` por oferta."""
    for site in snapshot["sites"]:
        _flag_broken_source(site, state)
        _flag_new_offers(site, state)

    _flag_new_vital_flyers(snapshot, state)


def _flag_broken_source(site: dict, state: JSONFileStateStore) -> None:
    name = site["name"]
    count = len(site["offers"])
    max_key = f"max_count::{name}"

    max_seen = state.get(max_key, 0)
    if count > max_seen:
        state.set(max_key, count)
        max_seen = count

    site["source_warning"] = None
    if max_seen >= MIN_BASELINE_FOR_ALERT and count < max_seen * BROKEN_SOURCE_RATIO:
        site["source_warning"] = (
            f"Trajo solo {count} ofertas hoy, contra un máximo histórico de "
            f"{max_seen} — probablemente la fuente cambió algo, no que no "
            f"haya ofertas."
        )


def _flag_new_offers(site: dict, state: JSONFileStateStore) -> None:
    key = f"last_offers::{site['name']}"
    previous_ids = set(state.get(key, []))

    current_ids = []
    for offer in site["offers"]:
        # incluye el % de descuento en el identificador: si el mismo
        # producto mejora su descuento, también cuenta como "novedad"
        offer_id = f"{offer.get('product_id')}::{offer['discount_pct']}"
        offer["is_new"] = offer_id not in previous_ids
        current_ids.append(offer_id)

    state.set(key, current_ids)


def _flag_new_vital_flyers(snapshot: dict, state: JSONFileStateStore) -> None:
    key = "last_vital_flyers"
    previous_urls = set(state.get(key, []))

    current_urls = []
    for flyer in snapshot["vital_flyers"]:
        flyer["is_new"] = flyer["pdf_url"] not in previous_urls
        current_urls.append(flyer["pdf_url"])

    state.set(key, current_urls)
