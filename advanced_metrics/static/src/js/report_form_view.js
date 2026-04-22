/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class AdvancedMetricsReportFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
  }

  async openProductionSummary() {
    if (!this.model.root.resId) {
      return;
    }
    const action = await this.orm.call(
      this.props.resModel,
      "action_open_production_summary",
      [[this.model.root.resId]],
    );
    await this.actionService.doAction(action);
  }
}

AdvancedMetricsReportFormController.template = "advanced_metrics.ReportFormView";

export const advancedMetricsReportFormView = {
  ...formView,
  Controller: AdvancedMetricsReportFormController,
};

registry
  .category("views")
  .add("advanced_metrics_report_form", advancedMetricsReportFormView);
