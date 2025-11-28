# Copyright 2025 Xtendoo - Manuel Calero
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import TransactionCase
from datetime import date


class TestProductionEntryLine(TransactionCase):
    """Tests para el modelo cdv.production.entry.line"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear ubicaciones
        cls.location_production = cls.env['stock.location'].create({
            'name': 'Producción Test',
            'usage': 'production',
        })

        cls.location_stock = cls.env['stock.location'].create({
            'name': 'Stock Test',
            'usage': 'internal',
        })

        # Crear tipo de albarán
        cls.picking_type = cls.env['stock.picking.type'].create({
            'name': 'Entrada Producción Test',
            'code': 'incoming',
            'warehouse_id': cls.env['stock.warehouse'].search([
                ('company_id', '=', cls.env.company.id)
            ], limit=1).id,
            'sequence_code': 'PROD-IN',
            'default_location_src_id': cls.location_production.id,
            'default_location_dest_id': cls.location_stock.id,
        })

        # Crear materias primas
        product_tmpl_flour = cls.env['product.template'].create({
            'name': 'Harina Test',
            'tracking': 'lot',
        })
        cls.product_flour = product_tmpl_flour.product_variant_id

        product_tmpl_sugar = cls.env['product.template'].create({
            'name': 'Azúcar Test',
            'tracking': 'lot',
        })
        cls.product_sugar = product_tmpl_sugar.product_variant_id

        # Crear productos terminados
        product_tmpl_with_bom = cls.env['product.template'].create({
            'name': 'Producto Con BoM',
            'tracking': 'lot',
        })
        cls.product_with_bom = product_tmpl_with_bom.product_variant_id

        product_tmpl_without_bom = cls.env['product.template'].create({
            'name': 'Producto Sin BoM',
            'tracking': 'lot',
        })
        cls.product_without_bom = product_tmpl_without_bom.product_variant_id

        # Crear BoM
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_with_bom.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': cls.product_flour.id,
                    'product_qty': 0.5,
                }),
                (0, 0, {
                    'product_id': cls.product_sugar.id,
                    'product_qty': 0.1,
                }),
            ],
        })

        # Crear parte de producción
        cls.entry = cls.env['cdv.production.entry'].create({
            'date': date.today(),
            'picking_type_id': cls.picking_type.id,
        })

    def test_01_create_production_line(self):
        """Test: Crear línea de producción"""
        line = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_with_bom.id,
            'quantity': 10,
            'uom_id': self.product_with_bom.uom_id.id,
        })

        self.assertTrue(line)
        self.assertEqual(line.product_id, self.product_with_bom)
        self.assertEqual(line.quantity, 10)
        self.assertEqual(line.company_id, self.env.company)
        self.assertEqual(line.date, self.entry.date)

    def test_02_compute_has_bom_true(self):
        """Test: Producto con BoM"""
        line = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_with_bom.id,
            'quantity': 10,
            'uom_id': self.product_with_bom.uom_id.id,
        })

        self.assertTrue(line.has_bom)
        self.assertEqual(line.bom_id, self.bom)

    def test_03_compute_has_bom_false(self):
        """Test: Producto sin BoM"""
        line = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_without_bom.id,
            'quantity': 10,
            'uom_id': self.product_without_bom.uom_id.id,
        })

        self.assertFalse(line.has_bom)
        self.assertFalse(line.bom_id)

    def test_04_related_fields(self):
        """Test: Campos relacionados con el parte de producción"""
        line = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_with_bom.id,
            'quantity': 10,
            'uom_id': self.product_with_bom.uom_id.id,
        })

        # Verificar campos relacionados
        self.assertEqual(line.company_id, self.entry.company_id)
        self.assertEqual(line.date, self.entry.date)
        self.assertEqual(line.state, self.entry.state)

    def test_05_default_sequence(self):
        """Test: Secuencia por defecto"""
        line = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_with_bom.id,
            'quantity': 10,
            'uom_id': self.product_with_bom.uom_id.id,
        })

        self.assertEqual(line.sequence, 10)

    def test_06_multiple_lines_ordering(self):
        """Test: Ordenación de múltiples líneas"""
        line1 = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_with_bom.id,
            'quantity': 10,
            'uom_id': self.product_with_bom.uom_id.id,
            'sequence': 20,
        })

        line2 = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_without_bom.id,
            'quantity': 5,
            'uom_id': self.product_without_bom.uom_id.id,
            'sequence': 10,
        })

        lines = self.env['cdv.production.entry.line'].search([
            ('entry_id', '=', self.entry.id)
        ])

        # Verificar orden
        self.assertEqual(lines[0], line2)
        self.assertEqual(lines[1], line1)

    def test_07_lot_assignment(self):
        """Test: Asignación de lote a línea"""
        lot = self.env['stock.lot'].create({
            'name': 'LOT-TEST-001',
            'product_id': self.product_with_bom.id,
            'company_id': self.env.company.id,
        })

        line = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_with_bom.id,
            'quantity': 10,
            'uom_id': self.product_with_bom.uom_id.id,
            'lot_id': lot.id,
        })

        self.assertEqual(line.lot_id, lot)

    def test_08_cascade_delete(self):
        """Test: Eliminar parte de producción elimina líneas"""
        line = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_with_bom.id,
            'quantity': 10,
            'uom_id': self.product_with_bom.uom_id.id,
        })

        line_id = line.id
        self.entry.unlink()

        # Verificar que la línea se eliminó
        deleted_line = self.env['cdv.production.entry.line'].search([
            ('id', '=', line_id)
        ])
        self.assertFalse(deleted_line)

    def test_09_uom_consistency(self):
        """Test: Unidad de medida del producto"""
        line = self.env['cdv.production.entry.line'].create({
            'entry_id': self.entry.id,
            'product_id': self.product_with_bom.id,
            'quantity': 10,
            'uom_id': self.product_with_bom.uom_id.id,
        })

        self.assertEqual(line.uom_id, self.product_with_bom.uom_id)

    def test_10_compute_bom_with_company(self):
        """Test: BoM específico de compañía"""
        # Crear una segunda compañía
        company2 = self.env['res.company'].create({
            'name': 'Company 2',
        })

        # Crear BoM específico para company2
        bom_company2 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_with_bom.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'company_id': company2.id,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.product_flour.id,
                    'product_qty': 0.8,
                }),
            ],
        })

        # Crear parte en company2
        entry_company2 = self.env['cdv.production.entry'].create({
            'date': date.today(),
            'picking_type_id': self.picking_type.id,
            'company_id': company2.id,
        })

        line = self.env['cdv.production.entry.line'].create({
            'entry_id': entry_company2.id,
            'product_id': self.product_with_bom.id,
            'quantity': 10,
            'uom_id': self.product_with_bom.uom_id.id,
        })

        # Debería encontrar la BoM de company2
        self.assertTrue(line.has_bom)
        self.assertEqual(line.bom_id, bom_company2)

