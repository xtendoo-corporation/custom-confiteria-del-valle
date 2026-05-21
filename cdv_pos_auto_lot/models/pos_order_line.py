from odoo import api, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    @api.model
    def get_lots_for_auto_assign(self, company_id, config_id, product_id):
        """
        Return the best lot to auto-assign using FEFO (First Expired, First Out).
        If no stock is available, return the last created lot for the product.
        Returns a list of dicts: [{id, name, product_qty, expiration_date}]
        """
        self.check_access("read")
        pos_config = self.env["pos.config"].browse(config_id)
        if not pos_config:
            return []

        src_loc = pos_config.picking_type_id.default_location_src_id

        # 1. Search quants with stock > 0, join with lot for expiration_date
        domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "=", company_id),
            ("product_id", "=", product_id),
            ("location_id", "child_of", src_loc.id),
            ("quantity", ">", 0),
            ("lot_id", "!=", False),
        ]

        quants = self.sudo().env["stock.quant"].search(
            domain,
        )

        from datetime import datetime
        def lot_sort_key(q):
            lot_name = q.lot_id.name or ""
            parsed_date = None
            if len(lot_name) >= 6:
                try:
                    # Intentar parsear los primeros 6 caracteres como DDMMYY
                    parsed_date = datetime.strptime(lot_name[:6], '%d%m%y')
                except ValueError:
                    pass
            
            fallback_date = q.lot_id.create_date or q.create_date or datetime.min
            # Ordenar primero por la fecha del nombre, luego por create_date
            return (parsed_date or datetime.min, fallback_date)

        quants = quants.sorted(key=lot_sort_key, reverse=True)

        lot_dict = {}
        for q in quants:
            if q.lot_id.id not in lot_dict:
                lot_dict[q.lot_id.id] = {
                    "id": q.lot_id.id,
                    "name": q.lot_id.name,
                    "product_qty": 0,
                    "create_date": q.lot_id.create_date.isoformat() if q.lot_id.create_date else "",
                }
            lot_dict[q.lot_id.id]["product_qty"] += q.quantity

        result = list(lot_dict.values())

        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning("POS AUTO LOT ASSIGN RESULT: %s", result)

        if result:
            return result

        # 2. No stock available — find the last created lot for this product
        all_lots = self.sudo().env["stock.lot"].search([
            ("product_id", "=", product_id),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", company_id),
        ])
        
        if all_lots:
            from datetime import datetime
            def fallback_sort_key(lot):
                lot_name = lot.name or ""
                parsed_date = None
                if len(lot_name) >= 6:
                    try:
                        parsed_date = datetime.strptime(lot_name[:6], '%d%m%y')
                    except ValueError:
                        pass
                fallback_date = lot.create_date or datetime.min
                return (parsed_date or datetime.min, fallback_date)

            sorted_lots = all_lots.sorted(key=fallback_sort_key, reverse=True)
            last_lot = sorted_lots[0]
            
            return [
                {
                    "id": last_lot.id,
                    "name": last_lot.name,
                    "product_qty": 0,
                    "expiration_date": (
                        last_lot.expiration_date.isoformat()
                        if hasattr(last_lot, "expiration_date")
                        and last_lot.expiration_date
                        else False
                    ),
                }
            ]

        return []
