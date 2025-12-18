from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date


class CdvForwardTraceReport(models.TransientModel):
    """Informe de Materia Prima (Forward Traceability)

    Permite rastrear en qué productos finales se ha utilizado un lote
    específico de materia prima.
    """
    _name = "cdv.forward.trace.report"
    _description = "Informe de Materia Prima"

    # Filtros de búsqueda
    date_from = fields.Date(
        string="Fecha desde",
        required=True,
        default=lambda self: date(date.today().year, 1, 1),
        help="Fecha de inicio del período de búsqueda",
    )
    date_to = fields.Date(
        string="Fecha hasta",
        required=True,
        default=fields.Date.context_today,
        help="Fecha de fin del período de búsqueda",
    )
    raw_material_id = fields.Many2one(
        comodel_name="product.product",
        string="Materia prima",
        required=True,
        help="Materia prima a rastrear",
    )
    raw_material_lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lote de materia prima",
        required=True,
        help="Lote de la materia prima a rastrear",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    warning_message = fields.Html(
        string="Mensaje de advertencia",
        readonly=True,
    )

    # Resultados
    line_ids = fields.One2many(
        comodel_name="cdv.forward.trace.report.line",
        inverse_name="wizard_id",
        string="Productos finales encontrados",
        readonly=True,
    )

    # Estadísticas
    total_finished_products = fields.Integer(
        string="Total de productos finales",
        compute="_compute_totals",
        store=False,
        help="Número de productos finales diferentes donde se usó la materia prima",
    )
    total_productions = fields.Integer(
        string="Total de producciones",
        compute="_compute_totals",
        store=False,
        help="Número total de producciones donde se usó la materia prima",
    )
    total_qty_produced = fields.Float(
        string="Total de unidades producidas",
        compute="_compute_totals",
        store=False,
        help="Total de unidades producidas con esta materia prima",
    )
    usage_period_start = fields.Datetime(
        string="Inicio del uso",
        compute="_compute_usage_period",
        store=False,
        help="Primera vez que se puso en uso la materia prima",
    )
    usage_period_end = fields.Datetime(
        string="Fin del uso",
        compute="_compute_usage_period",
        store=False,
        help="Última vez que se finalizó el uso de la materia prima",
    )

    @api.depends("line_ids")
    def _compute_totals(self):
        """Calcular totales para el resumen"""
        for record in self:
            # Contar productos finales únicos
            finished_products = record.line_ids.mapped('finished_product_id')
            record.total_finished_products = len(set(finished_products.ids))

            # Contar producciones (producto + lote + fecha)
            productions = record.line_ids.mapped(
                lambda l: (l.finished_product_id.id, l.finished_lot_id.id, l.production_date)
            )
            record.total_productions = len(set(productions))

            # Sumar total de unidades producidas (evitar duplicados por componente)
            qty_dict = {}
            for line in record.line_ids:
                key = (line.finished_product_id.id, line.finished_lot_id.id, line.production_date)
                if key not in qty_dict:
                    qty_dict[key] = line.finished_qty
            record.total_qty_produced = sum(qty_dict.values())

    @api.depends("raw_material_id", "raw_material_lot_id", "company_id")
    def _compute_usage_period(self):
        """Calcular período de uso de la materia prima"""
        for record in self:
            if not record.raw_material_id or not record.raw_material_lot_id:
                record.usage_period_start = False
                record.usage_period_end = False
                continue

            # Buscar todos los registros de uso de esta materia prima con este lote
            usage_records = self.env["cdv.raw.material.in.use"].search([
                ("product_id", "=", record.raw_material_id.id),
                ("lot_id", "=", record.raw_material_lot_id.id),
                ("company_id", "=", record.company_id.id),
            ], order="date_from asc")

            if usage_records:
                record.usage_period_start = usage_records[0].date_from
                # Buscar el último date_to o dejar en False si aún está en uso
                finished_records = usage_records.filtered(lambda r: r.date_to)
                if finished_records:
                    record.usage_period_end = max(finished_records.mapped('date_to'))
                else:
                    record.usage_period_end = False
            else:
                record.usage_period_start = False
                record.usage_period_end = False

    @api.onchange("raw_material_id")
    def _onchange_raw_material_id(self):
        """Limpiar lote cuando cambia la materia prima"""
        if self.raw_material_id:
            self.raw_material_lot_id = False
            return {
                "domain": {
                    "raw_material_lot_id": [
                        ("product_id", "=", self.raw_material_id.id),
                        ("company_id", "=", self.company_id.id),
                    ]
                }
            }
        return {"domain": {"raw_material_lot_id": []}}

    def action_compute_trace(self):
        """Calcular trazabilidad hacia adelante"""
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError(
                _("La fecha desde debe ser menor o igual a la fecha hasta.")
            )

        # Limpiar líneas anteriores y mensaje de advertencia
        self.line_ids.unlink()
        self.warning_message = False

        # 1. Buscar todos los períodos donde esta materia prima estuvo en uso
        usage_records = self.env["cdv.raw.material.in.use"].search([
            ("product_id", "=", self.raw_material_id.id),
            ("lot_id", "=", self.raw_material_lot_id.id),
            ("company_id", "=", self.company_id.id),
        ])

        if not usage_records:
            # Mostrar advertencia en lugar de error
            self.warning_message = """
                <h4 class="alert-heading">
                    <i class="fa fa-exclamation-triangle"></i>
                    No se encontraron registros de uso
                </h4>
                <p>
                    No se encontraron registros de uso para la materia prima
                    <strong>%s</strong> (Lote: <strong>%s</strong>).
                </p>
                <hr/>
                <p class="mb-0">
                    <strong>Verifique que:</strong>
                </p>
                <ul>
                    <li>La materia prima y lote sean correctos</li>
                    <li>Se haya registrado el uso de esta materia prima</li>
                    <li>El período de búsqueda sea correcto</li>
                </ul>
            """ % (self.raw_material_id.name, self.raw_material_lot_id.name)

            return {
                "type": "ir.actions.act_window",
                "res_model": "cdv.forward.trace.report",
                "view_mode": "form",
                "res_id": self.id,
                "target": "new",
                "context": self.env.context,
            }

        # 2. Buscar partes de producción que coincidan con los períodos de uso
        lines_to_create = []

        for usage in usage_records:
            # Determinar el rango de fechas efectivo
            usage_start = usage.date_from
            usage_end = usage.date_to or fields.Datetime.now()

            # Convertir a date para comparación con el filtro del usuario
            usage_start_date = usage_start.date() if isinstance(usage_start, datetime) else usage_start
            usage_end_date = usage_end.date() if isinstance(usage_end, datetime) else usage_end

            # Intersección con el rango de búsqueda del usuario
            search_start = max(usage_start_date, self.date_from)
            search_end = min(usage_end_date, self.date_to)

            # Si no hay intersección, continuar
            if search_start > search_end:
                continue

            # Buscar partes de producción en este rango
            domain = [
                ("is_production_entry", "=", True),
                ("state", "=", "done"),
                ("date_done", ">=", datetime.combine(search_start, datetime.min.time())),
                ("date_done", "<=", datetime.combine(search_end, datetime.max.time())),
                ("company_id", "=", self.company_id.id),
            ]

            production_entries = self.env["stock.picking"].search(domain)

            # 3. Para cada producción, verificar si usa esta materia prima en su BoM
            for entry in production_entries:
                for line in entry.move_ids:
                    # Obtener BoM del producto terminado
                    boms = self.env["mrp.bom"]._bom_find(
                        line.product_id,
                        company_id=self.company_id.id,
                        bom_type="normal",
                    )
                    bom = boms[line.product_id] if boms else False

                    if not bom:
                        # Producto sin BoM, no podemos saber si usa esta materia prima
                        continue

                    # Verificar si la materia prima está en los componentes de la BoM
                    bom_component = bom.bom_line_ids.filtered(
                        lambda bl: bl.product_id == self.raw_material_id
                    )

                    if not bom_component:
                        # Esta producción no usa nuestra materia prima
                        continue

                    # Esta producción SÍ usa nuestra materia prima
                    # Crear una línea por cada lote del producto terminado
                    prod_date = entry.date_done.date() if entry.date_done else entry.scheduled_date

                    for move_line in line.move_line_ids:
                        lines_to_create.append({
                            "wizard_id": self.id,
                            "production_date": prod_date,
                            "usage_period_id": usage.id,
                            "finished_product_id": line.product_id.id,
                            "finished_lot_id": move_line.lot_id.id if move_line.lot_id else False,
                            "finished_qty": move_line.quantity,
                            "finished_uom_id": line.product_uom.id,
                            "component_qty_per_unit": bom_component[0].product_qty if bom_component else 0.0,
                            "component_qty_total": (
                                bom_component[0].product_qty * move_line.quantity
                                if bom_component else 0.0
                            ),
                            "production_entry_id": entry.id,
                        })

        if lines_to_create:
            # Crear las líneas
            self.env["cdv.forward.trace.report.line"].create(lines_to_create)
            self.warning_message = False
        else:
            # Mostrar advertencia en lugar de error
            self.warning_message = """
                <h4 class="alert-heading">
                    <i class="fa fa-exclamation-triangle"></i>
                    No se encontraron producciones
                </h4>
                <p>
                    No se encontraron producciones que utilicen la materia prima
                    <strong>%s</strong> (Lote: <strong>%s</strong>)
                    en el período seleccionado.
                </p>
                <hr/>
                <p class="mb-0">
                    <strong>Verifique que:</strong>
                </p>
                <ul>
                    <li>La materia prima y lote sean correctos</li>
                    <li>Existan partes de producción en el período indicado</li>
                    <li>Los productos elaborados tengan BoM configuradas</li>
                    <li>La materia prima esté incluida en las BoM</li>
                </ul>
            """ % (self.raw_material_id.name, self.raw_material_lot_id.name)

        return {
            "type": "ir.actions.act_window",
            "res_model": "cdv.forward.trace.report",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }

    def action_print_report(self):
        """Imprimir informe PDF"""
        self.ensure_one()

        if not self.line_ids:
            raise UserError(
                _("Debe calcular la trazabilidad antes de imprimir el informe.")
            )

        return self.env.ref(
            "cdv_production_traceability.action_report_forward_traceability"
        ).report_action(self)

    def action_reset(self):
        """Volver a borrador para nueva búsqueda"""
        self.ensure_one()
        self.line_ids.unlink()
        self.warning_message = False
        return {
            "type": "ir.actions.act_window",
            "res_model": "cdv.forward.trace.report",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }


class CdvForwardTraceReportLine(models.TransientModel):
    """Línea de informe de materia prima"""
    _name = "cdv.forward.trace.report.line"
    _description = "Línea de informe de materia prima"
    _order = "production_date desc, finished_product_id"

    wizard_id = fields.Many2one(
        comodel_name="cdv.forward.trace.report",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    production_date = fields.Date(
        string="Fecha de producción",
        required=True,
        index=True,
    )
    usage_period_id = fields.Many2one(
        comodel_name="cdv.raw.material.in.use",
        string="Período de uso",
        help="Registro de materia prima en uso durante esta producción",
    )
    finished_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto final",
        required=True,
        index=True,
    )
    finished_lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lote producto final",
        index=True,
    )
    finished_qty = fields.Float(
        string="Cantidad producida",
        digits="Product Unit of Measure",
    )
    finished_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UdM",
    )
    component_qty_per_unit = fields.Float(
        string="Cantidad materia prima por unidad",
        digits="Product Unit of Measure",
        help="Cantidad de materia prima necesaria por unidad según BoM",
    )
    component_qty_total = fields.Float(
        string="Cantidad total materia prima",
        digits="Product Unit of Measure",
        help="Cantidad total de materia prima utilizada en esta producción",
    )
    production_entry_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Parte de producción",
        help="Albarán de producción donde se registró",
    )
    usage_date_from = fields.Datetime(
        string="Inicio uso materia prima",
        related="usage_period_id.date_from",
        readonly=True,
    )
    usage_date_to = fields.Datetime(
        string="Fin uso materia prima",
        related="usage_period_id.date_to",
        readonly=True,
    )

