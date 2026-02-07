from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        """
        Validar al escribir movimientos que pertenezcan a partes de producción
        """
        result = super(StockMove, self).write(vals)

        # Si se está actualizando el producto, validar
        if 'product_id' in vals:
            for move in self:
                if move.picking_id and move.picking_id.is_production_entry:
                    self._validate_production_product(move.product_id)

        return result

    @api.model_create_multi
    def create(self, vals_list):
        """
        Validar al crear movimientos que pertenezcan a partes de producción
        """
        moves = super(StockMove, self).create(vals_list)

        for move in moves:
            if move.picking_id and move.picking_id.is_production_entry:
                self._validate_production_product(move.product_id)

        return moves

    def _validate_production_product(self, product):
        """
        Método auxiliar para validar que un producto cumpla con los requisitos
        de los partes de producción
        """
        if not product:
            return

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

    def _action_cancel(self):
        """
        Permitir cancelar movimientos incluso si están en estado 'done'.
        Sobrescribimos completamente la lógica para evitar la validación del estado.
        """
        # Cambiar directamente el estado sin validaciones
        self.sudo().write({'state': 'cancel'})
        return True

    def action_cancel(self):
        """
        Sobrescribir el método público de cancelación.
        """
        return self._action_cancel()

    def unlink(self):
        """
        Permitir borrar movimientos de stock sin importar su estado.
        Saltamos las validaciones estándar usando el método unlink del modelo base.
        """
        return models.Model.unlink(self)

