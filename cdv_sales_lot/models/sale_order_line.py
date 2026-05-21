from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lot_ids = fields.Many2many(
        'stock.lot', 
        string='Lotes Sugeridos'
    )
    
    lot_qty_insufficient = fields.Boolean(
        string='Stock de lote insuficiente',
        compute='_compute_lot_data'
    )
    lot_available_qty = fields.Float(
        string='Stock Lote',
        compute='_compute_lot_data'
    )

    @api.depends('lot_ids', 'product_uom_qty', 'product_id')
    def _compute_lot_data(self):
        for line in self:
            if not line.lot_ids or not line.product_id:
                line.lot_qty_insufficient = False
                line.lot_available_qty = 0.0
                continue
                
            # Extraer IDs reales de base de datos para evitar NewIds en onchange
            product_id = line.product_id._origin.id or line.product_id.id
            lot_ids = line.lot_ids.mapped(lambda l: l._origin.id or l.id)
            lot_ids = [l for l in lot_ids if isinstance(l, int) and l]
            
            if not lot_ids or not product_id:
                line.lot_qty_insufficient = False
                line.lot_available_qty = 0.0
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
                
            line.lot_available_qty = total_stock
            line.lot_qty_insufficient = line.product_uom_qty > total_stock

    @api.onchange('product_id')
    def _onchange_product_id_set_oldest_lot(self):
        for line in self:
            line.lot_ids = [(5, 0, 0)] # Limpiar lotes actuales
            if line.product_id and line.product_id.tracking in ['lot', 'serial']:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    '|',
                    ('company_id', '=', line.company_id.id or self.env.company.id),
                    ('company_id', '=', False),
                    ('location_id', 'child_of', line.order_id.warehouse_id.lot_stock_id.id),
                    ('quantity', '>', 0),
                    ('lot_id', '!=', False)
                ])
                
                if quants:
                    from datetime import datetime
                    def lot_sort_key(q):
                        lot_name = q.lot_id.name or ""
                        parsed_date = None
                        if len(lot_name) >= 6:
                            try:
                                parsed_date = datetime.strptime(lot_name[:6], '%d%m%y')
                            except ValueError:
                                pass
                        fallback_date = q.lot_id.create_date or q.create_date or datetime.min
                        return (parsed_date or datetime.min, fallback_date)

                    sorted_quants = quants.sorted(key=lot_sort_key, reverse=True)
                    line.lot_ids = [(4, sorted_quants[0].lot_id.id)]

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
