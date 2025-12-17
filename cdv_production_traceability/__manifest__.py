{
    "name": "Confitería del Valle - Trazabilidad de Producción",
    "version": "19.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Sistema completo de trazabilidad de producción para confitería/panadería",
    "description": """
        Trazabilidad de Producción - Confitería del Valle
        ==================================================

        Características principales:

        * Gestión de materias primas en uso con interfaz táctil
        * Partes de producción para registrar múltiples productos a la vez
        * Lotes automáticos por fecha (formato DDMMYY) compartidos entre todos los productos
        * Integración con albaranes de entrada (stock.picking)
        * Informes de trazabilidad completos para inspecciones sanitarias
        * Integración con BoM (Listas de materiales)

        Configuración inicial:

        1. Ir a Inventario > Configuración > Ajustes
        2. Buscar la sección "Confitería del Valle - Trazabilidad"
        3. Configurar ubicaciones de materias primas y productos terminados

        Uso diario:

        1. Poner materias primas en producción (Producción > Materias primas > Materias primas en uso)
        2. Crear partes de producción con múltiples productos (Producción > Producción diaria > Partes de producción)
        3. El número de lote se genera automáticamente en formato DDMMYY y se aplica a todos los productos
        4. Consultar trazabilidad (Producción > Informes > Informe de trazabilidad)
    """,
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "stock",
        "mrp",
    ],
    "data": [
        # Seguridad
        "security/cdv_security.xml",
        "security/ir.model.access.csv",
        # Vistas
        "views/cdv_raw_material_in_use_views.xml",
        "views/stock_picking_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
        # Wizards (deben cargarse antes de los menús que los referencian)
        "wizards/cdv_raw_material_wizard_views.xml",
        "wizards/cdv_production_trace_report_views.xml",
        # Menús (deben cargarse después de las vistas y wizards)
        "views/cdv_menus.xml",
        # Informes
        "report/cdv_traceability_report.xml",
        "report/cdv_traceability_report_template.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
