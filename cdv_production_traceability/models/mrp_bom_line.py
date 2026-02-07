from odoo import api, fields, models, _


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    @api.onchange('product_id')
    def _onchange_product_id_uom_production_preferred(self):
        """
        Al cambiar el producto, aplicar la UoM de producción preferida si existe.
        Solo se aplica si el producto tiene configurada una UoM preferida para producción.
        """
        if self.product_id and self.product_id.uom_production_preferred_id:
            # Aplicar la UoM preferida
            self.product_uom_id = self.product_id.uom_production_preferred_id
        elif self.product_id:
            # Comportamiento estándar: usar la UoM base del producto
            self.product_uom_id = self.product_id.uom_id

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id_check_category(self):
        """
        Validar que la UoM seleccionada manualmente pertenezca a la misma categoría
        que la UoM base del producto.
        """
        if self.product_id and self.product_uom_id:
            if self.product_uom_id.category_id != self.product_id.uom_id.category_id:
                return {
                    'warning': {
                        'title': _('Categoría de UdM incompatible'),
                        'message': _(
                            'La UdM seleccionada "%s" no pertenece a la misma categoría '
                            'que la UdM base del producto "%s".\n\n'
                            'Se recomienda usar una UdM de la categoría: %s'
                        ) % (
                            self.product_uom_id.name,
                            self.product_id.uom_id.name,
                            self.product_id.uom_id.category_id.name,
                        )
                    }
                }

