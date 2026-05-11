/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class PeackPlaningReportFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
    this.actionService = useService("action");
    // Inyectamos el servicio en window para que el JS custom pueda disparar acciones
    window.__peackPlaningDoAction = (action) => this.actionService.doAction(action);
    window.__peackPlaningGetResId = () => this.model.root.resId;
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

PeackPlaningReportFormController.template = "peack_planing.ReportFormView";

export const advancedMetricsReportFormView = {
  ...formView,
  Controller: PeackPlaningReportFormController,
};

registry
  .category("views")
  .add("peack_planing_report_form", advancedMetricsReportFormView);
