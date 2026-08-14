# Configuración de cada supermercado: todos corren sobre la plataforma VTEX,
# por eso se puede usar el mismo cliente (vtex_client.py) apuntando a cada dominio
# con los IDs de categoría de Bebidas que le corresponden a cada uno.

SITES = [
    {
        "name": "Carrefour",
        "base_url": "https://www.carrefour.com.ar",
        # "Bebidas" es una categoría padre única: este ID trae todas las subcategorías
        "category_ids": [255],
    },
    {
        "name": "Vea",
        "base_url": "https://www.vea.com.ar",
        "category_ids": [2],
    },
    {
        "name": "Día",
        "base_url": "https://diaonline.supermercadosdia.com.ar",
        "category_ids": [164],
    },
    {
        "name": "Changomas",
        "base_url": "https://www.masonline.com.ar",
        # Acá no hay una única categoría "Bebidas": están repartidas en varias top-level
        "category_ids": [
            200023,  # Cervezas
            200104,  # Vinos y Espumantes
            200044,  # Fernet y Aperitivos
            200015,  # Bebidas Blancas, Licores y Whiskys
            200051,  # Gaseosas
            200006,  # Aguas
            200062,  # Jugos
            200016,  # Isotónicas y Energizantes
        ],
    },
]
