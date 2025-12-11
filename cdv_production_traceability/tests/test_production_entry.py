# Copyright 2025 Xtendoo - Manuel Calero
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime


class TestProductionEntry(TransactionCase):
    """Tests para el modelo cdv.production.entry"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear ubicaciones
        cls.location_production = cls.env["stock.location"].create(
            {
                "name": "Producción Test",
                "usage": "production",
            }
        )

        cls.location_stock = cls.env["stock.location"].create(
            {
                "name": "Stock Test",
                "usage": "internal",
            }
        )

        # Crear tipo de albarán
        cls.picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "Entrada Producción Test",
                "code": "incoming",
                "warehouse_id": cls.env["stock.warehouse"]
                .search([("company_id", "=", cls.env.company.id)], limit=1)
                .id,
                "sequence_code": "PROD-IN",
                "default_location_src_id": cls.location_production.id,
                "default_location_dest_id": cls.location_stock.id,
            }
        )

        # Configurar parámetros del sistema
        cls.env["ir.config_parameter"].sudo().set_param(
            "cdv_production_traceability.finished_picking_type_id", cls.picking_type.id
        )

        # Crear materias primas
        product_tmpl_flour = cls.env["product.template"].create(
            {
                "name": "Harina Test",
                "tracking": "lot",
            }
        )
        cls.product_flour = product_tmpl_flour.product_variant_id

        product_tmpl_sugar = cls.env["product.template"].create(
            {
                "name": "Azúcar Test",
                "tracking": "lot",
            }
        )
        cls.product_sugar = product_tmpl_sugar.product_variant_id

        # Crear producto terminado con seguimiento de lote
        product_tmpl_bread = cls.env["product.template"].create(
            {
                "name": "Pan Test",
                "tracking": "lot",
            }
        )
        cls.product_bread = product_tmpl_bread.product_variant_id

        # Crear BoM para el pan
        cls.bom_bread = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product_bread.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_flour.id,
                            "product_qty": 0.5,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_sugar.id,
                            "product_qty": 0.1,
                        },
                    ),
                ],
            }
        )

        # Producto sin BoM para tests de validación
        product_tmpl_no_bom = cls.env["product.template"].create(
            {
                "name": "Producto Sin BoM",
                "tracking": "lot",
            }
        )
        cls.product_no_bom = product_tmpl_no_bom.product_variant_id

    def test_01_create_production_entry(self):
        """Test: Crear un parte de producción"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
            }
        )

        self.assertTrue(entry)
        self.assertEqual(entry.state, "draft")
        self.assertNotEqual(entry.name, "Nuevo")
        self.assertEqual(entry.company_id, self.env.company)

    def test_02_compute_locations(self):
        """Test: Cálculo automático de ubicaciones desde tipo de albarán"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
            }
        )

        self.assertEqual(entry.location_src_id, self.location_production)
        self.assertEqual(entry.location_dest_id, self.location_stock)

    def test_03_compute_total_lines(self):
        """Test: Cálculo del total de líneas"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 20,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                ],
            }
        )

        self.assertEqual(entry.total_lines, 2)

    def test_04_confirm_production_entry(self):
        """Test: Confirmar parte de producción genera albarán"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                ],
            }
        )

        self.assertEqual(entry.state, "draft")
        self.assertFalse(entry.picking_id)

        # Confirmar
        entry.action_confirm()

        self.assertEqual(entry.state, "done")
        self.assertTrue(entry.picking_id)
        self.assertEqual(entry.picking_id.origin, entry.name)

    def test_05_auto_generate_lot(self):
        """Test: Generación automática de lote con formato DD-MM-YY"""
        test_date = date(2025, 11, 26)
        expected_lot_name = "26-11-25"

        entry = self.env["cdv.production.entry"].create(
            {
                "date": test_date,
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                ],
            }
        )

        # La línea no debe tener lote antes de confirmar
        self.assertFalse(entry.line_ids[0].lot_id)

        # Confirmar genera el lote
        entry.action_confirm()

        # Verificar que se creó el lote
        self.assertTrue(entry.line_ids[0].lot_id)
        self.assertEqual(entry.line_ids[0].lot_id.name, expected_lot_name)

    def test_06_reuse_existing_lot(self):
        """Test: Reutilizar lote existente del mismo día"""
        test_date = date(2025, 11, 26)
        lot_name = "26-11-25"

        # Crear lote previamente
        existing_lot = self.env["stock.lot"].create(
            {
                "name": lot_name,
                "product_id": self.product_bread.id,
                "company_id": self.env.company.id,
            }
        )

        entry = self.env["cdv.production.entry"].create(
            {
                "date": test_date,
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                ],
            }
        )

        entry.action_confirm()

        # Debe reutilizar el lote existente
        self.assertEqual(entry.line_ids[0].lot_id, existing_lot)

    def test_07_error_confirm_without_lines(self):
        """Test: Error al confirmar parte sin líneas"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
            }
        )

        with self.assertRaises(UserError):
            entry.action_confirm()

    def test_08_error_confirm_product_without_bom(self):
        """Test: Error al confirmar producto sin BoM"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_no_bom.id,
                            "quantity": 10,
                            "uom_id": self.product_no_bom.uom_id.id,
                        },
                    ),
                ],
            }
        )

        with self.assertRaises(ValidationError):
            entry.action_confirm()

    def test_09_cancel_production_entry(self):
        """Test: Cancelar parte de producción"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                ],
            }
        )

        entry.action_confirm()

        self.assertEqual(entry.state, "done")

        # Cancelar
        entry.action_cancel()

        self.assertEqual(entry.state, "cancelled")

    def test_10_error_delete_confirmed_entry(self):
        """Test: Error al eliminar parte confirmado"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                ],
            }
        )

        entry.action_confirm()

        with self.assertRaises(UserError):
            entry.unlink()

    def test_11_action_view_picking(self):
        """Test: Acción para ver el albarán asociado"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                ],
            }
        )

        entry.action_confirm()

        action = entry.action_view_picking()

        self.assertEqual(action["res_model"], "stock.picking")
        self.assertEqual(action["res_id"], entry.picking_id.id)

    def test_12_picking_moves_created(self):
        """Test: Verificar creación de movimientos en el albarán"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                ],
            }
        )

        entry.action_confirm()

        self.assertEqual(len(entry.picking_id.move_ids), 1)
        move = entry.picking_id.move_ids[0]
        self.assertEqual(move.product_id, self.product_bread)
        self.assertEqual(move.product_uom_qty, 10)

    def test_13_error_draft_with_picking(self):
        """Test: Error al volver a borrador si tiene albarán"""
        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                        },
                    ),
                ],
            }
        )

        entry.action_confirm()

        with self.assertRaises(UserError):
            entry.action_draft()

    def test_14_manual_lot_assignment(self):
        """Test: Asignación manual de lote"""
        manual_lot = self.env["stock.lot"].create(
            {
                "name": "LOTE-MANUAL-001",
                "product_id": self.product_bread.id,
                "company_id": self.env.company.id,
            }
        )

        entry = self.env["cdv.production.entry"].create(
            {
                "date": date.today(),
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bread.id,
                            "quantity": 10,
                            "uom_id": self.product_bread.uom_id.id,
                            "lot_id": manual_lot.id,
                        },
                    ),
                ],
            }
        )

        entry.action_confirm()

        # Debe mantener el lote manual
        self.assertEqual(entry.line_ids[0].lot_id, manual_lot)
