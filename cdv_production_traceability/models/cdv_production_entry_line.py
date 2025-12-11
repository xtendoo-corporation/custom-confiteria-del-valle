from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CdvProductionEntryLine(models.Model):
    _name = "cdv.production.entry.line"
    _description = "Línea de parte de producción"
    _order = "entry_id, sequence, id"

    sequence = fields.Integer(
        string="Secuencia",
        default=10,
    )
    entry_id = fields.Many2one(
        comodel_name="cdv.production.entry",
        string="Parte de producción",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto terminado",
        required=True,
        index=True,
    )
    quantity = fields.Float(
        string="Cantidad",
        required=True,
        default=1.0,
        digits="Product Unit of Measure",
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unidad de medida",
        required=True,
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lote",
        help="Lote del producto terminado. Si está vacío, se generará automáticamente con el formato DD-MM-YY",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        related="entry_id.company_id",
        store=True,
        index=True,
    )
    date = fields.Date(
        string="Fecha",
        related="entry_id.date",
        store=True,
        index=True,
    )
    state = fields.Selection(
        string="Estado",
        related="entry_id.state",
        store=True,
    )
    has_bom = fields.Boolean(
        string="Tiene BoM",
        compute="_compute_has_bom",
        store=False,
    )
    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Lista de materiales",
        compute="_compute_bom_id",
        store=False,
    )

    @api.depends("product_id", "company_id")
    def _compute_has_bom(self):
        """Verificar si el producto tiene BoM"""
        for record in self:
            if record.product_id:
                boms = self.env["mrp.bom"]._bom_find(
                    record.product_id,
                    company_id=record.company_id.id,
                    bom_type="normal",
                )
                if isinstance(boms, dict):
                    record.has_bom = bool(boms.get(record.product_id))
                else:
                    record.has_bom = bool(boms)
            else:
                record.has_bom = False

    @api.depends("product_id", "company_id")
    def _compute_bom_id(self):
        """Obtener la BoM del producto"""
        for record in self:
            if record.product_id:
                boms = self.env["mrp.bom"]._bom_find(
                    record.product_id,
                    company_id=record.company_id.id,
                    bom_type="normal",
                )
                if isinstance(boms, dict):
                    record.bom_id = boms.get(record.product_id) or False
                else:
                    record.bom_id = boms[0] if boms else False
            else:
                record.bom_id = False

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """Actualizar UoM cuando cambia el producto"""
        if self.product_id:
            self.uom_id = self.product_id.uom_id

            # Limpiar lote si cambia el producto
            if self.lot_id and self.lot_id.product_id != self.product_id:
                self.lot_id = False

            return {
                "domain": {
                    "uom_id": [
                        ("category_id", "=", self.product_id.uom_id.category_id.id)
                    ],
                    "lot_id": [
                        ("product_id", "=", self.product_id.id),
                        ("company_id", "=", self.company_id.id),
                    ],
                }
            }
        return {"domain": {"uom_id": [], "lot_id": []}}

    @api.constrains("quantity")
    def _check_quantity(self):
        """Validar que la cantidad sea positiva"""
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_("La cantidad debe ser mayor que cero."))

    # TODO: Fix UoM category validation for Odoo 19
    # @api.constrains('uom_id', 'product_id')
    # def _check_uom_category(self):
    #     """Validar que la UoM pertenezca a la categoría correcta"""
    #     for record in self:
    #         if record.product_id and record.uom_id:
    #             if record.uom_id.category_id != record.product_id.uom_id.category_id:
    #                 raise ValidationError(
    #                     _('La unidad de medida debe pertenecer a la categoría "%s".',
    #                       record.product_id.uom_id.category_id.name)
    #                 )

    @api.model_create_multi
    def create(self, vals_list):
        """Establecer UoM por defecto si no se proporciona"""
        for vals in vals_list:
            if "product_id" in vals and not vals.get("uom_id"):
                product = self.env["product.product"].browse(vals["product_id"])
                vals["uom_id"] = product.uom_id.id
        return super().create(vals_list)
