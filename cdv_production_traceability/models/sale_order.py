from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_deliver_and_invoice(self):
        for order in self:
            # 1. Validate pickings
            pickings = order.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])
            for picking in pickings:
                if picking.state in ['draft', 'waiting', 'confirmed']:
                    picking.action_assign()
                for move in picking.move_ids.filtered(lambda m: m.state not in ['done', 'cancel']):
                    move.quantity = move.product_uom_qty
                    if hasattr(move, 'picked'):
                        move.picked = True
                picking.with_context(skip_sms=True, skip_backorder=True).button_validate()
            
            # 2. Create invoice
            if order.invoice_status in ['to invoice', 'no']:
                try:
                    invoices = order._create_invoices(final=True)
                    for invoice in invoices:
                        if invoice.state == 'draft':
                            invoice.action_post()
                except Exception as e:
                    # Ignore if nothing to invoice
                    pass
        return True
