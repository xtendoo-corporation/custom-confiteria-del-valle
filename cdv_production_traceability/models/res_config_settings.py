from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cdv_raw_material_location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Ubicación de materias primas',
        help='Ubicación donde se almacenan las materias primas',
        config_parameter='cdv_production_traceability.raw_material_location_id',
    )
    cdv_finished_location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Ubicación de productos terminados',
        help='Ubicación destino para productos terminados',
        config_parameter='cdv_production_traceability.finished_location_id',
    )
    cdv_finished_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Tipo de albarán para productos terminados',
        help='Tipo de albarán usado para entradas de productos terminados',
        config_parameter='cdv_production_traceability.finished_picking_type_id',
    )
    cdv_auto_validate_picking = fields.Boolean(
        string='Validar albaranes automáticamente',
        help='Si está marcado, los albaranes de producción se validarán automáticamente al confirmar el parte',
        config_parameter='cdv_production_traceability.auto_validate_picking',
        default=False,
    )

