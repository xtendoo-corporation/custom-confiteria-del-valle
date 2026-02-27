from odoo import models, fields, api

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    lot_qty_insufficient = fields.Boolean(
        string='Stock de lote insuficiente',
        compute='_compute_lot_qty_insufficient'
    )

    @api.depends('lot_id', 'quantity', 'product_id', 'company_id')
    def _compute_lot_qty_insufficient(self):
        for line in self:
            if not line.lot_id or not line.product_id:
                line.lot_qty_insufficient = False
                continue
                
            product_id = line.product_id._origin.id or line.product_id.id
            lot_id = line.lot_id._origin.id or line.lot_id.id
            
            if not lot_id or not product_id:
                line.lot_qty_insufficient = False
                continue
                
            domain = [
                ('product_id', '=', product_id),
                ('lot_id', '=', lot_id),
                ('location_id.usage', '=', 'internal'),
            ]
            if line.company_id:
                domain.append('|')
                domain.append(('company_id', '=', line.company_id.id))
                domain.append(('company_id', '=', False))

            quants = self.env['stock.quant'].search(domain)
            
            total_stock = 0.0
            for quant in quants:
                free_qty = quant.quantity
                if hasattr(quant, 'reserved_quantity'):
                     free_qty -= quant.reserved_quantity
                total_stock += free_qty
            
            line.lot_qty_insufficient = line.quantity > total_stock

    def action_lot_warning(self):
        self.ensure_one()
        return {
            'name': 'Lotes Disponibles',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [
                ('product_id', '=', self.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0)
            ],
            'context': {
                'search_default_locationgroup': 1,
            },
            'target': 'new',
        }
