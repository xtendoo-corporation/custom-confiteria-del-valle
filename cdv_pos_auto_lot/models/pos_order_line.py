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
            ("location_id", "in", src_loc.child_internal_location_ids.ids),
            ("quantity", ">", 0),
            ("lot_id", "!=", False),
        ]

        groups = (
            self.sudo()
            .env["stock.quant"]
            ._read_group(
                domain=domain,
                groupby=["lot_id"],
                aggregates=["quantity:sum"],
            )
        )

        result = []
        for lot_recordset, total_quantity in groups:
            if lot_recordset:
                result.append(
                    {
                        "id": lot_recordset.id,
                        "name": lot_recordset.name,
                        "product_qty": total_quantity,
                        "expiration_date": (
                            lot_recordset.expiration_date.isoformat()
                            if hasattr(lot_recordset, "expiration_date")
                            and lot_recordset.expiration_date
                            else False
                        ),
                    }
                )

        # Sort by expiration_date ASC (FEFO), nulls last
        result.sort(
            key=lambda x: (
                x["expiration_date"] is False,
                x["expiration_date"] or "",
            )
        )

        if result:
            return result

        # 2. No stock available — find the last created lot for this product
        last_lot = (
            self.sudo()
            .env["stock.lot"]
            .search(
                [
                    ("product_id", "=", product_id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", company_id),
                ],
                order="create_date DESC",
                limit=1,
            )
        )

        if last_lot:
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
