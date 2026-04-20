from odoo import http
from odoo.http import request


class WebsiteCardProducts(http.Controller):

    @http.route(["/alergenos"], type="http", auth="public", website=True)
    def selection_page(self, **post):
        # Fetch categories - If none exist, use a default list based on the design
        categories = request.env["product.public.category"].search(
            [("parent_id", "=", False)]
        )

        # If no categories are defined in Odoo, we provide the names for the sidebar UI
        default_category_names = [
            "Pasteles y Tartas",
            "Bollería Creativa",
            "Pastas de Té",
            "Chocolates y Bombones",
            "Postres de Temporada",
            "Opciones Veganas/Sin Gluten",
        ]

        # Allergen exclusion logic
        exclude_allergen_ids = []
        if post.get("exclude_allergens"):
            try:
                exclude_allergen_ids = [
                    int(i) for i in post.get("exclude_allergens").split(",")
                ]
            except ValueError:
                exclude_allergen_ids = []

        domain = [("is_published", "=", True), ("sale_ok", "=", True)]

        if exclude_allergen_ids:
            # Exclude products that have ANY of the excluded allergens
            domain.append(("allergen_ids", "not in", exclude_allergen_ids))

        products = request.env["product.template"].search(
            domain,
            order="allergen_page_sequence ASC NULLS LAST, name ASC",
        )
        allergens = request.env["product.allergen"].search([])

        values = {
            "categories": categories,
            "default_category_names": default_category_names,
            "products": products,
            "allergens": allergens,
            "exclude_allergen_ids": exclude_allergen_ids,
        }
        return request.render("cdv_website_card_products.alergenos", values)
