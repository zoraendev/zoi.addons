/** @odoo-module **/

import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class PeackPlaningSalesOrdersFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
    this._lastCardSignature = null;
    this._renderRequestToken = 0;
    this._onRootClick = this._onRootClick.bind(this);

    onMounted(() => {
      window.__advancedMetricsSalesOrdersGetState = () =>
        this.model?.root?.data || {};
      this.rootRef.el?.addEventListener("click", this._onRootClick);
      this._syncSelectionCards({ force: true });
    });

    onPatched(() => {
      this._syncSelectionCards();
    });

    onWillUnmount(() => {
      this.rootRef.el?.removeEventListener("click", this._onRootClick);
      if (window.__advancedMetricsSalesOrdersGetState) {
        delete window.__advancedMetricsSalesOrdersGetState;
      }
    });
  }

  displayName() {
    return "Ordenes de Venta";
  }

  _getResIds(fieldName) {
    const fieldValue = this.model?.root?.data?.[fieldName];
    if (Array.isArray(fieldValue)) {
      return fieldValue;
    }
    if (Array.isArray(fieldValue?.currentIds)) {
      return fieldValue.currentIds;
    }
    if (Array.isArray(fieldValue?.resIds)) {
      return fieldValue.resIds;
    }
    return [];
  }

  _getSelectionSignature() {
    const wizardId = this.model?.root?.resId || 0;
    const clientIds = this._getResIds("selected_cliente_line_ids");
    const productIds = this._getResIds("selected_product_line_ids");
    return `${wizardId}|c:${clientIds.join(",")}|p:${productIds.join(",")}`;
  }

  async _syncSelectionCards({ force = false } = {}) {
    const signature = this._getSelectionSignature();
    if (!force && signature === this._lastCardSignature) {
      return;
    }
    this._lastCardSignature = signature;

    const wizardId = this.model?.root?.resId;
    const rootEl = this.rootRef.el;
    if (!wizardId || !rootEl) {
      return;
    }

    const token = ++this._renderRequestToken;
    const payload = await this.orm.call(
      this.props.resModel,
      "get_selected_review_cards",
      [[wizardId]],
    );
    if (token !== this._renderRequestToken) {
      return;
    }

    this._renderCards(
      rootEl.querySelector('.zrn_am_cards_grid[data-card-type="clients"]'),
      payload?.clients || [],
      "peack_planing.report.wizard.client.line",
    );
    this._renderCards(
      rootEl.querySelector('.zrn_am_cards_grid[data-card-type="products"]'),
      payload?.products || [],
      "peack_planing.report.wizard.product.line",
    );
  }

  _renderCards(container, items, modelName) {
    if (!container) {
      return;
    }

    if (!items.length) {
      const emptyMessage =
        modelName === "peack_planing.report.wizard.product.line"
          ? "No hay productos seleccionados."
          : "No hay clientes seleccionados.";
      container.innerHTML = `<div class="zrn_am_cards_empty">${emptyMessage}</div>`;
      return;
    }

    container.innerHTML = items
      .map((item) => {
        const statsHtml = (item.stats || [])
          .map(
            (stat) => `
              <div class="zrn_am_card_stat">
                <span>${this._escapeHtml(stat.label || "")}</span>
                <strong>${this._escapeHtml(String(stat.value ?? ""))}</strong>
              </div>`,
          )
          .join("");

        const subtitleHtml = item.subtitle
          ? `<div class="zrn_am_card_subtitle">${this._escapeHtml(item.subtitle)}</div>`
          : "";
        const metaHtml = item.meta
          ? `<div class="zrn_am_card_meta">${this._escapeHtml(item.meta)}</div>`
          : "";

        return `
          <article class="zrn_am_selection_card">
            <button
              type="button"
              class="zrn_am_card_remove"
              data-model="${modelName}"
              data-line-id="${item.line_id}"
              aria-label="Quitar"
              title="Quitar"
            >
              <i class="fa fa-times" role="img" aria-hidden="true"></i>
            </button>
            <div class="zrn_am_card_title">${this._escapeHtml(item.title || "")}</div>
            ${subtitleHtml}
            ${metaHtml}
            <div class="zrn_am_card_stats">${statsHtml}</div>
          </article>`;
      })
      .join("");
  }

  _escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  async _onRootClick(ev) {
    const removeButton = ev.target.closest(".zrn_am_card_remove");
    if (!removeButton) {
      return;
    }

    ev.preventDefault();
    const lineId = Number(removeButton.dataset.lineId || 0);
    const modelName = removeButton.dataset.model;
    if (!lineId || !modelName) {
      return;
    }

    removeButton.disabled = true;
    try {
      await this.orm.call(modelName, "action_remove", [[lineId]]);
      await this.model.root.load();
      this._lastCardSignature = null;
      await this._syncSelectionCards({ force: true });
    } finally {
      removeButton.disabled = false;
    }
  }
}

export const advancedMetricsSalesOrdersFormView = {
  ...formView,
  Controller: PeackPlaningSalesOrdersFormController,
};

registry
  .category("views")
  .add(
    "peack_planing_sales_orders_form",
    advancedMetricsSalesOrdersFormView,
  );
