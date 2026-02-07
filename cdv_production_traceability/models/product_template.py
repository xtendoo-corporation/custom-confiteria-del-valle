from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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

    # UoM preferidas para producción y compra
    uom_production_preferred_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UdM preferida para Producción',
        help='Unidad de medida que se aplicará automáticamente en órdenes de fabricación y BoMs. '
             'Debe pertenecer a la misma categoría que la UdM base del producto.',
    )
    uom_purchase_preferred_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UdM preferida para Compra',
        help='Unidad de medida preferida para compras (independiente del proveedor). '
             'Debe pertenecer a la misma categoría que la UdM base del producto.',
    )

    @api.onchange('uom_id')
    def _onchange_uom_id_clear_preferred(self):
        """Al cambiar la UoM base, limpiar las preferidas si no son compatibles"""
        if self.uom_id:
            if self.uom_production_preferred_id and \
               self.uom_production_preferred_id.category_id != self.uom_id.category_id:
                self.uom_production_preferred_id = False
            if self.uom_purchase_preferred_id and \
               self.uom_purchase_preferred_id.category_id != self.uom_id.category_id:
                self.uom_purchase_preferred_id = False

    @api.constrains('uom_production_preferred_id', 'uom_id')
    def _check_uom_production_preferred_category(self):
        """Validar que la UoM de producción preferida pertenezca a la misma categoría que la UoM base"""
        for product in self:
            if product.uom_production_preferred_id:
                if product.uom_production_preferred_id.category_id != product.uom_id.category_id:
                    raise ValidationError(
                        _("La UdM preferida para Producción '%s' debe pertenecer a la misma categoría "
                          "que la UdM base del producto '%s'.\n\n"
                          "UdM base: %s (Categoría: %s)\n"
                          "UdM preferida: %s (Categoría: %s)") % (
                            product.uom_production_preferred_id.name,
                            product.name,
                            product.uom_id.name,
                            product.uom_id.category_id.name,
                            product.uom_production_preferred_id.name,
                            product.uom_production_preferred_id.category_id.name,
                        )
                    )

    @api.constrains('uom_purchase_preferred_id', 'uom_id')
    def _check_uom_purchase_preferred_category(self):
        """Validar que la UoM de compra preferida pertenezca a la misma categoría que la UoM base"""
        for product in self:
            if product.uom_purchase_preferred_id:
                if product.uom_purchase_preferred_id.category_id != product.uom_id.category_id:
                    raise ValidationError(
                        _("La UdM preferida para Compra '%s' debe pertenecer a la misma categoría "
                          "que la UdM base del producto '%s'.\n\n"
                          "UdM base: %s (Categoría: %s)\n"
                          "UdM preferida: %s (Categoría: %s)") % (
                            product.uom_purchase_preferred_id.name,
                            product.name,
                            product.uom_id.name,
                            product.uom_id.category_id.name,
                            product.uom_purchase_preferred_id.name,
                            product.uom_purchase_preferred_id.category_id.name,
                        )
                    )


