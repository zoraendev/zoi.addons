/** @odoo-module **/

import { onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class PeackPlaningProductionFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
    this._onRootClick = this._onRootClick.bind(this);

    onMounted(() => {
      this.rootRef.el?.addEventListener("click", this._onRootClick);
    });

    onWillUnmount(() => {
      this.rootRef.el?.removeEventListener("click", this._onRootClick);
    });
  }

  async backToReport() {
    if (!this.model.root.resId) {
      return;
    }
    const action = await this.orm.call(
      this.props.resModel,
      "action_back_to_report",
      [[this.model.root.resId]],
    );
    await this.actionService.doAction(action);
  }

  async _onRootClick(ev) {
    const createButton = ev.target.closest(".zrn_am_create_mo_btn");
    if (!createButton || !this.model.root.resId) {
      return;
    }

    ev.preventDefault();
    if (createButton.disabled) {
      return;
    }

    const productId = Number(createButton.dataset.productId || 0);
    const productQty = Number(createButton.dataset.productQty || 0);
    if (!productId) {
      return;
    }

    createButton.disabled = true;
    try {
      const action = await this.orm.call(
        this.props.resModel,
        "action_open_mrp_production_create",
        [[this.model.root.resId], productId, productQty],
      );
      if (action) {
        await this.actionService.doAction(action);
      }
    } finally {
      createButton.disabled = false;
    }
  }
}

PeackPlaningProductionFormController.template =
  "peack_planing.ProductionFormView";

export const advancedMetricsProductionFormView = {
  ...formView,
  Controller: PeackPlaningProductionFormController,
};

registry
  .category("views")
  .add("peack_planing_production_form", advancedMetricsProductionFormView);
