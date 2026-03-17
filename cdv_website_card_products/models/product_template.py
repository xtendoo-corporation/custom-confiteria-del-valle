from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_selection_short_description = fields.Char(
        string='Descripción corta',
        translate=True,
        help='A short description for the premium product card in the website selection page.'
    )

    allergen_ids = fields.Many2many(
        'product.allergen',
        string='Alergenos',
        help='Select allergens for this product.'
    )
