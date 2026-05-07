/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

function isCdvProductDebug(props) {
    return props?.resModel === "product.product" && !!props?.context?.cdv_debug_product_filter;
}

function shouldLimitFinishedProducts(props) {
    const ctx = props?.context || {};
    return (
        props?.resModel === "product.product" &&
        !!(
            ctx.cdv_limit_finished_products_for_production_entry ||
            ctx.cdv_picking_is_production_entry ||
            ctx.default_cdv_picking_is_production_entry ||
            ctx.default_is_production_entry
        )
    );
}

patch(Many2XAutocomplete.prototype, {
    async search(name) {
        const domain = this.props.getDomain();
        const context = this.props.context;
        let records = await super.search(...arguments);
        if (shouldLimitFinishedProducts(this.props) && records.length) {
            const originalRecords = [...records];
            const allowedRecords = await this.orm.searchRead(
                "product.product",
                [
                    ["id", "in", originalRecords.map((record) => record.id)],
                    ["cdv_is_finished_product", "=", true],
                    ["is_storable", "=", true],
                    ["tracking", "in", ["lot", "serial"]],
                ],
                ["display_name"],
                { context }
            );
            const allowedIds = new Set(allowedRecords.map((record) => record.id));
            records = records.filter((record) => allowedIds.has(record.id));
            if (isCdvProductDebug(this.props)) {
                console.warn("[CDV JS][search post-filter]", {
                    name,
                    allowedIds: [...allowedIds],
                    filteredOutIds: originalRecords
                        .map((record) => record.id)
                        .filter((recordId) => !allowedIds.has(recordId)),
                });
            }
        }
        if (isCdvProductDebug(this.props)) {
            console.warn("[CDV JS][search]", {
                name,
                domain,
                context,
                records: records.map((record) => ({
                    id: record.id,
                    display_name: record.display_name,
                    formatted: record.__formatted_display_name,
                })),
            });
        }
        return records;
    },

    async suggest(request, lock) {
        const suggestions = await super.suggest(...arguments);
        const dedupedSuggestions = [];
        const seenRecordKeys = new Set();

        for (const suggestion of suggestions) {
            const slotName = suggestion.data?.slotName;
            if (slotName === "autoCompleteItem") {
                const recordId = suggestion.data?.record?.id;
                const recordDisplayName = suggestion.data?.record?.display_name || suggestion.label;
                const key = `${slotName}:${recordId || recordDisplayName}`;
                if (seenRecordKeys.has(key)) {
                    continue;
                }
                seenRecordKeys.add(key);
            }
            dedupedSuggestions.push(suggestion);
        }

        if (isCdvProductDebug(this.props)) {
            console.warn("[CDV JS][suggest]", {
                request,
                suggestions: suggestions.map((suggestion) => ({
                    label: suggestion.label,
                    recordId: suggestion.data?.record?.id,
                    recordDisplayName: suggestion.data?.record?.display_name,
                    slotName: suggestion.data?.slotName,
                    cssClass: suggestion.cssClass,
                })),
                dedupedSuggestions: dedupedSuggestions.map((suggestion) => ({
                    label: suggestion.label,
                    recordId: suggestion.data?.record?.id,
                    recordDisplayName: suggestion.data?.record?.display_name,
                    slotName: suggestion.data?.slotName,
                    cssClass: suggestion.cssClass,
                })),
            });
        }
        return dedupedSuggestions;
    },
});

