/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

function splitTextByLength(text, maxLength = 18) {
    const normalized = String(text || "")
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .join(" ");

    if (!normalized) {
        return [];
    }

    const words = normalized.split(/\s+/);
    const lines = [];
    let currentLine = "";

    for (const word of words) {
        if (!currentLine) {
            if (word.length <= maxLength) {
                currentLine = word;
            } else {
                lines.push(...(word.match(new RegExp(`.{1,${maxLength}}`, "g")) || [word]));
            }
            continue;
        }

        const nextLine = `${currentLine} ${word}`;
        if (nextLine.length <= maxLength) {
            currentLine = nextLine;
            continue;
        }

        lines.push(currentLine);
        if (word.length <= maxLength) {
            currentLine = word;
        } else {
            const chunks = word.match(new RegExp(`.{1,${maxLength}}`, "g")) || [word];
            lines.push(...chunks.slice(0, -1));
            currentLine = chunks[chunks.length - 1] || "";
        }
    }

    if (currentLine) {
        lines.push(currentLine);
    }

    return lines;
}

function parseReceiptNote(note) {
    const normalized = String(note || "").trim();
    if (!normalized || normalized === "[]") {
        return "";
    }

    if (!normalized.startsWith("[") && !normalized.startsWith("{")) {
        return normalized;
    }

    try {
        const flattenNoteText = (value) => {
            if (typeof value === "string") {
                return [value.trim()].filter(Boolean);
            }
            if (Array.isArray(value)) {
                return value.flatMap((item) => flattenNoteText(item));
            }
            if (value && typeof value === "object") {
                return flattenNoteText(value.text || value.name || "");
            }
            return [];
        };

        const parsed = JSON.parse(normalized);
        if (Array.isArray(parsed)) {
            return flattenNoteText(parsed).join("\n");
        }
        if (parsed && typeof parsed === "object") {
            return flattenNoteText(parsed).join("\n") || normalized;
        }
    } catch {
        return normalized;
    }

    return normalized;
}

patch(OrderReceipt.prototype, {
    getReceiptCompanyName(order, data, company) {
        return (
            company?.display_name ||
            company?.name ||
            company?.partner_id?.name ||
            data?.company?.display_name ||
            data?.company?.name ||
            data?.company?.partner_id?.name ||
            order?.company?.display_name ||
            order?.company?.name ||
            order?.company?.partner_id?.name ||
            ""
        );
    },

    getReceiptCompanyNameLines(companyName, maxLength = 18) {
        return splitTextByLength(companyName, maxLength);
    },

    getReceiptLogoUrl(order, data, company) {
        const rawLogo = company?.logo || data?.company?.logo || order?.company?.logo;
        return (
            order?.config?.receiptLogoUrl ||
            (typeof rawLogo === "string" && rawLogo.startsWith("data:image/") ? rawLogo : false) ||
            (typeof rawLogo === "string" && rawLogo
                ? `data:image/png;base64,${rawLogo}`
                : false) ||
            company?.logo_url ||
            data?.company?.logo_url ||
            false
        );
    },

    getReceiptNoteDisplay(line) {
        const customerNote =
            (typeof line?.getCustomerNote === "function" && line.getCustomerNote()) ||
            line?.customerNote ||
            line?.customer_note ||
            "";
        if (customerNote && String(customerNote).trim()) {
            return String(customerNote).trim();
        }

        const internalNote =
            (typeof line?.getNote === "function" && line.getNote()) ||
            line?.note ||
            "";
        return parseReceiptNote(internalNote);
    },
});

patch(PosStore.prototype, {
    /**
     * Override editLots to auto-assign lot using FEFO criteria
     * instead of showing the SelectLotPopup to the user.
     *
     * - If lots with stock exist: pick the one with earliest expiration (FEFO)
     * - If no stock but lots exist: pick the last created lot
     * - If no lots at all: return empty lot name (allow blank)
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
