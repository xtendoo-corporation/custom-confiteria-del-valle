# Copyright 2025 Xtendoo - Manuel Calero
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TestRawMaterialInUse(TransactionCase):
    """Tests para el modelo cdv.raw.material.in.use"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear productos almacenables (materias primas)
        product_tmpl_flour = cls.env['product.template'].create({
            'name': 'Harina',
            'tracking': 'lot',
        })
        cls.product_flour = product_tmpl_flour.product_variant_id

        product_tmpl_sugar = cls.env['product.template'].create({
            'name': 'Azúcar',
            'tracking': 'lot',
        })
        cls.product_sugar = product_tmpl_sugar.product_variant_id

        # Crear lotes
        cls.lot_flour_001 = cls.env['stock.lot'].create({
            'name': 'LOT-FLOUR-001',
            'product_id': cls.product_flour.id,
            'company_id': cls.env.company.id,
        })

        cls.lot_flour_002 = cls.env['stock.lot'].create({
            'name': 'LOT-FLOUR-002',
            'product_id': cls.product_flour.id,
            'company_id': cls.env.company.id,
        })

        cls.lot_sugar_001 = cls.env['stock.lot'].create({
            'name': 'LOT-SUGAR-001',
            'product_id': cls.product_sugar.id,
            'company_id': cls.env.company.id,
        })

        # Crear ubicación
        cls.location = cls.env['stock.location'].create({
            'name': 'Ubicación Producción Test',
            'usage': 'internal',
        })

    def test_01_create_raw_material_in_use(self):
        """Test: Crear una materia prima en uso"""
        raw_material = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
            'location_id': self.location.id,
        })

        self.assertTrue(raw_material)
        self.assertEqual(raw_material.product_id, self.product_flour)
        self.assertEqual(raw_material.lot_id, self.lot_flour_001)
        self.assertTrue(raw_material.active)
        self.assertEqual(raw_material.state, 'in_use')
        self.assertFalse(raw_material.date_to)

    def test_02_compute_name(self):
        """Test: Verificar cálculo del nombre"""
        raw_material = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
        })

        expected_name = f"{self.product_flour.name} - {self.lot_flour_001.name}"
        self.assertEqual(raw_material.name, expected_name)

    def test_03_compute_display_name(self):
        """Test: Verificar cálculo del display_name"""
        date_from = datetime(2025, 11, 26, 10, 0, 0)
        raw_material = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': date_from,
        })

        self.assertIn('Harina - LOT-FLOUR-001', raw_material.display_name)
        self.assertIn('2025-11-26', raw_material.display_name)

    def test_04_finish_raw_material(self):
        """Test: Finalizar materia prima en uso"""
        raw_material = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
        })

        self.assertTrue(raw_material.active)
        self.assertEqual(raw_material.state, 'in_use')

        # Finalizar
        raw_material.action_finish()

        self.assertFalse(raw_material.active)
        self.assertEqual(raw_material.state, 'finished')
        self.assertTrue(raw_material.date_to)

    def test_05_reopen_raw_material(self):
        """Test: Reabrir materia prima finalizada"""
        raw_material = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
            'date_to': datetime.now(),
        })

        self.assertFalse(raw_material.active)
        self.assertEqual(raw_material.state, 'finished')

        # Reabrir
        raw_material.action_reopen()

        self.assertTrue(raw_material.active)
        self.assertEqual(raw_material.state, 'in_use')
        self.assertFalse(raw_material.date_to)

    def test_06_constraint_single_active_per_product(self):
        """Test: Solo puede haber una materia prima activa por producto"""
        # Crear primera materia prima activa
        self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
            'location_id': self.location.id,
        })

        # Intentar crear segunda materia prima activa para el mismo producto
        with self.assertRaises(ValidationError):
            self.env['cdv.raw.material.in.use'].create({
                'product_id': self.product_flour.id,
                'lot_id': self.lot_flour_002.id,
                'date_from': datetime.now(),
                'location_id': self.location.id,
            })

    def test_07_multiple_products_active(self):
        """Test: Pueden haber múltiples productos activos diferentes"""
        raw_material_1 = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
        })

        raw_material_2 = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_sugar.id,
            'lot_id': self.lot_sugar_001.id,
            'date_from': datetime.now(),
        })

        self.assertTrue(raw_material_1.active)
        self.assertTrue(raw_material_2.active)

    def test_08_finish_and_create_new(self):
        """Test: Finalizar y crear nueva materia prima para mismo producto"""
        raw_material_1 = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
        })

        # Finalizar la primera
        raw_material_1.action_finish()

        # Ahora se puede crear otra para el mismo producto
        raw_material_2 = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_002.id,
            'date_from': datetime.now(),
        })

        self.assertFalse(raw_material_1.active)
        self.assertTrue(raw_material_2.active)

    def test_09_available_qty_computation(self):
        """Test: Cálculo de cantidad disponible"""
        # Crear stock quant
        self.env['stock.quant'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'location_id': self.location.id,
            'quantity': 100.0,
        })

        raw_material = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
            'location_id': self.location.id,
        })

        self.assertEqual(raw_material.available_qty, 100.0)

    def test_10_onchange_product(self):
        """Test: Onchange del producto limpia el lote"""
        raw_material = self.env['cdv.raw.material.in.use'].new({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
        })

        # Cambiar producto
        raw_material.product_id = self.product_sugar
        result = raw_material._onchange_product_id()

        # El onchange debería retornar un dominio para lot_id
        self.assertIn('domain', result)
        self.assertIn('lot_id', result['domain'])

    def test_11_error_finish_already_finished(self):
        """Test: Error al finalizar una materia prima ya finalizada"""
        raw_material = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
            'date_to': datetime.now(),
        })

        with self.assertRaises(ValidationError):
            raw_material.action_finish()

    def test_12_error_reopen_already_active(self):
        """Test: Error al reabrir una materia prima ya activa"""
        raw_material = self.env['cdv.raw.material.in.use'].create({
            'product_id': self.product_flour.id,
            'lot_id': self.lot_flour_001.id,
            'date_from': datetime.now(),
        })

        with self.assertRaises(ValidationError):
            raw_material.action_reopen()

