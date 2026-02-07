from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.onchange('product_id')
    def _onchange_product_id_uom_production_preferred(self):
        """
        Al cambiar el producto a fabricar, aplicar la UoM de producción preferida si existe.
        """
        if self.product_id and self.product_id.uom_production_preferred_id:
            self.product_uom_id = self.product_id.uom_production_preferred_id
        elif self.product_id:
            # Comportamiento estándar
            self.product_uom_id = self.product_id.uom_id

    @api.model_create_multi
    def create(self, vals_list):
        """
        Al crear una orden de fabricación, si el producto tiene UoM preferida,
        aplicarla si no se especificó otra.
        """
        for vals in vals_list:
            product_id = vals.get('product_id')
            if product_id and 'product_uom_id' not in vals:
                product = self.env['product.product'].browse(product_id)
                if product.uom_production_preferred_id:
                    vals['product_uom_id'] = product.uom_production_preferred_id.id

        return super(MrpProduction, self).create(vals_list)

    def write(self, vals):
        """
        Al cambiar el producto en una MO existente, aplicar UoM preferida si corresponde.
        """
        if 'product_id' in vals and 'product_uom_id' not in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            if product.uom_production_preferred_id:
                vals['product_uom_id'] = product.uom_production_preferred_id.id

        return super(MrpProduction, self).write(vals)

