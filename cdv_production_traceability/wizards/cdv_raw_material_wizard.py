from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CdvRawMaterialWizard(models.TransientModel):
    _name = 'cdv.raw.material.wizard'
    _description = 'Asistente para poner materias primas en producción'

    step = fields.Selection(
        selection=[
            ('select_product', 'Seleccionar producto'),
            ('select_lot', 'Seleccionar lote'),
        ],
        string='Paso',
        default='select_product',
        required=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Materia prima',
        domain=[('detailed_type', '=', 'product')],
    )
    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Lote',
    )
    date_from = fields.Datetime(
        string='Fecha inicio uso',
        default=fields.Datetime.now,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Ubicación',
    )
    available_lot_ids = fields.Many2many(
        comodel_name='stock.lot',
        string='Lotes disponibles',
        compute='_compute_available_lot_ids',
    )

    @api.depends('product_id', 'company_id')
    def _compute_available_lot_ids(self):
        """Calcular lotes disponibles con stock positivo"""
        for wizard in self:
            if not wizard.product_id:
                wizard.available_lot_ids = False
                continue

            # Buscar lotes con stock
            quants = self.env['stock.quant'].search([
                ('product_id', '=', wizard.product_id.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ])

            wizard.available_lot_ids = quants.mapped('lot_id')

    def action_select_product(self):
        """Seleccionar producto y pasar al siguiente paso"""
        self.ensure_one()

        if not self.product_id:
            raise UserError(_('Debe seleccionar una materia prima.'))

        self.step = 'select_lot'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cdv.raw.material.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_back(self):
        """Volver al paso anterior"""
        self.ensure_one()
        self.step = 'select_product'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cdv.raw.material.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_put_in_production(self):
        """Poner materia prima en producción"""
        self.ensure_one()

        if not self.product_id or not self.lot_id:
            raise UserError(_('Debe seleccionar una materia prima y un lote.'))

        # Cerrar registros anteriores del mismo producto
        previous_records = self.env['cdv.raw.material.in.use'].search([
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.company_id.id),
            ('date_to', '=', False),
        ])

        if previous_records:
            previous_records.write({'date_to': self.date_from})

        # Crear nuevo registro
        raw_material = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_id.id,
            'lot_id': self.lot_id.id,
            'date_from': self.date_from,
            'company_id': self.company_id.id,
            'location_id': self.location_id.id if self.location_id else False,
        })

        # Mostrar mensaje de éxito
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('¡Éxito!'),
                'message': _('Materia prima %s con lote %s puesta en producción.',
                           self.product_id.display_name, self.lot_id.name),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window_close',
                },
            }
        }

