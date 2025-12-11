# Copyright 2025 Xtendoo - Manuel Calero
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import TransactionCase
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError


class TestTraceabilityScenario(TransactionCase):
    """Tests para escenarios de casos de uso reales de trazabilidad"""

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
                "sequence_code": "PROD-IN-TEST",
                "default_location_src_id": cls.location_production.id,
                "default_location_dest_id": cls.location_stock.id,
                "warehouse_id": cls.env["stock.warehouse"]
                .search([("company_id", "=", cls.env.company.id)], limit=1)
                .id,
            }
        )

        # Configurar parámetro del sistema
        cls.env["ir.config_parameter"].sudo().set_param(
            "cdv_production_traceability.finished_picking_type_id", cls.picking_type.id
        )

        # 1. Crear Productos: Bollito de leche, Harina, Azucar
        cls.product_harina = cls.env["product.product"].create(
            {
                "name": "Harina",
                "tracking": "lot",
                "is_storable": True,
                "uom_id": cls.env.ref("uom.product_uom_kgm").id,
            }
        )

        cls.product_azucar = cls.env["product.product"].create(
            {
                "name": "Azucar",
                "tracking": "lot",
                "is_storable": True,
                "uom_id": cls.env.ref("uom.product_uom_kgm").id,
            }
        )

        cls.product_bollito = cls.env["product.product"].create(
            {
                "name": "Bollito de leche",
                "tracking": "lot",
                "is_storable": True,
                "uom_id": cls.env.ref("uom.product_uom_unit").id,
            }
        )

        # 2. Crear Lista de Materiales (BoM)
        cls.bom_bollito = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product_bollito.product_tmpl_id.id,
                "product_qty": 100.0,  # Para 100 bollitos (luego ajustamos en linea)
                "type": "normal",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_harina.id,
                            "product_qty": 10.0,  # Ejemplo: 10kg harina
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_azucar.id,
                            "product_qty": 2.0,  # Ejemplo: 2kg azucar
                        },
                    ),
                ],
            }
        )

        # Crear Lotes
        cls.lot_harina_1234 = cls.env["stock.lot"].create(
            {
                "name": "1234",
                "product_id": cls.product_harina.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.lot_harina_5678 = cls.env["stock.lot"].create(
            {
                "name": "5678",
                "product_id": cls.product_harina.id,
                "company_id": cls.env.company.id,
            }
        )

    def test_traceability_bollito_scenario(self):
        """
        Caso de uso:
        - 1/12/2025 10:00: Harina lote 1234 en uso.
        - 2/12/2025: Producción 100 bollitos.
        - 3/12/2025: Harina lote 5678 en uso.
        - Verificación: En 2/12 se usó Harina 1234 y Azucar (sin lote).
        """

        # Simulamos fechas
        date_usage_start_1 = datetime(2025, 12, 1, 10, 0, 0)  # 1 Dec 2025 10:00
        date_production = date(2025, 12, 2)  # 2 Dec 2025
        date_usage_start_2 = datetime(2025, 12, 3, 9, 0, 0)  # 3 Dec 2025 09:00

        # 1. Poner en uso Harina Lote 1234 el 1/12
        raw_material_1 = self.env["cdv.raw.material.in.use"].create(
            {
                "product_id": self.product_harina.id,
                "lot_id": self.lot_harina_1234.id,
                "date_from": date_usage_start_1,
                "company_id": self.env.company.id,
            }
        )

        # Verificamos que está activo
        self.assertTrue(raw_material_1.is_in_use)
        self.assertEqual(raw_material_1.state, "in_use")

        # 2. Crear Parte de Producción el 2/12
        production_entry = self.env["cdv.production.entry"].create(
            {
                "date": date_production,
                "picking_type_id": self.picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_bollito.id,
                            "quantity": 100.0,
                            "uom_id": self.product_bollito.uom_id.id,
                        },
                    ),
                ],
            }
        )
        production_entry.action_confirm()
        self.assertEqual(production_entry.state, "done")

        # 3. Poner en uso Harina Lote 5678 el 3/12
        # Primero debemos finalizar el anterior para evitar constraint error
        # El usuario dijo "el dia 3/12 ... se pone en uso la harina ... 5678"
        # Asumimos que esto implica cerrar el anterior.
        # Si cerramos el anterior con fecha 3/12, seguirá cubriendo el 2/12.

        raw_material_1.date_to = date_usage_start_2
        raw_material_1._compute_state()  # Forzar recomputo si necesario, o confiar en ORM

        raw_material_2 = self.env["cdv.raw.material.in.use"].create(
            {
                "product_id": self.product_harina.id,
                "lot_id": self.lot_harina_5678.id,
                "date_from": date_usage_start_2,
                "company_id": self.env.company.id,
            }
        )

        # 4. Generar Informe de Trazabilidad para el 2/12
        wizard = self.env["cdv.production.trace.report"].create(
            {
                "date_from": date_production,
                "date_to": date_production,
                "company_id": self.env.company.id,
            }
        )
        wizard.action_compute_trace()

        # 5. Verificaciones
        lines = wizard.line_ids
        self.assertTrue(lines, "Debería haber líneas en el informe")

        # Debemos encontrar 2 líneas de componentes para el Bollito (Harina y Azujar)
        # o más bien 1 línea por componente.

        # Verificar Harina
        line_harina = lines.filtered(
            lambda l: l.component_product_id == self.product_harina
        )
        self.assertEqual(len(line_harina), 1, "Debe haber una línea para Harina")
        self.assertEqual(
            line_harina.component_lot_id,
            self.lot_harina_1234,
            "El lote de harina debe ser 1234",
        )
        self.assertEqual(
            line_harina.trace_status, "found", "El estado debe ser 'found'"
        )

        # Verificar Azucar
        line_azucar = lines.filtered(
            lambda l: l.component_product_id == self.product_azucar
        )
        self.assertEqual(len(line_azucar), 1, "Debe haber una línea para Azucar")
        self.assertFalse(line_azucar.component_lot_id, "No debe haber lote para Azucar")
        self.assertEqual(
            line_azucar.trace_status, "missing", "El estado debe ser 'missing'"
        )

    def test_auto_finish_previous_material(self):
        """
        Caso de uso:
        - Se crea una materia prima en uso.
        - Se intenta crear otra para el mismo producto sin cerrar la anterior.
        - El sistema debe cerrar automáticamente la anterior y permitir crear la nueva.
        """
        # 1. Crear primera materia prima en uso
        raw_material_1 = self.env["cdv.raw.material.in.use"].create(
            {
                "product_id": self.product_harina.id,
                "lot_id": self.lot_harina_1234.id,
                "date_from": datetime.now() - timedelta(hours=2),
                "company_id": self.env.company.id,
            }
        )
        self.assertTrue(raw_material_1.is_in_use)
        self.assertFalse(raw_material_1.date_to)

        # 2. Crear segunda materia prima para el mismo producto (nuevo lote)
        # Esto debería fallar antes del fix y pasar después
        raw_material_2 = self.env["cdv.raw.material.in.use"].create(
            {
                "product_id": self.product_harina.id,
                "lot_id": self.lot_harina_5678.id,
                "date_from": datetime.now() - timedelta(hours=1),
                "company_id": self.env.company.id,
            }
        )

        # 3. Verificaciones
        # La primera debe estar cerrada
        self.assertFalse(raw_material_1.is_in_use)
        self.assertTrue(raw_material_1.date_to)

        # La fecha fin de la primera debe coincidir con la fecha inicio de la segunda (aprox o exacta)
        # En la implementación usaremos la fecha inicio de la segunda como fecha fin de la primera
        self.assertEqual(raw_material_1.date_to, raw_material_2.date_from)

        # La segunda debe estar activa
        self.assertTrue(raw_material_2.is_in_use)
        self.assertFalse(raw_material_2.date_to)
