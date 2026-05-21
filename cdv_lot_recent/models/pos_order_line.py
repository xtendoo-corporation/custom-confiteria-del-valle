from odoo import api, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    @api.model
    def get_lots_for_auto_assign(self, company_id, config_id, product_id):
        """
        Sobreescribe el método FEFO de cdv_pos_auto_lot para usar criterio LIFO
        (lote más reciente primero, por fecha de caducidad o fecha de creación).

        Si hay stock disponible: devuelve el lote con fecha de caducidad más
        reciente (o con fecha de entrada más reciente si no hay caducidad).
        Si no hay stock: devuelve el último lote creado para el producto.
        Devuelve: [{id, name, product_qty, expiration_date, create_date}]
        """
        self.check_access("read")
        pos_config = self.env["pos.config"].browse(config_id)
        if not pos_config:
            return []

        src_loc = pos_config.picking_type_id.default_location_src_id

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
                        "create_date": lot_recordset.create_date.isoformat() if lot_recordset.create_date else "",
                    }
                )

        # Ordenar por fecha de caducidad DESC (LIFO — más reciente primero),
        # nulos al final, luego por fecha de creación DESC como criterio secundario.
        result.sort(
            key=lambda x: (
                x["expiration_date"] is not False,
                x["expiration_date"] or "",
                x["create_date"],
            ),
            reverse=True,
        )

        if result:
            return result

        # Sin stock disponible — buscar el último lote creado para este producto
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
                    "create_date": last_lot.create_date.isoformat() if last_lot.create_date else "",
                }
            ]

        return []
