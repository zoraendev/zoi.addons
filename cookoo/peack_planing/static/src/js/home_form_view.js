/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class PeackPlaningHomeFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
    this.actionService = useService("action");
    window.__peackPlaningDoAction = (action) => this.actionService.doAction(action);
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

PeackPlaningHomeFormController.template = "peack_planing.HomeFormView";

export const advancedMetricsHomeFormView = {
  ...formView,
  Controller: PeackPlaningHomeFormController,
};

registry
  .category("views")
  .add("peack_planing_home_form", advancedMetricsHomeFormView);
