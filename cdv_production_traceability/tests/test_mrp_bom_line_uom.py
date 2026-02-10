from odoo.tests.common import TransactionCase


class TestMrpBomLineUomPreferred(TransactionCase):
    """Tests para aplicación automática de UoM en BoM lines"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear UoMs
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")

        # Crear UoM caja
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

        # Crear producto con UoM preferida
        cls.product_with_preferred = cls.env["product.product"].create(
            {
                "name": "Product with Preferred UoM",
                "type": "product",
                "uom_id": cls.uom_unit.id,
                "uom_po_id": cls.uom_unit.id,
                "uom_production_preferred_id": cls.uom_box.id,
            }
        )

        # Crear producto sin UoM preferida
        cls.product_without_preferred = cls.env["product.product"].create(
            {
                "name": "Product without Preferred UoM",
                "type": "product",
                "uom_id": cls.uom_unit.id,
                "uom_po_id": cls.uom_unit.id,
            }
        )

        # Crear producto final para la BoM
        cls.product_final = cls.env["product.product"].create(
            {
                "name": "Final Product",
                "type": "product",
                "uom_id": cls.uom_unit.id,
            }
        )

        # Crear BoM
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product_final.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
            }
        )

    def test_01_bom_line_with_preferred_uom(self):
        """Test: Al añadir producto con UoM preferida, debe aplicarse automáticamente"""
        bom_line = self.env["mrp.bom.line"].create(
            {
                "bom_id": self.bom.id,
                "product_id": self.product_with_preferred.id,
                "product_qty": 1.0,
            }
        )

        # Simular onchange
        bom_line._onchange_product_id_uom_production_preferred()

        self.assertEqual(
            bom_line.product_uom_id,
            self.uom_box,
            "La UoM de la línea de BoM debe ser la preferida (Caja)",
        )

    def test_02_bom_line_without_preferred_uom(self):
        """Test: Producto sin UoM preferida usa la UoM base"""
        bom_line = self.env["mrp.bom.line"].create(
            {
                "bom_id": self.bom.id,
                "product_id": self.product_without_preferred.id,
                "product_qty": 1.0,
            }
        )

        # Simular onchange
        bom_line._onchange_product_id_uom_production_preferred()

        self.assertEqual(
            bom_line.product_uom_id,
            self.uom_unit,
            "La UoM de la línea de BoM debe ser la base (Unidad)",
        )

    def test_03_change_product_updates_uom(self):
        """Test: Cambiar el producto actualiza la UoM según la preferida"""
        bom_line = self.env["mrp.bom.line"].create(
            {
                "bom_id": self.bom.id,
                "product_id": self.product_without_preferred.id,
                "product_qty": 1.0,
            }
        )

        # Cambiar a producto con UoM preferida
        bom_line.product_id = self.product_with_preferred
        bom_line._onchange_product_id_uom_production_preferred()

        self.assertEqual(
            bom_line.product_uom_id,
            self.uom_box,
            "Al cambiar a producto con UoM preferida, debe aplicarse",
        )
