from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:
            if picking.state not in ['draft', 'cancel', 'done']:
                for move in picking.move_ids:
                    if move.state not in ['draft', 'cancel', 'done'] and move.product_id.tracking in ['lot', 'serial']:
                        demanded_qty = move.product_uom_qty
                        if demanded_qty <= 0:
                            continue

                        lines = move.move_line_ids.sorted(key=lambda l: l.id)
                        total_quantity = sum(lines.mapped('quantity'))
                        
                        assigned_lot = False
                        valid_lot_lines = lines.filtered(lambda l: l.lot_id)
                        if valid_lot_lines:
                            assigned_lot = valid_lot_lines[-1].lot_id
                            
                        if not assigned_lot and move.sale_line_id and move.sale_line_id.lot_ids:
                            assigned_lot = move.sale_line_id.lot_ids[-1]
                            
                        if not assigned_lot:
                            assigned_lot = self.env['stock.lot'].search([
                                ('product_id', '=', move.product_id.id),
                                '|', ('company_id', '=', move.company_id.id), ('company_id', '=', False)
                            ], limit=1, order='create_date desc')
                            
                        if total_quantity < demanded_qty:
                            missing_qty = demanded_qty - total_quantity
                            
                            if lines:
                                if valid_lot_lines:
                                    last_line = valid_lot_lines[-1]
                                    last_line.quantity += missing_qty
                                else:
                                    last_line = lines[-1]
                                    if assigned_lot:
                                        last_line.lot_id = assigned_lot.id
                                    last_line.quantity += missing_qty
                            else:
                                if assigned_lot:
                                    self.env['stock.move.line'].create({
                                        'move_id': move.id,
                                        'picking_id': picking.id,
                                        'product_id': move.product_id.id,
                                        'product_uom_id': move.product_uom.id,
                                        'location_id': move.location_id.id,
                                        'location_dest_id': move.location_dest_id.id,
                                        'lot_id': assigned_lot.id,
                                        'quantity': demanded_qty,
                                    })
                                else:
                                    move.quantity = demanded_qty

                        for line in lines.filtered(lambda l: not l.lot_id):
                            if assigned_lot:
                                line.lot_id = assigned_lot.id

        return super().button_validate()
