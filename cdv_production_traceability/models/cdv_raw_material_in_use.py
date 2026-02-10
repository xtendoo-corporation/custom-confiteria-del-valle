from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CdvRawMaterialInUse(models.Model):
    _name = "cdv.raw.material.in.use"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Materia prima en uso"
    _order = "date_from desc, id desc"
    _rec_name = "display_name"

    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True,
    )
    display_name = fields.Char(
        string="Nombre completo",
        compute="_compute_display_name",
        store=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Materia prima",
        required=True,
        index=True,
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lote",
        required=True,
        index=True,
    )
    date_from = fields.Datetime(
        string="Fecha inicio uso",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    date_to = fields.Datetime(
        string="Fecha fin uso",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Ubicación",
        help="Ubicación donde se usa esta materia prima",
    )
    is_in_use = fields.Boolean(
        string="En uso",
        compute="_compute_is_in_use",
        store=True,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("in_use", "En uso"),
            ("finished", "Finalizado"),
        ],
        string="Estado",
        compute="_compute_state",
        store=True,
    )

    # -------------------------------------------------------------------------
    # MÉTODOS DE NEGOCIO PARA GESTIÓN DE MATERIAS PRIMAS EN USO
    # -------------------------------------------------------------------------

    def _close_active_raw_material(self, vals):
        """
        Cierra el registro activo de una materia prima específica
        utilizando los valores del nuevo registro.

        :param vals: Diccionario de valores para el nuevo registro
        :return: Recordset de los registros cerrados
        """
        product_id = vals.get("product_id")
        company_id = vals.get("company_id") or self.env.company.id
        location_id = vals.get("location_id")

        # Si no hay fecha de inicio, usar ahora (aunque create ya lo asegura)
        closing_date = vals.get("date_from") or fields.Datetime.now()

        if not product_id:
            return self.browse()

        domain = [
            ("product_id", "=", product_id),
            ("company_id", "=", company_id),
            ("date_to", "=", False),
        ]
        if location_id:
            domain.append(("location_id", "=", location_id))

        existing = self.search(domain)
        if existing:
            existing.write({"date_to": closing_date})
        return existing

    def _get_closing_key(self, vals):
        """
        Genera la clave única para identificar un producto/compañía/ubicación.

        :param vals: Diccionario de valores
        :return: Tupla (product_id, company_id, location_id)
        """
        return (
            vals.get("product_id"),
            vals.get("company_id", self.env.company.id),
            vals.get("location_id", False),
        )

    def _prepare_new_record_vals(self, record, vals):
        """
        Prepara los valores para crear un nuevo registro basado en uno existente.

        :param record: Registro original
        :param vals: Valores nuevos a aplicar
        :return: Diccionario con los valores del nuevo registro
        """
        now = fields.Datetime.now()
        return {
            "product_id": vals.get("product_id", record.product_id.id),
            "lot_id": vals["lot_id"],
            "date_from": vals.get("date_from", now),
            "company_id": vals.get("company_id", record.company_id.id),
            "location_id": vals.get(
                "location_id",
                record.location_id.id if record.location_id else False,
            ),
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Crear nuevos registros de materia prima en uso."""
        vals_list = list(vals_list)

        for vals in vals_list:
            # Asegurar fecha de inicio
            if "date_from" not in vals:
                vals["date_from"] = fields.Datetime.now()

            # Si el registro no viene cerrado, cerrar el activo anterior
            if not vals.get("date_to"):
                # Cerrar el registro activo anterior si existe
                self._close_active_raw_material(vals)

        return super().create(vals_list)

    def _process_lot_change_on_write(self, vals):
        """
        Procesa el cambio de lote: cierra registros actuales y crea nuevos.
        Retorna: los registros que no fueron afectados por el cambio (deben procesarse normalmente).
        """
        if "lot_id" not in vals:
            return self

        records_to_close = self.filtered(
            lambda r: not r.date_to and r.lot_id.id != vals.get("lot_id")
        )

        if not records_to_close:
            return self

        now = fields.Datetime.now()
        new_records_vals = []

        for record in records_to_close:
            new_records_vals.append(self._prepare_new_record_vals(record, vals))

        # Cerrar los registros actuales
        super(CdvRawMaterialInUse, records_to_close).write({"date_to": now})

        # Crear los nuevos registros
        if new_records_vals:
            super(CdvRawMaterialInUse, self).create(new_records_vals)

        return self - records_to_close

    def write(self, vals):
        """
        Cuando se cambia el lote en un registro activo, cerrar el actual y crear uno nuevo.
        Esto asegura que siempre se mantenga el historial de uso.
        """
        remaining = self._process_lot_change_on_write(vals)

        if remaining:
            return super(CdvRawMaterialInUse, remaining).write(vals)
        return True

    # -------------------------------------------------------------------------
    # MÉTODO PÚBLICO PARA PONER EN USO UNA MATERIA PRIMA
    # -------------------------------------------------------------------------

    def action_put_in_use(
        self, product_id, lot_id, date_from=None, location_id=False, company_id=False
    ):
        """
        Pone en uso una materia prima con un lote específico.
        Si ya existe una materia prima activa del mismo producto, la finaliza automáticamente
        (manejado por el método create).

        :param product_id: ID del producto a poner en uso
        :param lot_id: ID del lote
        :param date_from: Fecha de inicio (opcional, por defecto ahora)
        :param location_id: ID de la ubicación (opcional)
        :param company_id: ID de la compañía (opcional, por defecto la actual)
        :return: El nuevo registro creado
        """
        if not date_from:
            date_from = fields.Datetime.now()
        if not company_id:
            company_id = self.env.company.id

        # Crear el nuevo registro
        # La lógica de cierre del anterior se maneja automáticamente en create()
        return self.create(
            {
                "product_id": product_id,
                "lot_id": lot_id,
                "date_from": date_from,
                "company_id": company_id,
                "location_id": location_id,
            }
        )

    @api.depends("product_id", "lot_id", "date_from")
    def _compute_name(self):
        for record in self:
            if record.product_id and record.lot_id and record.date_from:
                record.name = f"{record.product_id.name} - {record.lot_id.name}"
            else:
                record.name = "Materia prima en uso"

    @api.depends("name", "date_from", "date_to")
    def _compute_display_name(self):
        for record in self:
            date_from_str = (
                fields.Datetime.to_string(record.date_from)[:10]
                if record.date_from
                else ""
            )
            if record.date_to:
                date_to_str = fields.Datetime.to_string(record.date_to)[:10]
                record.display_name = f"{record.name} ({date_from_str} - {date_to_str})"
            else:
                record.display_name = f"{record.name} (desde {date_from_str})"

    @api.depends("date_to")
    def _compute_is_in_use(self):
        for record in self:
            record.is_in_use = not record.date_to

    @api.depends("date_to")
    def _compute_state(self):
        for record in self:
            record.state = "finished" if record.date_to else "in_use"

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

    @api.constrains("product_id")
    def _check_product_is_raw_material(self):
        """Validar que el producto sea una materia prima o un producto elaborado (semi-terminado)"""
        for record in self:
            if record.product_id and not (
                record.product_id.cdv_is_raw_material
                or record.product_id.cdv_is_finished_product
            ):
                raise ValidationError(
                    _(
                        "El producto '%s' no está marcado como materia prima ni como producto elaborado.\n\n"
                        "Solo se pueden agregar productos marcados como 'Es materia prima' o 'Es producto elaborado' "
                        "en las materias primas en uso."
                    )
                    % record.product_id.name
                )

    def action_finish(self):
        """Finalizar el uso de esta materia prima"""
        self.ensure_one()
        if self.date_to:
            raise ValidationError(_("Esta materia prima ya ha sido finalizada."))

        self.date_to = fields.Datetime.now()
        return True

    def action_reopen(self):
        """Reabrir el uso de esta materia prima"""
        self.ensure_one()
        if not self.date_to:
            raise ValidationError(_("Esta materia prima ya está en uso."))

        self.date_to = False
        return True

    def unlink(self):
        """
        Permitir eliminar materias primas en uso sin restricciones.
        Útil para corregir errores de registro.
        """
        return models.Model.unlink(self)
