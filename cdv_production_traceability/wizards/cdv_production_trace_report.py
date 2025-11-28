from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CdvProductionTraceReport(models.TransientModel):
    _name = "cdv.production.trace.report"
    _description = "Asistente de informe de trazabilidad"

    date_from = fields.Date(
        string="Fecha desde",
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string="Fecha hasta",
        required=True,
        default=fields.Date.context_today,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto terminado",
        domain=[("is_storable", "=", True)],
        help="Dejar vacío para todos los productos",
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lote",
        help="Dejar vacío para todos los lotes",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        comodel_name="cdv.production.trace.report.line",
        inverse_name="wizard_id",
        string="Líneas de trazabilidad",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("computed", "Calculado"),
        ],
        string="Estado",
        default="draft",
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """Limpiar lote cuando cambia el producto"""
        if self.product_id:
            self.lot_id = False
            return {
                "domain": {
                    "lot_id": [
                        ("product_id", "=", self.product_id.id),
                        ("company_id", "=", self.company_id.id),
                    ]
                }
            }
        return {"domain": {"lot_id": []}}

    def action_compute_trace(self):
        """Calcular trazabilidad"""
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError(
                _("La fecha desde debe ser menor o igual a la fecha hasta.")
            )

        # Limpiar líneas anteriores
        self.line_ids.unlink()

        # Buscar partes de producción en el rango
        domain = [
            ("state", "=", "done"),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("company_id", "=", self.company_id.id),
        ]

        production_entries = self.env["cdv.production.entry"].search(domain)

        if not production_entries:
            raise UserError(
                _("No se encontraron partes de producción en el período seleccionado.")
            )

        # Procesar cada línea de producción
        lines_to_create = []

        for entry in production_entries:
            for line in entry.line_ids:
                # Filtrar por producto y lote si están especificados
                if self.product_id and line.product_id != self.product_id:
                    continue
                if self.lot_id and line.lot_id != self.lot_id:
                    continue

                # Obtener BoM del producto
                bom = self.env["mrp.bom"]._bom_find(
                    line.product_id,
                    company_id=self.company_id.id,
                    bom_type="normal",
                )

                if not bom:
                    # Producto sin BoM - crear línea sin componentes
                    lines_to_create.append(
                        {
                            "wizard_id": self.id,
                            "production_date": entry.date,
                            "finished_product_id": line.product_id.id,
                            "finished_lot_id": line.lot_id.id if line.lot_id else False,
                            "finished_qty": line.quantity,
                            "finished_uom_id": line.uom_id.id,
                            "component_product_id": False,
                            "component_qty_standard": 0.0,
                            "component_lot_id": False,
                            "trace_status": "missing",
                        }
                    )
                    continue

                # Procesar cada componente de la BoM
                bom_obj = self.env["mrp.bom"].browse(bom[0].id)

                for bom_line in bom_obj.bom_line_ids:
                    component_product = bom_line.product_id

                    # Buscar materia prima en uso en la fecha de producción
                    raw_material = self.env["cdv.raw.material.in.use"].search(
                        [
                            ("product_id", "=", component_product.id),
                            ("company_id", "=", self.company_id.id),
                            ("date_from", "<=", entry.date),
                            "|",
                            ("date_to", "=", False),
                            ("date_to", ">=", entry.date),
                        ],
                        limit=1,
                    )

                    trace_status = "found" if raw_material else "missing"
                    component_lot = raw_material.lot_id if raw_material else False

                    lines_to_create.append(
                        {
                            "wizard_id": self.id,
                            "production_date": entry.date,
                            "finished_product_id": line.product_id.id,
                            "finished_lot_id": line.lot_id.id if line.lot_id else False,
                            "finished_qty": line.quantity,
                            "finished_uom_id": line.uom_id.id,
                            "component_product_id": component_product.id,
                            "component_qty_standard": bom_line.product_qty,
                            "component_lot_id": (
                                component_lot.id if component_lot else False
                            ),
                            "trace_status": trace_status,
                        }
                    )

        if lines_to_create:
            self.env["cdv.production.trace.report.line"].create(lines_to_create)

        self.state = "computed"

        return {
            "type": "ir.actions.act_window",
            "res_model": "cdv.production.trace.report",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }

    def action_print_report(self):
        """Imprimir informe PDF"""
        self.ensure_one()

        if self.state != "computed":
            raise UserError(
                _("Debe calcular la trazabilidad antes de imprimir el informe.")
            )

        return self.env.ref(
            "cdv_production_traceability.action_report_traceability"
        ).report_action(self)

    def action_export_excel(self):
        """Exportar a Excel (opcional - requiere módulo adicional)"""
        self.ensure_one()

        if self.state != "computed":
            raise UserError(_("Debe calcular la trazabilidad antes de exportar."))

        # Esta funcionalidad requeriría un módulo adicional para exportar a Excel
        # Por ahora mostramos un mensaje
        raise UserError(
            _("La exportación a Excel estará disponible en una versión futura.")
        )


class CdvProductionTraceReportLine(models.TransientModel):
    _name = "cdv.production.trace.report.line"
    _description = "Línea de informe de trazabilidad"
    _order = "production_date desc, finished_product_id, component_product_id"

    wizard_id = fields.Many2one(
        comodel_name="cdv.production.trace.report",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    production_date = fields.Date(
        string="Fecha producción",
        required=True,
        index=True,
    )
    finished_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto terminado",
        required=True,
        index=True,
    )
    finished_lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lote producto terminado",
        index=True,
    )
    finished_qty = fields.Float(
        string="Cantidad producida",
        digits="Product Unit of Measure",
    )
    finished_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UdM producto terminado",
    )
    component_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Componente (materia prima)",
        index=True,
    )
    component_qty_standard = fields.Float(
        string="Cantidad estándar componente",
        digits="Product Unit of Measure",
        help="Cantidad del componente según BoM",
    )
    component_lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lote componente",
        index=True,
    )
    trace_status = fields.Selection(
        selection=[
            ("found", "Encontrado"),
            ("missing", "No encontrado"),
        ],
        string="Estado trazabilidad",
        required=True,
        index=True,
    )
    trace_status_display = fields.Char(
        string="Estado",
        compute="_compute_trace_status_display",
    )

    @api.depends("trace_status")
    def _compute_trace_status_display(self):
        for record in self:
            if record.trace_status == "found":
                record.trace_status_display = "✓ Encontrado"
            else:
                record.trace_status_display = "⚠ No encontrado"
