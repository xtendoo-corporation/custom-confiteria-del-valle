import logging
from xml.etree import ElementTree as ET

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date


_logger = logging.getLogger(__name__)

_CDV_INTERNAL_FINISHED_PRODUCT_DOMAIN = [
    ('product_tmpl_id.cdv_is_finished_product', '=', True),
    ('is_storable', '=', True),
]


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _cdv_is_internal_finished_transfer(self):
        self.ensure_one()
        return self.picking_type_id.code == 'internal' and not self.is_production_entry

    def action_import_finished_products(self):
        self.ensure_one()

        if not self._cdv_is_internal_finished_transfer() or self.state != 'draft':
            return False

        existing_products = self.move_ids.filtered(
            lambda move: move.state != 'cancel'
        ).mapped('product_id')
        products_to_add = self.env['product.product'].search(
            _CDV_INTERNAL_FINISHED_PRODUCT_DOMAIN
        ) - existing_products

        move_vals_list = []
        for product in products_to_add:
            move_vals_list.append(
                {
                    'picking_id': self.id,
                    'product_id': product.id,
                    'product_uom_qty': 0.0,
                    'product_uom': product.uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                }
            )

        if move_vals_list:
            self.env['stock.move'].create(move_vals_list)

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_import_stock_lots_from_source(self):
        self.ensure_one()

        if not self._cdv_is_internal_finished_transfer() or self.state != 'draft':
            return False

        existing_pairs = {
            (line.product_id.id, line.lot_id.id)
            for line in self.move_line_ids.filtered(lambda line: line.lot_id and line.state != 'cancel')
        }
        quant_domain = [
            ('location_id', 'child_of', self.location_id.id),
            ('quantity', '>', 0),
            ('lot_id', '!=', False),
            ('product_id.is_storable', '=', True),
        ]
        quants = self.env['stock.quant'].search(quant_domain, order='product_id, lot_id, in_date, id')

        move_vals_list = []
        for quant in quants:
            pair = (quant.product_id.id, quant.lot_id.id)
            if pair in existing_pairs:
                continue

            available_qty = quant.quantity - quant.reserved_quantity
            if quant.product_uom_id.is_zero(available_qty):
                continue

            move_vals_list.append(
                {
                    'picking_id': self.id,
                    'product_id': quant.product_id.id,
                    'product_uom_qty': available_qty,
                    'product_uom': quant.product_uom_id.id,
                    'location_id': quant.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'move_line_ids': [
                        (
                            0,
                            0,
                            {
                                'picking_id': self.id,
                                'product_id': quant.product_id.id,
                                'product_uom_id': quant.product_uom_id.id,
                                'quantity': available_qty,
                                'location_id': quant.location_id.id,
                                'location_dest_id': self.location_dest_id.id,
                                'lot_id': quant.lot_id.id,
                            },
                        )
                    ],
                }
            )
            existing_pairs.add(pair)

        if move_vals_list:
            self.env['stock.move'].create(move_vals_list)

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _cdv_prepare_internal_finished_transfer_validation(self):
        for picking in self.filtered(lambda item: item._cdv_is_internal_finished_transfer()):
            zero_qty_moves = picking.move_ids.filtered(
                lambda move: move.state not in ['done', 'cancel']
                and move.product_uom.is_zero(move.product_uom_qty)
            )
            if zero_qty_moves:
                zero_qty_moves.unlink()

    def _cdv_debug_log_production_view(self, result, view_id, view_type):
        if view_type != 'form' or not self.env.context.get('cdv_debug_product_filter'):
            return
        try:
            arch = result.get('arch') or ''
            root = ET.fromstring(arch)
            product_node = None
            move_node = None
            for node in root.iter('field'):
                if node.attrib.get('name') == 'move_ids' and move_node is None:
                    move_node = node
                if node.attrib.get('name') == 'product_id':
                    product_node = node
                    break
            _logger.warning(
                '[CDV VIEW] stock.picking.get_view view_id=%s view_type=%s ctx=%s move_ids_context=%s product_domain=%s product_context=%s widget=%s',
                view_id,
                view_type,
                {
                    'default_is_production_entry': self.env.context.get('default_is_production_entry'),
                    'cdv_limit_finished_products_for_production_entry': self.env.context.get('cdv_limit_finished_products_for_production_entry'),
                    'cdv_debug_product_filter': self.env.context.get('cdv_debug_product_filter'),
                    'params': self.env.context.get('params'),
                },
                move_node.attrib.get('context') if move_node is not None else None,
                product_node.attrib.get('domain') if product_node is not None else None,
                product_node.attrib.get('context') if product_node is not None else None,
                product_node.attrib.get('widget') if product_node is not None else None,
            )
        except Exception as err:  # pragma: no cover - depuración defensiva
            _logger.warning('[CDV VIEW] Error registrando vista de producción: %s', err)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        self._cdv_debug_log_production_view(result, view_id, view_type)
        return result

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

    @api.constrains('move_ids', 'is_production_entry')
    def _check_production_entry_products(self):
        """
        Validar que solo se puedan agregar productos almacenables y con seguimiento por lotes
        en los partes de producción
        """
        for picking in self:
            if picking.is_production_entry:
                for move in picking.move_ids:
                    product = move.product_id

                    # Verificar que el producto esté marcado como producto elaborado
                    if not product.cdv_is_finished_product:
                        raise ValidationError(
                            _("El producto '%s' no está marcado como producto elaborado.\n\n"
                              "Solo se pueden agregar productos marcados como 'Es producto elaborado' "
                              "en los partes de producción.")
                            % product.name
                        )

                    # Verificar que el producto sea almacenable (is_storable = True)
                    if not product.is_storable:
                        raise ValidationError(
                            _("El producto '%s' no es almacenable.\n\n"
                              "Solo se pueden agregar productos almacenables (con 'Puede almacenarse' activado) "
                              "en los partes de producción para garantizar la trazabilidad.")
                            % product.name
                        )

                    # Verificar que el producto tenga seguimiento por lotes o número de serie
                    if product.tracking not in ['lot', 'serial']:
                        raise ValidationError(
                            _("El producto '%s' no tiene seguimiento por lotes/número de serie.\n\n"
                              "Solo se pueden agregar productos con seguimiento por lotes o números de serie "
                              "en los partes de producción para garantizar la trazabilidad correcta en los informes.")
                            % product.name
                        )

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
        self._cdv_prepare_internal_finished_transfer_validation()

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

    def action_cancel(self):
        """
        Permitir cancelar albaranes incluso si están en estado 'done'.
        Forzamos el estado de los movimientos a 'cancel' para evitar la validación estándar.
        """
        for picking in self:
            # Cambiar el estado de los movimientos relacionados directamente usando sudo
            picking.move_ids.sudo().write({'state': 'cancel'})
            # Cambiar el estado del picking también
            picking.sudo().write({'state': 'cancel'})
        return True

    def unlink(self):
        """
        Permitir borrar albaranes sin importar su estado.
        Saltamos las validaciones estándar usando el método unlink del modelo base.
        """
        return models.Model.unlink(self)

