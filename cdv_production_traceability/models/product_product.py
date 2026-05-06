import logging

from odoo import api, models
from odoo.fields import Domain


_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _cdv_finished_product_domain(self):
        return Domain(
            [
                ("cdv_is_finished_product", "=", True),
                ("is_storable", "=", True),
                ("tracking", "in", ["lot", "serial"]),
            ]
        )

    def _cdv_should_limit_finished_products(self):
        ctx = self.env.context
        if ctx.get("cdv_limit_finished_products_for_production_entry"):
            return True
        if ctx.get("default_is_production_entry"):
            return True

        default_picking_id = ctx.get("default_picking_id")
        if default_picking_id:
            picking = self.env["stock.picking"].browse(default_picking_id)
            if picking.exists() and picking.is_production_entry:
                return True

        if ctx.get("active_model") == "stock.picking" and ctx.get("active_id"):
            picking = self.env["stock.picking"].browse(ctx["active_id"])
            if picking.exists() and picking.is_production_entry:
                return True

        return False

    def _cdv_debug_log_filter(self, source, domain):
        if self.env.context.get("cdv_debug_product_filter"):
            _logger.warning(
                "[CDV FILTER][%s] ctx=%s domain=%s",
                source,
                {
                    "default_is_production_entry": self.env.context.get(
                        "default_is_production_entry"
                    ),
                    "cdv_limit_finished_products_for_production_entry": self.env.context.get(
                        "cdv_limit_finished_products_for_production_entry"
                    ),
                    "active_model": self.env.context.get("active_model"),
                    "active_id": self.env.context.get("active_id"),
                    "default_picking_id": self.env.context.get("default_picking_id"),
                },
                domain,
            )

    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        if self._cdv_should_limit_finished_products():
            domain = Domain(domain or Domain.TRUE) & self._cdv_finished_product_domain()
        self._cdv_debug_log_filter("_search", domain)
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            **kwargs,
        )

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        if self._cdv_should_limit_finished_products():
            domain = Domain(domain or Domain.TRUE) & self._cdv_finished_product_domain()
        self._cdv_debug_log_filter("name_search", domain)
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

