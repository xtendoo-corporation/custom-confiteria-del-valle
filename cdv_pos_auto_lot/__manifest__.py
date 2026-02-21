{
    "name": "POS Auto Lot FEFO",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Asignación automática de lotes en POS usando criterio FEFO",
    "description": """
        POS Auto Lot FEFO
        =================

        Asigna automáticamente el número de lote a los productos en el
        Punto de Venta siguiendo el criterio FEFO (First Expired, First Out).

        Comportamiento:
        * Productos con lote y stock: se asigna el lote con fecha de caducidad
          más próxima automáticamente, sin intervención del usuario.
        * Productos con lote sin stock: se asigna el último lote producido
          o se deja en blanco.
        * Productos sin trazabilidad de lote: funcionan normalmente.
        * Nunca se muestra el popup de selección de lote ni el diálogo
          de confirmación de lotes faltantes al pagar.
    """,
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "product_expiry",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "cdv_pos_auto_lot/static/src/js/pos_auto_lot.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
