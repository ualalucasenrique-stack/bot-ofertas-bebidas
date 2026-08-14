"""Junta las ofertas de todos los sitios y las guarda en un JSON, para poder
armar un panel visual (HTML) a partir de datos reales sin tener que volver a
scrapear cada vez.

Uso: python export_data.py
"""

import json
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
