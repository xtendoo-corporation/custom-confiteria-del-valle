from odoo.tests.common import TransactionCase


class TestMrpProductionUomPreferred(TransactionCase):
    """Tests para aplicación automática de UoM en Manufacturing Orders"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear UoMs
        cls.uom_category_unit = cls.env.ref('uom.product_uom_categ_unit')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Crear UoM caja
        cls.uom_box = cls.env['uom.uom'].search([
            ('name', '=', 'Caja'),
            ('category_id', '=', cls.uom_category_unit.id)
        ], limit=1)

        if not cls.uom_box:
            cls.uom_box = cls.env['uom.uom'].create({
                'name': 'Caja',
                'category_id': cls.uom_category_unit.id,
                'factor_inv': 12.0,
                'uom_type': 'bigger',
                'rounding': 1.0,
            })

        # Crear producto con UoM preferida
        cls.product_with_preferred = cls.env['product.product'].create({
            'name': 'Product with Preferred UoM for Production',
            'type': 'product',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'uom_production_preferred_id': cls.uom_box.id,
        })

        # Crear producto sin UoM preferida
        cls.product_without_preferred = cls.env['product.product'].create({
            'name': 'Product without Preferred UoM',
            'type': 'product',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
        })

        # Crear BoM para el producto con preferida
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_with_preferred.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
        })

        # Crear ubicación
        cls.location = cls.env.ref('stock.stock_location_stock')

    def test_01_mo_creation_with_preferred_uom(self):
        """Test: Al crear MO con producto que tiene UoM preferida, debe aplicarse"""
        mo = self.env['mrp.production'].create({
            'product_id': self.product_with_preferred.id,
            'product_qty': 2.0,
            'bom_id': self.bom.id,
            'location_src_id': self.location.id,
            'location_dest_id': self.location.id,
        })

        self.assertEqual(
            mo.product_uom_id,
            self.uom_box,
            "La UoM de la MO debe ser la preferida (Caja)"
        )

    def test_02_mo_creation_without_preferred_uom(self):
        """Test: MO sin UoM preferida usa la UoM base"""
        # Crear BoM para producto sin preferida
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_without_preferred.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
        })

        mo = self.env['mrp.production'].create({
            'product_id': self.product_without_preferred.id,
            'product_qty': 1.0,
            'bom_id': bom.id,
            'location_src_id': self.location.id,
            'location_dest_id': self.location.id,
        })

        self.assertEqual(
            mo.product_uom_id,
            self.uom_unit,
            "La UoM de la MO debe ser la base (Unidad)"
        )

    def test_03_mo_explicit_uom_not_overridden(self):
        """Test: Si se especifica UoM explícitamente, no debe sobrescribirse"""
        mo = self.env['mrp.production'].create({
            'product_id': self.product_with_preferred.id,
            'product_qty': 2.0,
            'product_uom_id': self.uom_unit.id,  # Especificada explícitamente
            'bom_id': self.bom.id,
            'location_src_id': self.location.id,
            'location_dest_id': self.location.id,
        })

        self.assertEqual(
            mo.product_uom_id,
            self.uom_unit,
            "Si se especifica UoM explícitamente, debe respetarse"
        )

    def test_04_mo_onchange_product_applies_preferred_uom(self):
        """Test: Onchange de producto aplica UoM preferida"""
        mo = self.env['mrp.production'].new({
            'product_id': self.product_with_preferred.id,
            'product_qty': 1.0,
            'bom_id': self.bom.id,
        })

        # Simular onchange
        mo._onchange_product_id_uom_production_preferred()

        self.assertEqual(
            mo.product_uom_id,
            self.uom_box,
            "Onchange debe aplicar UoM preferida"
        )

    def test_05_mo_write_product_applies_preferred_uom(self):
        """Test: Al cambiar el producto en una MO, se aplica UoM preferida"""
        # Crear BoM para producto sin preferida
        bom_without = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_without_preferred.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
        })

        mo = self.env['mrp.production'].create({
            'product_id': self.product_without_preferred.id,
            'product_qty': 1.0,
            'bom_id': bom_without.id,
            'location_src_id': self.location.id,
            'location_dest_id': self.location.id,
        })

        # Cambiar a producto con UoM preferida
        mo.write({
            'product_id': self.product_with_preferred.id,
            'bom_id': self.bom.id,
        })

        self.assertEqual(
            mo.product_uom_id,
            self.uom_box,
            "Al cambiar el producto, debe aplicarse la UoM preferida"
        )

