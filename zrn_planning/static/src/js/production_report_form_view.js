/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class ZrnPlanningProductionReportFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
  }

  async openManufactureTable() {
    if (!this.model.root.resId) {
      return;
    }
    const action = await this.orm.call(
      this.props.resModel,
      "action_open_manufacture_table",
      [[this.model.root.resId]],
    );
    await this.actionService.doAction(action);
  }
}

class ZrnPlanningProductionManufactureFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
  }

  async createMfgPlan() {
    if (!this.model.root.resId) {
      return;
    }
    const action = await this.orm.call(
      this.props.resModel,
      "action_open_create_mfg_plan_modal",
      [[this.model.root.resId]],
    );
    await this.actionService.doAction(action);
  }
}

ZrnPlanningProductionReportFormController.template =
  "zrn_planning.ProductionReportFormView";
ZrnPlanningProductionManufactureFormController.template =
  "zrn_planning.ProductionManufactureFormView";

registry.category("views").add("zrn_planning_production_report_form", {
  ...formView,
  Controller: ZrnPlanningProductionReportFormController,
});

registry.category("views").add("zrn_planning_production_manufacture_form", {
  ...formView,
  Controller: ZrnPlanningProductionManufactureFormController,
});
