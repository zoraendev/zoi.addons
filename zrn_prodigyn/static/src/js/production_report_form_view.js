/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class ZrnProdigynProductionReportFormController extends FormController {
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

class ZrnProdigynProductionManufactureFormController extends FormController {
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
      "action_create_mfg_plan",
      [[this.model.root.resId]],
    );
    await this.actionService.doAction(action);
  }
}

ZrnProdigynProductionReportFormController.template =
  "zrn_prodigyn.ProductionReportFormView";
ZrnProdigynProductionManufactureFormController.template =
  "zrn_prodigyn.ProductionManufactureFormView";

registry.category("views").add("zrn_prodigyn_production_report_form", {
  ...formView,
  Controller: ZrnProdigynProductionReportFormController,
});

registry.category("views").add("zrn_prodigyn_production_manufacture_form", {
  ...formView,
  Controller: ZrnProdigynProductionManufactureFormController,
});
