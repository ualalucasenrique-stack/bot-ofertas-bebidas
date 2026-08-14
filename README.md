# Bot de ofertas de bebidas — Carrefour, Vea, Día, Changomas y Vital

Junta las ofertas de la categoría Bebidas de estos 5 supermercados y arma un
panel visual (HTML) para abrir en el navegador. No manda email — es un
dashboard, no un digest diario.

## Qué hace y qué no

- **Carrefour, Vea, Día, Changomas**: lee directamente los precios y descuentos
  de sus tiendas online (misma info que ves navegando el sitio), filtrado a la
  categoría Bebidas (alcohólicas, gaseosas, aguas, jugos).
- **Vital**: no tiene tienda online con precios, solo publica folletos semanales
  en PDF (son imágenes escaneadas, no se puede leer el texto automáticamente).
  El panel muestra los links a los folletos vigentes de la sucursal La Plata,
  sin filtrar por categoría — hay que abrir el PDF para ver qué hay.
- **Canales de WhatsApp de los súper**: no están incluidos en esta primera
  versión (no tienen una forma oficial de leerse automáticamente).

## Cómo correrlo

Necesitás tener Python instalado. Después, desde esta carpeta:

```bash
pip install -r requirements.txt
python export_data.py     # scrapea los 5 sitios y guarda offers_snapshot.json
python build_dashboard.py # genera dashboard.html a partir del snapshot
```

Abrí `dashboard.html` directo en el navegador — no depende de ningún servidor.

## Cambiar la sucursal de Vital

Por defecto usa "La Plata". Si querés otra sucursal, cambiá `BRANCH_SLUG` en
`vital_scraper.py` (los valores válidos están en el desplegable de
`vital.com.ar/ofertas`, por ejemplo `berisso` si existiera, o `avellaneda`,
`quilmes`, etc. — fijate cuáles ofrece el sitio).

## Estructura del proyecto

- `sites.py` — qué supermercados y categorías de bebidas se consultan
- `vtex_client.py` — el "motor" que habla con la API de Carrefour/Vea/Día/Changomas
  (retry con backoff vía `thor_common`, ver más abajo)
- `vital_scraper.py` — el scraper especial para Vital (folletos PDF)
- `export_data.py` — scrapea todos los sitios y guarda `offers_snapshot.json`
- `build_dashboard.py` — genera `dashboard.html` a partir del snapshot
- `thor_common/` — copia vendorizada de utilidades compartidas (retry con
  backoff distinguiendo error de red de error lógico). Ver
  [`../ARQUITECTURA-AGENTES.md`](../ARQUITECTURA-AGENTES.md) para el porqué.
  No editar acá directo — el original vive en `../thor-common/`.

## Nota sobre corrida automática

Este proyecto tenía antes un workflow de GitHub Actions + envío por email
(diario, 9am hora Argentina). Se removió al pasar al formato dashboard. Si
en algún momento se quiere volver a automatizar (cron diario + publicar
`dashboard.html` en algún lado, o volver a mandarlo por email), eso queda
pendiente de decidir — no está armado hoy.
