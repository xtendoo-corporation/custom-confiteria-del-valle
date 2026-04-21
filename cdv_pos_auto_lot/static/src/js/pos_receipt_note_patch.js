/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

const parseReceiptNote = (rawValue) => {
    if (!rawValue || rawValue === "[]") {
        return "";
    }

    if (typeof rawValue !== "string") {
        return String(rawValue || "");
    }

    const trimmedValue = rawValue.trim();
    if (!trimmedValue) {
        return "";
    }

    if (!trimmedValue.startsWith("[")) {
        return trimmedValue;
    }

    try {
        const parsedLines = JSON.parse(trimmedValue);
        if (!Array.isArray(parsedLines)) {
            return trimmedValue;
        }

        const parsedTexts = parsedLines
            .map((parsedLine) => parsedLine?.text)
            .filter((parsedText) => Boolean(parsedText));
        return parsedTexts.length ? parsedTexts.join(", ") : "";
    } catch {
        return trimmedValue;
    }
};

patch(PosOrderline.prototype, {
    getCustomerNote() {
        const directCustomerNote = this.customer_note || this.customerNote || "";
        const parsedCustomerNote = parseReceiptNote(directCustomerNote);
        if (parsedCustomerNote) {
            return parsedCustomerNote;
        }

        return parseReceiptNote(this.note || (this.getNote && this.getNote()) || "");
    },

    getPrintableLineNote() {
        return this.getCustomerNote();
    },
});
