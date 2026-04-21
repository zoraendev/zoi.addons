/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class AdvancedMetricsProductionFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
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
}

AdvancedMetricsProductionFormController.template =
  "advanced_metrics.ProductionFormView";

export const advancedMetricsProductionFormView = {
  ...formView,
  Controller: AdvancedMetricsProductionFormController,
};

registry
  .category("views")
  .add("advanced_metrics_production_form", advancedMetricsProductionFormView);
