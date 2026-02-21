/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /**
     * Override editLots to auto-assign lot using FEFO criteria
     * instead of showing the SelectLotPopup to the user.
     *
     * - If lots with stock exist: pick the one with earliest expiration (FEFO)
     * - If no stock but lots exist: pick the last created lot
     * - If no lots at all: return empty lot name (allow blank)
     */
    async editLots(product, packLotLinesToEdit) {
        let lots = [];
        try {
            lots = await this.data.call("pos.order.line", "get_lots_for_auto_assign", [
                this.company.id,
                this.config.id,
                product.id,
            ]);
        } catch {
            // If RPC fails, allow proceeding with empty lot
            lots = [];
        }

        if (lots.length > 0) {
            // Auto-assign the first lot (FEFO-sorted from backend)
            const lotName = lots[0].name;

            // Check if this lot is already fully used in draft orders
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

            // Find a lot that still has available qty
            for (const lot of lots) {
                const usedQty = usedLotsQty[lot.name] || 0;
                if (lot.product_qty > usedQty || lot.product_qty === 0) {
                    return {
                        modifiedPackLotLines: {},
                        newPackLotLines: [{ lot_name: lot.name }],
                    };
                }
            }

            // All lots fully used, still assign the first one
            return {
                modifiedPackLotLines: {},
                newPackLotLines: [{ lot_name: lotName }],
            };
        }

        // No lots found at all — return empty (allow blank)
        return {
            modifiedPackLotLines: {},
            newPackLotLines: [{ lot_name: "" }],
        };
    },

    /**
     * Override pay() to skip the "Some Serial/Lot Numbers are missing" dialog.
     * Navigate directly to PaymentScreen without asking the user.
     */
    async pay() {
        const currentOrder = this.getOrder();

        if (!currentOrder.canPay()) {
            return;
        }

        // Skip lot validation — go directly to payment
        this.mobile_pane = "right";
        this.navigate("PaymentScreen", {
            orderUuid: this.selectedOrderUuid,
        });
    },
});
