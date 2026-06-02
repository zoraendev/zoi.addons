/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class ZrnAnaliticsFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
  }

  get modelParams() {
    const modelParams = super.modelParams;
    if (this.props.resModel === "zrn_analitics.home") {
      const activeIds = this.props.context?.active_ids || [];
      if (activeIds.length > 1) {
        modelParams.config.resIds = activeIds;
        modelParams.config.resId =
          this.props.resId || this.props.context?.active_id || activeIds[0];
      }
    }
    return modelParams;
  }

  async openAnaliticsAction(methodName) {
    const action = await this.orm.call(this.props.resModel, methodName, [
      [this.model.root.resId],
    ]);
    await this.actionService.doAction(action);
  }

  openButton1() {
    return this.openAnaliticsAction("action_open_button_1");
  }

  openButton2() {
    return this.openAnaliticsAction("action_open_button_2");
  }

  openButton3() {
    return this.openAnaliticsAction("action_open_button_3");
  }

  openButton4() {
    return this.openAnaliticsAction("action_open_button_4");
  }

  openButton5() {
    return this.openAnaliticsAction("action_open_button_5");
  }

  openHome() {
    return this.openAnaliticsAction("action_open_home");
  }
}

ZrnAnaliticsFormController.template = "zrn_analitics.FormView";

export const ZrnAnaliticsFormView = {
  ...formView,
  Controller: ZrnAnaliticsFormController,
};

registry.category("views").add("zrn_analitics_form", ZrnAnaliticsFormView);
