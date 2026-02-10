from odoo import api, fields, models, _


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    @api.onchange("product_id")
    def _onchange_product_id_uom_production_preferred(self):
        """
        Al cambiar el producto, aplicar la UoM de producción preferida si existe.
        Solo se aplica si el producto tiene configurada una UoM preferida para producción.
        """
        if self.product_id and self.product_id.uom_production_preferred_id:
            # Aplicar la UoM preferida
            self.product_uom_id = self.product_id.uom_production_preferred_id
        elif self.product_id:
            # Comportamiento estándar: usar la UoM base del producto
            self.product_uom_id = self.product_id.uom_id

    @api.onchange("product_uom_id")
    def _onchange_product_uom_id_check_category(self):
        """
        Validar que la UdM seleccionada manualmente pertenezca a la misma categoría
        que la UdM base del producto.
        """
        if self.product_id and self.product_uom_id:
            if not self.product_uom_id._has_common_reference(self.product_id.uom_id):
                uom_base_root_id = int(self.product_id.uom_id.parent_path.split("/")[0])
                uom_base_root = self.env["uom.uom"].browse(uom_base_root_id)
                return {
                    "warning": {
                        "title": _("UdM incompatible"),
                        "message": _(
                            'La UdM seleccionada "%s" no pertenece al mismo sistema de referencia '
                            'que la UdM base del producto "%s".\n\n'
                            "Se recomienda usar una UdM asociada a: %s"
                        )
                        % (
                            self.product_uom_id.name,
                            self.product_id.uom_id.name,
                            uom_base_root.name,
                        ),
                    }
                }
