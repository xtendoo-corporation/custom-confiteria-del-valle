from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CdvProductionEntry(models.Model):
    _name = 'cdv.production.entry'
    _description = 'Parte de producción diaria'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Número',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
        tracking=True,
    )
    date = fields.Date(
        string='Fecha de producción',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('done', 'Confirmado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Albarán de entrada',
        readonly=True,
        copy=False,
        tracking=True,
    )
    picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Tipo de albarán',
        required=True,
        default=lambda self: self._default_picking_type_id(),
    )
    location_src_id = fields.Many2one(
        comodel_name='stock.location',
        string='Ubicación origen',
        compute='_compute_locations',
        store=True,
    )
    location_dest_id = fields.Many2one(
        comodel_name='stock.location',
        string='Ubicación destino',
        compute='_compute_locations',
        store=True,
    )
    line_ids = fields.One2many(
        comodel_name='cdv.production.entry.line',
        inverse_name='entry_id',
        string='Líneas de producción',
        copy=True,
    )
    total_lines = fields.Integer(
        string='Total líneas',
        compute='_compute_total_lines',
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        tracking=True,
    )
    notes = fields.Text(
        string='Notas',
    )

    def _default_picking_type_id(self):
        """Obtener tipo de albarán por defecto desde configuración"""
        picking_type_id = self.env['ir.config_parameter'].sudo().get_param(
            'cdv_production_traceability.finished_picking_type_id'
        )
        if picking_type_id:
            return int(picking_type_id)

        # Fallback: buscar tipo de albarán de entrada en el almacén principal
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', self.env.company.id),
        ], limit=1)
        return picking_type.id if picking_type else False

    @api.depends('picking_type_id')
    def _compute_locations(self):
        """Calcular ubicaciones origen y destino desde tipo de albarán o configuración"""
        for record in self:
            if record.picking_type_id:
                record.location_src_id = record.picking_type_id.default_location_src_id
                record.location_dest_id = record.picking_type_id.default_location_dest_id
            else:
                # Usar ubicaciones de configuración como fallback
                finished_location = self.env['ir.config_parameter'].sudo().get_param(
                    'cdv_production_traceability.finished_location_id'
                )
                record.location_dest_id = int(finished_location) if finished_location else False
                record.location_src_id = False

    @api.depends('line_ids')
    def _compute_total_lines(self):
        for record in self:
            record.total_lines = len(record.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('cdv.production.entry') or _('Nuevo')
        return super().create(vals_list)

    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_('No puede eliminar un parte de producción confirmado.'))
        return super().unlink()

    def action_confirm(self):
        """Confirmar el parte de producción y generar albarán de entrada"""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_('Solo puede confirmar partes en estado Borrador.'))

        if not self.line_ids:
            raise UserError(_('Debe añadir al menos una línea de producción.'))

        # Validar que todos los productos tienen BoM
        self._validate_bom_exists()

        # Generar o actualizar lotes automáticamente
        self._generate_finished_lots()

        # Crear albarán de entrada
        self._create_incoming_picking()

        self.state = 'done'

        return True

    def action_cancel(self):
        """Cancelar el parte de producción"""
        self.ensure_one()

        if self.picking_id and self.picking_id.state == 'done':
            raise UserError(_('No puede cancelar un parte cuyo albarán ya está validado.'))

        if self.picking_id:
            self.picking_id.action_cancel()

        self.state = 'cancelled'
        return True

    def action_draft(self):
        """Volver a borrador"""
        self.ensure_one()

        if self.picking_id:
            raise UserError(_('No puede volver a borrador un parte que tiene albarán asociado.'))

        self.state = 'draft'
        return True

    def action_view_picking(self):
        """Abrir el albarán asociado"""
        self.ensure_one()

        if not self.picking_id:
            raise UserError(_('Este parte no tiene albarán asociado.'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
            'target': 'current',
        }

    def _validate_bom_exists(self):
        """Validar que todos los productos finales tienen BoM definida"""
        products_without_bom = []

        for line in self.line_ids:
            if not line.product_id.bom_ids and not self.env['mrp.bom'].search([
                ('product_id', '=', line.product_id.id),
                '|',
                ('company_id', '=', False),
                ('company_id', '=', self.company_id.id),
            ], limit=1):
                products_without_bom.append(line.product_id.display_name)

        if products_without_bom:
            raise ValidationError(
                _('Los siguientes productos no tienen lista de materiales definida:\n\n%s\n\n'
                  'Por favor, cree las listas de materiales antes de confirmar el parte.',
                  '\n'.join(f'• {p}' for p in products_without_bom))
            )

    def _generate_finished_lots(self):
        """Generar lotes automáticamente para productos terminados sin lote"""
        lot_name = self.date.strftime('%d-%m-%y')

        for line in self.line_ids:
            if not line.lot_id:
                # Buscar lote existente con este nombre
                lot = self.env['stock.lot'].search([
                    ('name', '=', lot_name),
                    ('product_id', '=', line.product_id.id),
                    ('company_id', '=', self.company_id.id),
                ], limit=1)

                # Si no existe, crearlo
                if not lot:
                    lot = self.env['stock.lot'].create({
                        'name': lot_name,
                        'product_id': line.product_id.id,
                        'company_id': self.company_id.id,
                    })

                line.lot_id = lot

    def _create_incoming_picking(self):
        """Crear albarán de entrada con los productos terminados"""
        self.ensure_one()

        if not self.location_src_id or not self.location_dest_id:
            raise UserError(
                _('No se han configurado las ubicaciones de origen y destino.\n'
                  'Por favor, configure el tipo de albarán correctamente.')
            )

        # Crear albarán
        picking_vals = {
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'scheduled_date': self.date,
            'move_ids_without_package': [],
        }

        # Crear movimientos para cada línea
        for line in self.line_ids:
            move_vals = {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.location_dest_id.id,
                'company_id': self.company_id.id,
            }
            picking_vals['move_ids_without_package'].append((0, 0, move_vals))

        picking = self.env['stock.picking'].create(picking_vals)

        # Confirmar el albarán
        picking.action_confirm()

        # Asignar lotes a las líneas de movimiento
        for line in self.line_ids:
            move = picking.move_ids_without_package.filtered(
                lambda m: m.product_id == line.product_id
            )[:1]

            if move and line.lot_id:
                # Crear move line con el lote
                move_line_vals = {
                    'move_id': move.id,
                    'product_id': line.product_id.id,
                    'lot_id': line.lot_id.id,
                    'quantity': line.quantity,
                    'product_uom_id': line.uom_id.id,
                    'location_id': self.location_src_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'company_id': self.company_id.id,
                }
                self.env['stock.move.line'].create(move_line_vals)

        # Validar el albarán automáticamente (configurable)
        auto_validate = self.env['ir.config_parameter'].sudo().get_param(
            'cdv_production_traceability.auto_validate_picking', 'False'
        )
        if auto_validate == 'True':
            picking.button_validate()

        self.picking_id = picking

