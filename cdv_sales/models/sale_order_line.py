from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_set_lot(self):
        for line in self:
            if line.product_id and line.product_id.tracking in ['lot', 'serial']:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('company_id', '=', line.company_id.id or self.env.company.id),
                    ('location_id.usage', '=', 'internal'),
                    ('quantity', '>', 0),
                    ('lot_id', '!=', False)
                ], order='in_date asc, id asc', limit=1)
                
                if quant and hasattr(line, 'lot_id'):
                    line.lot_id = quant.lot_id
