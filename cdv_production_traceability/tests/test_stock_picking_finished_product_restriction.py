# Copyright 2026 Xtendoo
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from lxml import etree

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestStockPickingFinishedProductRestriction(TransactionCase):
    """Tests para restringir productos en partes de producción."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.location_production = cls.env["stock.location"].create(
            {
                "name": "Producción Restricción Test",
                "usage": "production",
            }
        )
        cls.location_stock = cls.env["stock.location"].create(
            {
                "name": "Stock Restricción Test",
                "usage": "internal",
            }
        )

        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "Entrada Producción Restricción Test",
                "code": "incoming",
                "warehouse_id": warehouse.id,
                "sequence_code": "PROD-IN-RESTR",
                "default_location_src_id": cls.location_production.id,
                "default_location_dest_id": cls.location_stock.id,
            }
        )
        cls.internal_picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "Traslado Interno Restricción Test",
                "code": "internal",
                "warehouse_id": warehouse.id,
                "sequence_code": "INT-RESTR",
                "default_location_src_id": cls.location_stock.id,
                "default_location_dest_id": cls.location_stock.id,
            }
        )

        cls.production_picking = cls.env["stock.picking"].create(
            {
                "partner_id": cls.env.company.partner_id.id,
                "picking_type_id": cls.picking_type.id,
                "location_id": cls.location_production.id,
                "location_dest_id": cls.location_stock.id,
                "is_production_entry": True,
            }
        )
        cls.standard_picking = cls.env["stock.picking"].create(
            {
                "partner_id": cls.env.company.partner_id.id,
                "picking_type_id": cls.picking_type.id,
                "location_id": cls.location_production.id,
                "location_dest_id": cls.location_stock.id,
                "is_production_entry": False,
            }
        )
        cls.internal_picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.internal_picking_type.id,
                "location_id": cls.location_stock.id,
                "location_dest_id": cls.location_stock.id,
                "is_production_entry": False,
            }
        )

        invalid_template = cls.env["product.template"].create(
            {
                "name": "Producto no elaborado",
                "tracking": "lot",
                "is_storable": True,
            }
        )
        cls.invalid_product = invalid_template.product_variant_id

        valid_template = cls.env["product.template"].create(
            {
                "name": "Producto elaborado válido",
                "tracking": "lot",
                "is_storable": True,
                "cdv_is_finished_product": True,
            }
        )
        cls.valid_product = valid_template.product_variant_id

        invalid_same_name_template = cls.env["product.template"].create(
            {
                "name": "Tartitas",
                "tracking": "lot",
                "is_storable": True,
            }
        )
        cls.invalid_same_name_product = invalid_same_name_template.product_variant_id

        valid_same_name_template = cls.env["product.template"].create(
            {
                "name": "Tartitas",
                "tracking": "lot",
                "is_storable": True,
                "cdv_is_finished_product": True,
            }
        )
        cls.valid_same_name_product = valid_same_name_template.product_variant_id

        extra_finished_template = cls.env["product.template"].create(
            {
                "name": "Bizcocho elaborado",
                "tracking": "lot",
                "is_storable": True,
                "cdv_is_finished_product": True,
            }
        )
        cls.extra_finished_product = extra_finished_template.product_variant_id

        cls.valid_product_lot = cls.env["stock.lot"].create(
            {
                "name": "LOT-VALID-001",
                "product_id": cls.valid_product.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.invalid_product_lot = cls.env["stock.lot"].create(
            {
                "name": "LOT-INVALID-001",
                "product_id": cls.invalid_product.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.valid_product,
            cls.location_stock,
            5.0,
            lot_id=cls.valid_product_lot,
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.invalid_product,
            cls.location_stock,
            2.0,
            lot_id=cls.invalid_product_lot,
        )

    def _get_move_vals(self, picking, product):
        return {
            "picking_id": picking.id,
            "product_id": product.id,
            "product_uom_qty": 1.0,
            "product_uom": product.uom_id.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
        }

    def test_01_production_picking_rejects_non_finished_product(self):
        """Un parte de producción no debe aceptar productos no elaborados."""
        with self.assertRaisesRegex(
            ValidationError,
            "no esta marcado como producto elaborado",
        ):
            self.env["stock.move"].create(
                self._get_move_vals(self.production_picking, self.invalid_product)
            )

    def test_02_production_picking_accepts_finished_product(self):
        """Un parte de producción sí debe aceptar productos elaborados válidos."""
        move = self.env["stock.move"].create(
            self._get_move_vals(self.production_picking, self.valid_product)
        )

        self.assertEqual(move.picking_id, self.production_picking)
        self.assertEqual(move.product_id, self.valid_product)

    def test_03_standard_picking_allows_non_finished_product(self):
        """La restricción solo aplica cuando el albarán es parte de producción."""
        move = self.env["stock.move"].create(
            self._get_move_vals(self.standard_picking, self.invalid_product)
        )

        self.assertEqual(move.picking_id, self.standard_picking)
        self.assertEqual(move.product_id, self.invalid_product)

    def test_04_production_picking_rejects_product_change_to_non_finished(self):
        """Cambiar el producto de una línea también debe respetar la restricción."""
        move = self.env["stock.move"].create(
            self._get_move_vals(self.production_picking, self.valid_product)
        )

        with self.assertRaisesRegex(
            ValidationError,
            "no esta marcado como producto elaborado",
        ):
            move.write({"product_id": self.invalid_product.id})

    def test_05_picking_form_domain_filters_finished_products(self):
        """La vista del albarán debe filtrar productos elaborados en operaciones."""
        arch = self.env["stock.picking"].with_context(
            default_is_production_entry=True
        ).get_view(self.env.ref("stock.view_picking_form").id, "form")["arch"]
        tree = etree.fromstring(arch)
        move_nodes = tree.xpath("//field[@name='move_ids']")
        product_nodes = tree.xpath(
            "//field[@name='move_ids']/list/field[@name='product_id']"
        )

        self.assertTrue(move_nodes)
        self.assertTrue(product_nodes)
        move_context = move_nodes[0].attrib.get("context", "")
        domain = product_nodes[0].attrib.get("domain", "")
        context = product_nodes[0].attrib.get("context", "")
        widget = product_nodes[0].attrib.get("widget", "")
        self.assertIn("product_tmpl_id.cdv_is_finished_product", domain)
        self.assertIn("parent.is_production_entry", domain)
        self.assertEqual(widget, "many2one")
        self.assertIn("cdv_limit_finished_products_for_production_entry", move_context)
        self.assertIn("default_cdv_picking_is_production_entry", move_context)
        self.assertIn("cdv_limit_finished_products_for_production_entry", context)
        self.assertIn("cdv_picking_is_production_entry", context)

    def test_06_move_operations_form_domain_filters_finished_products(self):
        """El popup de operaciones de stock.move debe usar el mismo filtro."""
        arch = self.env["stock.move"].get_view(
            self.env.ref("stock.view_stock_move_operations").id,
            "form",
        )["arch"]
        tree = etree.fromstring(arch)
        product_nodes = tree.xpath("//field[@name='product_id']")

        self.assertTrue(product_nodes)
        domain = product_nodes[0].attrib.get("domain", "")
        context = product_nodes[0].attrib.get("context", "")
        self.assertEqual(domain, "cdv_product_id_domain")
        self.assertIn("cdv_limit_finished_products_for_production_entry", context)
        self.assertIn("cdv_picking_is_production_entry", context)

    def test_07_name_search_hides_non_finished_products_in_production_context(self):
        """El autocompletado no debe devolver productos no elaborados en producción."""
        results = self.env["product.product"].with_context(
            cdv_limit_finished_products_for_production_entry=True
        ).name_search(name="Producto", operator="ilike", limit=20)

        result_ids = {product_id for product_id, _display_name in results}
        self.assertIn(self.valid_product.id, result_ids)
        self.assertNotIn(self.invalid_product.id, result_ids)

    def test_08_name_search_keeps_non_finished_products_outside_production_context(self):
        """Fuera del contexto de producción la búsqueda estándar no debe cambiar."""
        results = self.env["product.product"].name_search(
            name="Producto", operator="ilike", limit=20
        )

        result_ids = {product_id for product_id, _display_name in results}
        self.assertIn(self.valid_product.id, result_ids)
        self.assertIn(self.invalid_product.id, result_ids)

    def test_09_name_search_only_returns_finished_homonyms_in_production_context(self):
        """Con dos productos homónimos solo debe aparecer el elaborado en producción."""
        results = self.env["product.product"].with_context(
            cdv_picking_is_production_entry=True,
            default_cdv_picking_is_production_entry=True,
            default_picking_id=self.production_picking.id,
        ).name_search(name="Tartitas", operator="ilike", limit=20)

        result_ids = [product_id for product_id, _display_name in results]
        self.assertIn(self.valid_same_name_product.id, result_ids)
        self.assertNotIn(self.invalid_same_name_product.id, result_ids)

    def test_10_move_onchange_restricts_product_domain_for_production_picking(self):
        """El onchange de stock.move debe restringir product_id en la vista inline."""
        move = self.env["stock.move"].new(
            {
                "picking_id": self.production_picking.id,
            }
        )

        result = move._onchange_cdv_product_id_domain()

        self.assertTrue(result)
        self.assertIn("domain", result)
        self.assertIn("product_id", result["domain"])
        self.assertIn(
            ("product_tmpl_id.cdv_is_finished_product", "=", True),
            result["domain"]["product_id"],
        )

    def test_11_internal_transfer_imports_finished_products_once(self):
        """El traslado interno debe importar solo productos elaborados y sin duplicarlos."""
        self.internal_picking.action_import_finished_products()

        imported_products = self.internal_picking.move_ids.mapped("product_id")
        self.assertIn(self.valid_product, imported_products)
        self.assertIn(self.valid_same_name_product, imported_products)
        self.assertIn(self.extra_finished_product, imported_products)
        self.assertNotIn(self.invalid_product, imported_products)

        initial_count = len(self.internal_picking.move_ids)
        self.internal_picking.action_import_finished_products()
        self.assertEqual(len(self.internal_picking.move_ids), initial_count)

    def test_12_internal_transfer_validation_skips_lines_without_units(self):
        """Antes de validar, el traslado interno debe dejar solo líneas con unidades."""
        self.internal_picking.action_import_finished_products()

        move_with_demand = self.internal_picking.move_ids.filtered(
            lambda move: move.product_id == self.valid_product
        )

        move_with_demand.product_uom_qty = 3.0

        self.internal_picking._cdv_prepare_internal_finished_transfer_validation()

        remaining_products = self.internal_picking.move_ids.mapped("product_id")
        self.assertIn(self.valid_product, remaining_products)
        self.assertNotIn(self.valid_same_name_product, remaining_products)
        self.assertNotIn(self.extra_finished_product, remaining_products)
        self.assertEqual(move_with_demand.product_uom_qty, 3.0)

    def test_13_internal_transfer_form_shows_import_button(self):
        """La vista del albarán debe exponer el botón de importación para traslados internos."""
        arch = self.env["stock.picking"].get_view(
            self.env.ref("stock.view_picking_form").id,
            "form",
        )["arch"]
        tree = etree.fromstring(arch)
        button_nodes = tree.xpath("//button[@name='action_import_finished_products']")

        self.assertTrue(button_nodes)
        self.assertIn("picking_type_code != 'internal'", button_nodes[0].attrib.get("invisible", ""))

    def test_14_internal_transfer_imports_stock_lots_from_source(self):
        """El traslado interno debe importar producto, lote y cantidad disponible desde origen."""
        self.internal_picking.action_import_stock_lots_from_source()

        move_lines = self.internal_picking.move_line_ids.filtered(lambda line: line.lot_id)
        line_pairs = {(line.product_id, line.lot_id) for line in move_lines}

        self.assertIn((self.valid_product, self.valid_product_lot), line_pairs)
        self.assertIn((self.invalid_product, self.invalid_product_lot), line_pairs)

        valid_line = move_lines.filtered(
            lambda line: line.product_id == self.valid_product
            and line.lot_id == self.valid_product_lot
        )
        invalid_line = move_lines.filtered(
            lambda line: line.product_id == self.invalid_product
            and line.lot_id == self.invalid_product_lot
        )
        self.assertEqual(valid_line.quantity, 5.0)
        self.assertEqual(invalid_line.quantity, 2.0)
        self.assertEqual(valid_line.move_id.product_uom_qty, 5.0)

        initial_count = len(self.internal_picking.move_line_ids)
        self.internal_picking.action_import_stock_lots_from_source()
        self.assertEqual(len(self.internal_picking.move_line_ids), initial_count)

    def test_15_internal_transfer_form_shows_stock_lot_import_button(self):
        """La vista del albarán debe exponer el botón de importación de stock con lotes."""
        arch = self.env["stock.picking"].get_view(
            self.env.ref("stock.view_picking_form").id,
            "form",
        )["arch"]
        tree = etree.fromstring(arch)
        button_nodes = tree.xpath("//button[@name='action_import_stock_lots_from_source']")

        self.assertTrue(button_nodes)
        self.assertIn("picking_type_code != 'internal'", button_nodes[0].attrib.get("invisible", ""))

