{
    'name': 'Confitería del Valle - Trazabilidad de Producción',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Sistema completo de trazabilidad de producción para confitería/panadería',
    'description': """
        Trazabilidad de Producción - Confitería del Valle
        ==================================================

        Características principales:

        * Gestión de materias primas en uso con interfaz táctil
        * Partes de producción diaria con generación automática de albaranes
        * Lotes automáticos por fecha de producción (DD-MM-YY)
        * Informes de trazabilidad completos para inspecciones sanitarias
        * Integración completa con BoM (Listas de materiales)

        Configuración inicial:

        1. Ir a Inventario > Configuración > Ajustes
        2. Buscar la sección "Confitería del Valle - Trazabilidad"
        3. Configurar:
           - Ubicación de materias primas
           - Ubicación de productos terminados
           - Tipo de albarán para productos terminados

        Uso diario:

        1. Poner materias primas en producción (Producción > Materia prima en uso)
        2. Registrar partes de producción diaria (Producción > Partes de producción)
        3. Consultar trazabilidad (Producción > Informe de trazabilidad)
    """,
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.es',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
        'mrp',
    ],
    'data': [
        # Seguridad
        'security/cdv_security.xml',
        'security/ir.model.access.csv',

        # Datos
        'data/sequence_data.xml',

        # Vistas
        'views/cdv_raw_material_in_use_views.xml',
        'views/cdv_production_entry_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_template_views.xml',
        'views/cdv_menus.xml',

        # Wizards
        'wizards/cdv_raw_material_wizard_views.xml',
        'wizards/cdv_production_trace_report_views.xml',

        # Informes
        'report/cdv_traceability_report.xml',
        'report/cdv_traceability_report_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

