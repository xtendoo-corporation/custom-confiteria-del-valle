/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    getPrintableLineNote() {
        const customerNote =
            this.customer_note ||
            this.customerNote ||
            (this.getCustomerNote && this.getCustomerNote()) ||
            "";

        if (customerNote) {
            return customerNote;
        }

        const rawNote = this.note || (this.getNote && this.getNote()) || "";
        if (!rawNote || rawNote === "[]") {
            return "";
        }

        if (typeof rawNote === "string") {
            const trimmedNote = rawNote.trim();
            if (trimmedNote.startsWith("[")) {
                try {
                    const parsedNotes = JSON.parse(trimmedNote);
                    if (Array.isArray(parsedNotes)) {
                        const noteTexts = parsedNotes
                            .map((noteLine) => noteLine?.text)
                            .filter((noteText) => Boolean(noteText));
                        if (noteTexts.length) {
                            return noteTexts.join(", ");
                        }
                    }
                } catch {
                    return trimmedNote;
                }
            }
            return trimmedNote;
        }

        return String(rawNote || "");
    },
});
