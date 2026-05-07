import logging

from odoo import api, models
from odoo.fields import Domain


_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @staticmethod
    def _cdv_context_truthy(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
        return False

    def _cdv_finished_product_domain(self):
        return Domain(
            [
                ("product_tmpl_id.cdv_is_finished_product", "=", True),
                ("is_storable", "=", True),
                ("tracking", "in", ["lot", "serial"]),
            ]
        )

    def _cdv_should_limit_finished_products(self):
        ctx = self.env.context
        params = ctx.get("params") if isinstance(ctx.get("params"), dict) else {}
        for key in (
            "cdv_limit_finished_products_for_production_entry",
            "cdv_picking_is_production_entry",
            "default_cdv_picking_is_production_entry",
            "default_is_production_entry",
            "is_production_entry",
        ):
            if self._cdv_context_truthy(ctx.get(key)):
                if self.env.context.get("cdv_debug_product_filter"):
                    _logger.warning(
                        "[CDV FILTER][decision] enabled_by=%s ctx=%s",
                        key,
                        {
                            "default_is_production_entry": ctx.get("default_is_production_entry"),
                            "cdv_picking_is_production_entry": ctx.get("cdv_picking_is_production_entry"),
                            "default_cdv_picking_is_production_entry": ctx.get(
                                "default_cdv_picking_is_production_entry"
                            ),
                            "cdv_limit_finished_products_for_production_entry": ctx.get(
                                "cdv_limit_finished_products_for_production_entry"
                            ),
                            "active_model": ctx.get("active_model"),
                            "active_id": ctx.get("active_id"),
                            "default_picking_id": ctx.get("default_picking_id"),
                            "params": params,
                        },
                    )
                return True

        if params.get("view_type") == "form" and self._cdv_context_truthy(
            params.get("default_is_production_entry")
        ):
            if self.env.context.get("cdv_debug_product_filter"):
                _logger.warning(
                    "[CDV FILTER][decision] enabled_by=params.default_is_production_entry ctx=%s",
                    {
                        "params": params,
                        "default_picking_id": ctx.get("default_picking_id"),
                    },
                )
            return True

        default_picking_id = ctx.get("default_picking_id")
        normalized_default_picking_id = None
        if isinstance(default_picking_id, int):
            normalized_default_picking_id = default_picking_id
        elif isinstance(default_picking_id, str) and default_picking_id.isdigit():
            normalized_default_picking_id = int(default_picking_id)

        if normalized_default_picking_id:
            picking = self.env["stock.picking"].browse(normalized_default_picking_id)
            if picking.exists() and getattr(picking, "is_production_entry", False):
                if self.env.context.get("cdv_debug_product_filter"):
                    _logger.warning(
                        "[CDV FILTER][decision] enabled_by=default_picking_id picking=%s",
                        normalized_default_picking_id,
                    )
                return True

        active_id = ctx.get("active_id")
        normalized_active_id = None
        if isinstance(active_id, int):
            normalized_active_id = active_id
        elif isinstance(active_id, str) and active_id.isdigit():
            normalized_active_id = int(active_id)

        if ctx.get("active_model") == "stock.picking" and normalized_active_id:
            picking = self.env["stock.picking"].browse(normalized_active_id)
            if picking.exists() and getattr(picking, "is_production_entry", False):
                if self.env.context.get("cdv_debug_product_filter"):
                    _logger.warning(
                        "[CDV FILTER][decision] enabled_by=active_id picking=%s",
                        normalized_active_id,
                    )
                return True

        if self.env.context.get("cdv_debug_product_filter"):
            _logger.warning(
                "[CDV FILTER][decision] disabled ctx=%s",
                {
                    "default_is_production_entry": ctx.get("default_is_production_entry"),
                    "cdv_picking_is_production_entry": ctx.get("cdv_picking_is_production_entry"),
                    "default_cdv_picking_is_production_entry": ctx.get(
                        "default_cdv_picking_is_production_entry"
                    ),
                    "cdv_limit_finished_products_for_production_entry": ctx.get(
                        "cdv_limit_finished_products_for_production_entry"
                    ),
                    "active_model": ctx.get("active_model"),
                    "active_id": ctx.get("active_id"),
                    "default_picking_id": ctx.get("default_picking_id"),
                    "params": params,
                },
            )

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
                    "cdv_picking_is_production_entry": self.env.context.get(
                        "cdv_picking_is_production_entry"
                    ),
                    "default_cdv_picking_is_production_entry": self.env.context.get(
                        "default_cdv_picking_is_production_entry"
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
        self._cdv_debug_log_filter(
            f"name_search name={name!r} operator={operator} limit={limit}", domain
        )
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

    @api.model
    def web_name_search(self, name, specification, domain=None, operator="ilike", limit=100):
        result = super().web_name_search(
            name,
            specification,
            domain=domain,
            operator=operator,
            limit=limit,
        )
        if self.env.context.get("cdv_debug_product_filter"):
            _logger.warning(
                "[CDV FILTER][web_name_search name=%r operator=%s limit=%s] ctx=%s incoming_domain=%s result=%s",
                name,
                operator,
                limit,
                {
                    "default_is_production_entry": self.env.context.get("default_is_production_entry"),
                    "cdv_picking_is_production_entry": self.env.context.get(
                        "cdv_picking_is_production_entry"
                    ),
                    "default_cdv_picking_is_production_entry": self.env.context.get(
                        "default_cdv_picking_is_production_entry"
                    ),
                    "cdv_limit_finished_products_for_production_entry": self.env.context.get(
                        "cdv_limit_finished_products_for_production_entry"
                    ),
                    "default_picking_id": self.env.context.get("default_picking_id"),
                },
                domain,
                [
                    {
                        "id": rec.get("id"),
                        "display_name": rec.get("display_name"),
                    }
                    for rec in result
                ],
            )
        return result

