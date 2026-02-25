from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_set_lot(self):
        for line in self:
            if line.product_id and line.product_id.tracking in ['lot', 'serial']:
                last_lot = self.env['stock.lot'].search([
                    ('product_id', '=', line.product_id.id),
                    ('company_id', '=', line.company_id.id or self.env.company.id),
                ], order='create_date desc, id desc', limit=1)
                
                if last_lot and hasattr(line, 'lot_id'):
                    line.lot_id = last_lot
