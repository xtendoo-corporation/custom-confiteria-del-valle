{
    "name": "Custom Ventas Confiteria del Valle",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Adaptaciones para el módulo de ventas",
    "description": """
        Adaptaciones de Ventas
        ======================
        - Botón entregar y facturar
        - Selección automática de lote en líneas de pedido
    """,
    "author": "Abraham (Xtendoo)",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "sale_stock"
    ],
    "data": [
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
