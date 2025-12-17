from odoo import api, fields, models
from datetime import date


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_production_entry = fields.Boolean(
        string="Es parte de producción",
        default=False,
        help="Indica si este albarán es un parte de producción",
    )
    lot_name = fields.Char(
        string="Número de lote",
        compute="_compute_lot_name",
        store=True,
        readonly=False,
        tracking=True,
        help="Número de lote que se aplicará a todos los productos elaborados en este parte",
    )

    @api.depends('is_production_entry', 'scheduled_date')
    def _compute_lot_name(self):
        """Generar número de lote por defecto con formato DDMMYY basado en la fecha planificada"""
        for picking in self:
            if picking.is_production_entry and not picking.lot_name:
                if picking.scheduled_date:
                    picking.lot_name = picking.scheduled_date.strftime("%d%m%y")
                else:
                    today = date.today()
                    picking.lot_name = today.strftime("%d%m%y")

    @api.model
    def default_get(self, fields_list):
        """Establecer valores por defecto para partes de producción"""
        res = super().default_get(fields_list)

        # Si es un parte de producción desde el contexto
        if self.env.context.get('default_is_production_entry'):
            # Partner es la propia compañía
            if 'partner_id' in fields_list:
                res['partner_id'] = self.env.company.partner_id.id

            # Tipo de operación: recepción de mercancía
            if 'picking_type_id' in fields_list:
                picking_type = self.env['stock.picking.type'].search([
                    ('code', '=', 'incoming'),
                    ('warehouse_id.company_id', '=', self.env.company.id),
                ], limit=1)
                if picking_type:
                    res['picking_type_id'] = picking_type.id

            # Ubicación de origen: Producción
            if 'location_id' in fields_list:
                production_location = self.env['stock.location'].search([
                    ('usage', '=', 'production'),
                    ('company_id', '=', self.env.company.id),
                ], limit=1)
                if production_location:
                    res['location_id'] = production_location.id

            # Ubicación de destino: Stock principal
            if 'location_dest_id' in fields_list:
                warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', self.env.company.id),
                ], limit=1)
                if warehouse:
                    res['location_dest_id'] = warehouse.lot_stock_id.id

        return res

    @api.onchange('lot_name')
    def _onchange_lot_name(self):
        """Actualizar lotes cuando cambia el número de lote en la cabecera"""
        if self.lot_name and self.is_production_entry and self.state == 'draft':
            for move in self.move_ids:
                if move.product_id.tracking in ['lot', 'serial']:
                    # Buscar o crear el lote
                    lot = self.env['stock.lot'].search([
                        ('name', '=', self.lot_name),
                        ('product_id', '=', move.product_id.id),
                        ('company_id', '=', self.company_id.id),
                    ], limit=1)

                    if not lot:
                        lot = self.env['stock.lot'].create({
                            'name': self.lot_name,
                            'product_id': move.product_id.id,
                            'company_id': self.company_id.id,
                        })

                    # Asignar el lote a las líneas de detalle del movimiento
                    for move_line in move.move_line_ids:
                        if not move_line.lot_id:
                            move_line.lot_id = lot.id
                            move_line.lot_name = lot.name

    def action_confirm(self):
        """Crear move_lines con el lote cuando se confirma el picking"""
        res = super().action_confirm()

        # Asignar lotes después de confirmar
        for picking in self:
            if picking.is_production_entry and picking.lot_name:
                for move in picking.move_ids:
                    if move.product_id.tracking in ['lot', 'serial'] and move.state not in ['done', 'cancel']:
                        # Buscar o crear el lote
                        lot = self.env['stock.lot'].search([
                            ('name', '=', picking.lot_name),
                            ('product_id', '=', move.product_id.id),
                            ('company_id', '=', picking.company_id.id),
                        ], limit=1)

                        if not lot:
                            lot = self.env['stock.lot'].create({
                                'name': picking.lot_name,
                                'product_id': move.product_id.id,
                                'company_id': picking.company_id.id,
                            })

                        # Si no hay move_lines, crearlas
                        if not move.move_line_ids:
                            move._action_assign()

                        # Asignar el lote a todas las move_lines
                        for move_line in move.move_line_ids:
                            move_line.write({
                                'lot_id': lot.id,
                                'lot_name': lot.name,
                            })

        return res

    def button_validate(self):
        """Asegurar que los lotes se asignen antes de validar"""
        for picking in self:
            if picking.is_production_entry and picking.lot_name:
                for move in picking.move_ids:
                    if move.product_id.tracking in ['lot', 'serial']:
                        # Buscar o crear el lote
                        lot = self.env['stock.lot'].search([
                            ('name', '=', picking.lot_name),
                            ('product_id', '=', move.product_id.id),
                            ('company_id', '=', picking.company_id.id),
                        ], limit=1)

                        if not lot:
                            lot = self.env['stock.lot'].create({
                                'name': picking.lot_name,
                                'product_id': move.product_id.id,
                                'company_id': picking.company_id.id,
                            })

                        # Si no hay move_lines, crearlas
                        if not move.move_line_ids:
                            move._action_assign()

                        # Asignar el lote a las líneas de detalle del movimiento
                        for move_line in move.move_line_ids:
                            move_line.write({
                                'lot_id': lot.id,
                                'lot_name': lot.name,
                            })

        return super().button_validate()

    def action_process_production(self):
        """Procesar parte de producción: asignar cantidades, asignar lotes y validar en un solo paso"""
        self.ensure_one()

        if not self.is_production_entry:
            return

        # 1. Confirmar el picking si está en borrador
        if self.state == 'draft':
            self.action_confirm()

        # 2. Asignar disponibilidad (crear move_lines)
        if self.state in ['confirmed', 'waiting', 'assigned']:
            self.action_assign()

        # 3. Asignar cantidades y lotes a todas las líneas
        if self.lot_name:
            for move in self.move_ids:
                if move.product_id.tracking in ['lot', 'serial']:
                    # Buscar o crear el lote
                    lot = self.env['stock.lot'].search([
                        ('name', '=', self.lot_name),
                        ('product_id', '=', move.product_id.id),
                        ('company_id', '=', self.company_id.id),
                    ], limit=1)

                    if not lot:
                        lot = self.env['stock.lot'].create({
                            'name': self.lot_name,
                            'product_id': move.product_id.id,
                            'company_id': self.company_id.id,
                        })

                    # Asignar cantidad completa y lote a cada move_line
                    for move_line in move.move_line_ids:
                        move_line.write({
                            'quantity': move_line.quantity,
                            'lot_id': lot.id,
                            'lot_name': lot.name,
                        })

        # 4. Validar el albarán
        if self.state == 'assigned':
            return self.button_validate()

        return True
