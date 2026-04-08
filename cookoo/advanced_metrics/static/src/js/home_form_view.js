/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class AdvancedMetricsHomeFormController extends FormController {
  async openExternalInstance() {
    await this.actionService.doAction(
      "advanced_metrics.action_advanced_metrics_external_instance",
    );
  }
}

AdvancedMetricsHomeFormController.template =
  "advanced_metrics.HomeFormView";

export const advancedMetricsHomeFormView = {
  ...formView,
  Controller: AdvancedMetricsHomeFormController,
};

registry.category("views").add(
  "advanced_metrics_home_form",
  advancedMetricsHomeFormView,
);
