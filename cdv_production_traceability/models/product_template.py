from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cdv_is_raw_material = fields.Boolean(
        string='Es materia prima',
        help='Marcar si este producto es una materia prima que se usa en producción',
        default=False,
    )
    cdv_is_finished_product = fields.Boolean(
        string='Es producto elaborado',
        help='Marcar si este producto es un producto terminado/elaborado que requiere trazabilidad',
        default=False,
    )

