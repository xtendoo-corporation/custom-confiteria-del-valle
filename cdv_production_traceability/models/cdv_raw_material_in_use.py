from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CdvRawMaterialInUse(models.Model):
    _name = 'cdv.raw.material.in.use'
    _description = 'Materia prima en uso'
    _order = 'date_from desc, id desc'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Nombre',
        compute='_compute_name',
        store=True,
    )
    display_name = fields.Char(
        string='Nombre completo',
        compute='_compute_display_name',
        store=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Materia prima',
        required=True,
        domain=[('detailed_type', '=', 'product')],
        index=True,
    )
    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Lote',
        required=True,
        index=True,
    )
    date_from = fields.Datetime(
        string='Fecha inicio uso',
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    date_to = fields.Datetime(
        string='Fecha fin uso',
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Ubicación',
        help='Ubicación donde se usa esta materia prima',
    )
    active = fields.Boolean(
        string='Activo',
        compute='_compute_active',
        store=True,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ('in_use', 'En uso'),
            ('finished', 'Finalizado'),
        ],
        string='Estado',
        compute='_compute_state',
        store=True,
    )
    available_qty = fields.Float(
        string='Cantidad disponible',
        compute='_compute_available_qty',
        help='Cantidad disponible del lote en la ubicación configurada',
    )

    @api.depends('product_id', 'lot_id', 'date_from')
    def _compute_name(self):
        for record in self:
            if record.product_id and record.lot_id and record.date_from:
                record.name = f"{record.product_id.name} - {record.lot_id.name}"
            else:
                record.name = 'Materia prima en uso'

    @api.depends('name', 'date_from', 'date_to')
    def _compute_display_name(self):
        for record in self:
            date_from_str = fields.Datetime.to_string(record.date_from)[:10] if record.date_from else ''
            if record.date_to:
                date_to_str = fields.Datetime.to_string(record.date_to)[:10]
                record.display_name = f"{record.name} ({date_from_str} - {date_to_str})"
            else:
                record.display_name = f"{record.name} (desde {date_from_str})"

    @api.depends('date_to')
    def _compute_active(self):
        for record in self:
            record.active = not record.date_to

    @api.depends('date_to')
    def _compute_state(self):
        for record in self:
            record.state = 'finished' if record.date_to else 'in_use'

    @api.depends('product_id', 'lot_id', 'location_id')
    def _compute_available_qty(self):
        for record in self:
            if not record.product_id or not record.lot_id:
                record.available_qty = 0.0
                continue

            domain = [
                ('product_id', '=', record.product_id.id),
                ('lot_id', '=', record.lot_id.id),
            ]

            if record.location_id:
                domain.append(('location_id', '=', record.location_id.id))

            quants = self.env['stock.quant'].search(domain)
            record.available_qty = sum(quants.mapped('quantity'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Limpiar lote cuando cambia el producto"""
        if self.product_id:
            self.lot_id = False
            return {
                'domain': {
                    'lot_id': [
                        ('product_id', '=', self.product_id.id),
                        ('company_id', '=', self.company_id.id),
                    ]
                }
            }
        return {'domain': {'lot_id': []}}

    @api.constrains('product_id', 'company_id', 'date_from', 'date_to')
    def _check_single_active_per_product(self):
        """Validar que solo haya un registro activo por producto y compañía"""
        for record in self:
            if record.date_to:
                continue

            domain = [
                ('product_id', '=', record.product_id.id),
                ('company_id', '=', record.company_id.id),
                ('date_to', '=', False),
                ('id', '!=', record.id),
            ]

            if record.location_id:
                domain.append(('location_id', '=', record.location_id.id))

            existing = self.search(domain, limit=1)
            if existing:
                raise ValidationError(
                    _('Ya existe una materia prima en uso para el producto "%s".\n'
                      'Por favor, finalice el uso del lote actual antes de iniciar uno nuevo.',
                      record.product_id.name)
                )

    def action_finish(self):
        """Finalizar el uso de esta materia prima"""
        self.ensure_one()
        if self.date_to:
            raise ValidationError(_('Esta materia prima ya ha sido finalizada.'))

        self.date_to = fields.Datetime.now()
        return True

    def action_reopen(self):
        """Reabrir el uso de esta materia prima"""
        self.ensure_one()
        if not self.date_to:
            raise ValidationError(_('Esta materia prima ya está en uso.'))

        self.date_to = False
        return True

