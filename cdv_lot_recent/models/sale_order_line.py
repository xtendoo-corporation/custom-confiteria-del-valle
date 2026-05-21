from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_set_recent_lot(self):
        """
        Sobreescribe el onchange de cdv_sales_lot para asignar el lote
        MÁS RECIENTE (LIFO) en lugar del más antiguo (FEFO).
        """
        for line in self:
            line.lot_ids = [(5, 0, 0)]  # Limpiar lotes actuales
            if line.product_id and line.product_id.tracking in ['lot', 'serial']:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('company_id', '=', line.company_id.id or self.env.company.id),
                    ('location_id.usage', '=', 'internal'),
                    ('quantity', '>', 0),
                    ('lot_id', '!=', False)
                ], order='in_date desc, id desc', limit=1)

                if quant:
                    line.lot_ids = [(4, quant.lot_id.id)]
