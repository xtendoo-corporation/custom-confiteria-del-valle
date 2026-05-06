from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_FINISHED_PRODUCT_DOMAIN = repr([
    ("cdv_is_finished_product", "=", True),
    ("is_storable", "=", True),
    ("tracking", "in", ["lot", "serial"]),
])
class StockMove(models.Model):
    _inherit = "stock.move"
    cdv_picking_is_production_entry = fields.Boolean(
        related="picking_id.is_production_entry",
        string="Es parte de produccion",
        readonly=True,
    )
    cdv_product_id_domain = fields.Char(
        compute="_compute_cdv_product_id_domain",
        store=False,
    )
    @api.depends("cdv_picking_is_production_entry")
    def _compute_cdv_product_id_domain(self):
        for move in self:
            if move.cdv_picking_is_production_entry:
                move.cdv_product_id_domain = _FINISHED_PRODUCT_DOMAIN
            else:
                move.cdv_product_id_domain = "[]"
    @api.depends("product_id", "picking_id.is_production_entry")
    def _compute_product_uom(self):
        super()._compute_product_uom()
        for move in self:
            is_production = (
                move.picking_id.is_production_entry
                or self.env.context.get("default_is_production_entry")
            )
            if is_production and move.product_id.uom_production_preferred_id:
                move.product_uom = move.product_id.uom_production_preferred_id
    def write(self, vals):
        if "product_id" in vals and "product_uom" not in vals:
            for move in self:
                if move.picking_id and move.picking_id.is_production_entry:
                    product = self.env["product.product"].browse(vals["product_id"])
                    if product.uom_production_preferred_id:
                        vals["product_uom"] = product.uom_production_preferred_id.id
                        break
        result = super().write(vals)
        if "product_id" in vals:
            for move in self:
                if move.picking_id and move.picking_id.is_production_entry:
                    self._validate_production_product(move.product_id)
        return result
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "product_id" in vals and "product_uom" not in vals:
                picking_id = vals.get("picking_id")
                if picking_id:
                    picking = self.env["stock.picking"].browse(picking_id)
                    if picking.is_production_entry:
                        product = self.env["product.product"].browse(vals["product_id"])
                        if product.uom_production_preferred_id:
                            vals["product_uom"] = product.uom_production_preferred_id.id
        moves = super().create(vals_list)
        for move in moves:
            if move.picking_id and move.picking_id.is_production_entry:
                self._validate_production_product(move.product_id)
        return moves
    def _validate_production_product(self, product):
        if not product:
            return
        if not product.cdv_is_finished_product:
            raise ValidationError(
                _(
                    "El producto '%s' no esta marcado como producto elaborado.\n\n"
                    "Solo se pueden agregar productos marcados como 'Es producto elaborado' "
                    "en los partes de produccion."
                )
                % product.name
            )
        if not product.is_storable:
            raise ValidationError(
                _(
                    "El producto '%s' no es almacenable.\n\n"
                    "Solo se pueden agregar productos almacenables en los partes de produccion."
                )
                % product.name
            )
        if product.tracking not in ["lot", "serial"]:
            raise ValidationError(
                _(
                    "El producto '%s' no tiene seguimiento por lotes/numero de serie.\n\n"
                    "Solo se pueden agregar productos con seguimiento por lotes o numeros de serie "
                    "en los partes de produccion."
                )
                % product.name
            )
    def _action_cancel(self):
        self.sudo().write({"state": "cancel"})
        return True
    def action_cancel(self):
        return self._action_cancel()
    def unlink(self):
        return models.Model.unlink(self)
