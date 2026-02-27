{
    "name": "Custom Ventas Lotes",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Múltiples lotes en líneas de venta y advertencias visuales",
    "description": """
        Múltiples Lotes en Ventas y Albaranes
        =====================================
        - Permite asignar múltiples lotes a una línea de venta.
        - Asigna el lote más antiguo por defecto.
        - Muestra una advertencia visual si la cantidad pedida es mayor al stock de los lotes indicados.
        - Muestra una advertencia en albaranes si la cantidad a mover supera el stock del lote escogido.
    """,
    "author": "Abraham (Xtendoo)",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "sale_stock",
        "stock"
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
