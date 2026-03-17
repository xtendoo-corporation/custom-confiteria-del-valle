from odoo import fields, models

class ProductAllergen(models.Model):
    _name = 'product.allergen'
    _description = 'Product Allergen'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre Alergeno', required=True, translate=True)
    image = fields.Binary(string='Logo', required=True, help='Icon/Logo representing the allergen')
    sequence = fields.Integer(default=10)
