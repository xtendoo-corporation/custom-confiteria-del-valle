{
    "name": "Trazabilidad de producción para confitería/panadería",
    "version": "19.0.1.1.0",
    "category": "Manufacturing",
    "summary": "Sistema completo de trazabilidad de producción para confitería/panadería",
    "description": """
        Trazabilidad de Producción - Información adicional
        ==================================================

        Características principales:

        * Gestión de materias primas en uso con interfaz táctil
        * Partes de producción para registrar múltiples productos a la vez
        * Lotes automáticos por fecha (formato DDMMYY) compartidos entre todos los productos
        * Integración con albaranes de entrada (stock.picking)
        * Informes de trazabilidad completos para inspecciones sanitarias
        * Integración con BoM (Listas de materiales)
        * **UoM preferidas para Producción y Compra**: Configure una vez la unidad de medida preferida
          (ej: "Caja") y se aplicará automáticamente en órdenes de fabricación y BoMs

        Configuración inicial:

        1. Ir a Inventario > Configuración > Ajustes
        2. Buscar la sección "Información adicional - Trazabilidad"
        3. Configurar ubicaciones de materias primas y productos terminados

        Uso diario:

        1. Poner materias primas en producción (Producción > Materias primas > Materias primas en uso)
        2. Crear partes de producción con múltiples productos (Producción > Producción diaria > Partes de producción)
        3. El número de lote se genera automáticamente en formato DDMMYY y se aplica a todos los productos
        4. Consultar trazabilidad (Producción > Informes > Informe de trazabilidad)

        UoM Preferidas:

        1. En la ficha del producto, pestaña Inventario, configurar "UdM preferida para Producción"
        2. Al crear órdenes de fabricación, se usará automáticamente esa unidad de medida
        3. En las líneas de BoM, se aplicará automáticamente al seleccionar el producto
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
        # Wizards (deben cargarse antes que las vistas que los referencian)
        "wizards/cdv_production_trace_report_views.xml",
        "wizards/cdv_forward_trace_report_views.xml",
        # Vistas (se cargan después de los wizards)
        "views/cdv_raw_material_in_use_views.xml",
        "views/stock_picking_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
        # Menús (deben cargarse después de las vistas y wizards)
        "views/cdv_menus.xml",
        # Informes
        "report/cdv_traceability_report.xml",
        "report/cdv_forward_traceability_report.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
