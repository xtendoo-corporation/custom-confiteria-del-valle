{
    "name": "Dulzuras del Sur - Website Card Products",
    "version": "1.0",
    "summary": "Premium product menu for Confitería Dulzuras del Sur",
    "description": """
        This module adds a custom product menu ("Nuestra Carta") to the website,
        with a premium layout, category sidebar, and high-quality product cards.
    """,
    "category": "Website/Website",
    "author": "Abraham, Endika (Xtendoo)",
    "depends": ["website", "website_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/website_templates.xml",
        "data/website_menu.xml",
        "views/product_allergen_views.xml",
        "views/product_template_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "cdv_website_card_products/static/src/scss/website_card_products.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
