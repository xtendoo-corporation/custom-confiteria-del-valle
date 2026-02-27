from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lot_ids = fields.Many2many(
        'stock.lot', 
        string='Lotes Sugeridos'
    )
    
    lot_qty_insufficient = fields.Boolean(
        string='Stock de lote insuficiente',
        compute='_compute_lot_qty_insufficient'
    )

    @api.depends('lot_ids', 'product_uom_qty', 'product_id')
    def _compute_lot_qty_insufficient(self):
        for line in self:
            if not line.lot_ids or not line.product_id:
                line.lot_qty_insufficient = False
                continue
                
            # Extraer IDs reales de base de datos para evitar NewIds en onchange
            product_id = line.product_id._origin.id or line.product_id.id
            lot_ids = line.lot_ids.mapped(lambda l: l._origin.id or l.id)
            lot_ids = [l for l in lot_ids if isinstance(l, int) and l]
            
            if not lot_ids or not product_id:
                line.lot_qty_insufficient = False
                continue
                
            # Buscar quants para estos lotes en ubicaciones internas
            domain = [
                ('product_id', '=', product_id),
                ('lot_id', 'in', lot_ids),
                ('location_id.usage', '=', 'internal'),
            ]
            if line.company_id:
                domain.append('|')
                domain.append(('company_id', '=', line.company_id.id))
                domain.append(('company_id', '=', False))
                
            quants = self.env['stock.quant'].search(domain)
            
            # Calcular la cantidad real disponible (quantity - reserved_quantity)
            total_stock = 0.0
            for quant in quants:
                # Usa quantity (stock físico real), pero restando reservas si se desea stock "libre"
                # O si se quiere simplemente 'quantity' (inventario a mano real):
                free_qty = quant.quantity
                if hasattr(quant, 'reserved_quantity'):
                     free_qty -= quant.reserved_quantity
                total_stock += free_qty
                
            line.lot_qty_insufficient = line.product_uom_qty > total_stock

    @api.onchange('product_id')
    def _onchange_product_id_set_oldest_lot(self):
        for line in self:
            line.lot_ids = [(5, 0, 0)] # Limpiar lotes actuales
            if line.product_id and line.product_id.tracking in ['lot', 'serial']:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('company_id', '=', line.company_id.id or self.env.company.id),
                    ('location_id.usage', '=', 'internal'),
                    ('quantity', '>', 0),
                    ('lot_id', '!=', False)
                ], order='in_date asc, id asc', limit=1)
                
                if quant:
                    line.lot_ids = [(4, quant.lot_id.id)]

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
