from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestUomProductionPreferred(TransactionCase):
    """Tests para UoM preferida de producción"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear UoMs
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")
        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")

        # Crear UoM caja (si no existe)
        cls.uom_box = cls.env["uom.uom"].search(
            [("name", "=", "Caja"), ("relative_uom_id", "=", cls.uom_unit.id)], limit=1
        )

        if not cls.uom_box:
            cls.uom_box = cls.env["uom.uom"].create(
                {
                    "name": "Caja",
                    "relative_uom_id": cls.uom_unit.id,
                    "relative_factor": 12.0,
                    "rounding": 1.0,
                }
            )

        # Crear producto de prueba
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "type": "product",
                "uom_id": cls.uom_unit.id,
                "uom_po_id": cls.uom_unit.id,
            }
        )

    def test_01_uom_production_preferred_same_category(self):
        """Test: UoM de producción preferida debe estar en la misma categoría"""
        # Configurar UoM preferida válida (misma categoría)
        self.product.uom_production_preferred_id = self.uom_box.id
        self.assertEqual(
            self.product.uom_production_preferred_id,
            self.uom_box,
            "UoM de producción preferida debería configurarse correctamente",
        )

    def test_02_uom_production_preferred_different_category_fails(self):
        """Test: UoM de producción preferida en categoría diferente debe fallar"""
        # Intentar configurar UoM de categoría diferente
        with self.assertRaises(ValidationError) as context:
            self.product.uom_production_preferred_id = self.uom_kg.id

        self.assertIn(
            "misma categoría",
            str(context.exception),
            "Debe lanzar error sobre categorías incompatibles",
        )

    def test_03_uom_purchase_preferred_same_category(self):
        """Test: UoM de compra preferida debe estar en la misma categoría"""
        # Configurar UoM preferida válida (misma categoría)
        self.product.uom_purchase_preferred_id = self.uom_dozen.id
        self.assertEqual(
            self.product.uom_purchase_preferred_id,
            self.uom_dozen,
            "UoM de compra preferida debería configurarse correctamente",
        )

    def test_04_uom_purchase_preferred_different_category_fails(self):
        """Test: UoM de compra preferida en categoría diferente debe fallar"""
        # Intentar configurar UoM de categoría diferente
        with self.assertRaises(ValidationError) as context:
            self.product.uom_purchase_preferred_id = self.uom_kg.id

        self.assertIn(
            "misma categoría",
            str(context.exception),
            "Debe lanzar error sobre categorías incompatibles",
        )

    def test_05_empty_uom_preferred_is_valid(self):
        """Test: UoM preferida vacía debe ser válida (comportamiento estándar)"""
        self.product.uom_production_preferred_id = False
        self.product.uom_purchase_preferred_id = False
        # No debe lanzar ningún error
        self.assertFalse(
            self.product.uom_production_preferred_id, "UoM preferida vacía es válida"
        )
