from odoo import api, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        if self.env.context.get("cdv_limit_finished_products_for_production_entry"):
            domain = Domain(domain or Domain.TRUE) & Domain(
                [
                    ("cdv_is_finished_product", "=", True),
                    ("is_storable", "=", True),
                    ("tracking", "in", ["lot", "serial"]),
                ]
            )
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

