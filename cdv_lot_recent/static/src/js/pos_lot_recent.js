/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /**
     * Sobreescribe editLots de cdv_pos_auto_lot para asignar el lote
     * más reciente (LIFO) en lugar del más antiguo (FEFO).
     *
     * - Si hay lotes con stock: elige el de fecha de caducidad más reciente (LIFO)
     * - Si no hay stock pero existen lotes: elige el último lote creado
     * - Si no hay lotes: devuelve nombre de lote vacío (permite en blanco)
     */
    async editLots(product, _packLotLinesToEdit) {
        let lots = [];
        try {
            lots = await this.data.call("pos.order.line", "get_lots_for_auto_assign", [
                this.company.id,
                this.config.id,
                product.id,
            ]);
        } catch {
            // Si falla el RPC, continuar con lote vacío
            lots = [];
        }

        if (lots.length > 0) {
            // Auto-asignar el primer lote (ya ordenado LIFO desde el backend)
            const lotName = lots[0].name;

            // Comprobar si el lote ya está completamente usado en pedidos en borrador
            const usedLotsQty = this.models["pos.pack.operation.lot"]
                .filter(
                    (lot) =>
                        lot.pos_order_line_id?.product_id?.id === product.id &&
                        lot.pos_order_line_id?.order_id?.state === "draft"
                )
                .reduce((acc, lot) => {
                    if (!acc[lot.lot_name]) {
                        acc[lot.lot_name] = 0;
                    }
                    acc[lot.lot_name] += lot.pos_order_line_id?.qty || 0;
                    return acc;
                }, {});

            // Buscar un lote que aún tenga cantidad disponible
            for (const lot of lots) {
                const usedQty = usedLotsQty[lot.name] || 0;
                if (lot.product_qty > usedQty || lot.product_qty === 0) {
                    return {
                        modifiedPackLotLines: {},
                        newPackLotLines: [{ lot_name: lot.name }],
                    };
                }
            }

            // Todos los lotes están agotados, asignar el primero de todas formas
            return {
                modifiedPackLotLines: {},
                newPackLotLines: [{ lot_name: lotName }],
            };
        }

        // No se encontraron lotes — devolver vacío (permitir en blanco)
        return {
            modifiedPackLotLines: {},
            newPackLotLines: [{ lot_name: "" }],
        };
    },
});
