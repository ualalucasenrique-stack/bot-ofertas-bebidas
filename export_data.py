"""Junta las ofertas de todos los sitios y las guarda en un JSON, para poder
armar un panel visual (HTML) a partir de datos reales sin tener que volver a
scrapear cada vez.

Uso: python export_data.py
"""

import json
import sys
from datetime import datetime

from sites import SITES
from vtex_client import fetch_offers_for_site
from vital_scraper import fetch_vital_flyers
from freshness import apply_freshness, load_state

OUTPUT_PATH = "offers_snapshot.json"


def main() -> None:
    snapshot = {
        "generated_at": datetime.now().isoformat(),
        "sites": [],
        "vital_flyers": [],
    }

    for site in SITES:
        print(f"Buscando ofertas en {site['name']}...")
        try:
            offers = fetch_offers_for_site(site["base_url"], site["category_ids"])
        except Exception as error:  # un sitio caído no debería tirar el reporte entero
            print(f"  {site['name']} falló: {error}")
            offers = []
        snapshot["sites"].append({"name": site["name"], "offers": offers})
        print(f"  {site['name']}: {len(offers)} ofertas")

    print("Buscando folletos de Vital (La Plata)...")
    try:
        snapshot["vital_flyers"] = fetch_vital_flyers()
    except Exception as error:
        print(f"  Vital falló: {error}")

    total_offers = sum(len(site["offers"]) for site in snapshot["sites"])
    total_flyers = len(snapshot["vital_flyers"])
    if total_offers == 0 and total_flyers == 0:
        # Las 5 fuentes en cero a la vez casi seguro es una falla de red/entorno
        # (proxy, DNS, bloqueo), no que ningún supermercado tenga ofertas hoy.
        # Mejor no pisar el último snapshot bueno con uno vacío.
        print(
            "\nERROR: las 5 fuentes devolvieron 0 resultados. Esto huele a falla "
            "de red/entorno, no a que no haya ofertas en ningún lado. No se "
            "sobreescribe el snapshot anterior."
        )
        sys.exit(1)

    print("Comparando contra la corrida anterior...")
    apply_freshness(snapshot, load_state())

    for site in snapshot["sites"]:
        # nuevas/mejoradas primero, después por % de descuento
        site["offers"].sort(key=lambda o: (not o["is_new"], -o["discount_pct"]))
        if site["source_warning"]:
            print(f"  Aviso: {site['name']}: {site['source_warning']}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
