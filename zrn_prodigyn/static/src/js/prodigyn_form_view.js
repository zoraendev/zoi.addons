/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class ZrnProdigynFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
  }

  async openProdigynAction(methodName) {
    const action = await this.orm.call(this.props.resModel, methodName, [
      [this.model.root.resId],
    ]);
    await this.actionService.doAction(action);
  }

  openButton1() {
    return this.openProdigynAction("action_open_button_1");
  }

  openButton2() {
    return this.openProdigynAction("action_open_button_2");
  }

  openButton3() {
    return this.openProdigynAction("action_open_button_3");
  }

  openButton4() {
    return this.openProdigynAction("action_open_button_4");
  }

  openButton5() {
    return this.openProdigynAction("action_open_button_5");
  }

  openSupport() {
    return this.openProdigynAction("action_open_support");
  }

  openProdigynGo() {
    return this.openProdigynAction("action_open_prodigyn_go");
  }
}

ZrnProdigynFormController.template = "zrn_prodigyn.FormView";

export const zrnProdigynFormView = {
  ...formView,
  Controller: ZrnProdigynFormController,
};

registry.category("views").add("zrn_prodigyn_form", zrnProdigynFormView);
