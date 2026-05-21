{
    "name": "CDV Lote Más Reciente",
    "version": "19.0.1.0.0",
    "category": "Inventory",
    "summary": "Selección automática del lote más reciente en ventas y TPV",
    "description": """
        CDV Lote Más Reciente
        =====================

        Extiende los módulos cdv_sales_lot y cdv_pos_auto_lot para cambiar
        el criterio de selección automática de lotes al más reciente (LIFO).

        Comportamiento:
        * En Ventas: al seleccionar un producto, se asigna automáticamente
          el lote con fecha de entrada más reciente.
        * En TPV: al añadir un producto con lote, se asigna automáticamente
          el lote más reciente (por fecha de caducidad o de creación),
          sin mostrar el popup de selección.
    """,
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "cdv_sales_lot",
        "cdv_pos_auto_lot",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "cdv_lot_recent/static/src/js/pos_lot_recent.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
