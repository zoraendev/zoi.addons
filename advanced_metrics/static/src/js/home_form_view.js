/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class AdvancedMetricsHomeFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
  }

  async openExternalInstance() {
    const action = await this.orm.call(
      this.props.resModel,
      "action_open_external_instance",
      [[this.model.root.resId]],
    );
    await this.actionService.doAction(action);
  }
}

AdvancedMetricsHomeFormController.template = "advanced_metrics.HomeFormView";

export const advancedMetricsHomeFormView = {
  ...formView,
  Controller: AdvancedMetricsHomeFormController,
};

registry
  .category("views")
  .add("advanced_metrics_home_form", advancedMetricsHomeFormView);
