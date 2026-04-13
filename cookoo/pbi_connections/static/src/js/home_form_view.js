/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class PbiConnectionsHomeFormController extends FormController {
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

  async openEndpoints() {
    await this.actionService.doAction(
      "pbi_connections.action_pbi_connections_endpoint",
    );
  }
}

PbiConnectionsHomeFormController.template = "pbi_connections.HomeFormView";

export const pbiConnectionsHomeFormView = {
  ...formView,
  Controller: PbiConnectionsHomeFormController,
};

registry
  .category("views")
  .add("pbi_connections_home_form", pbiConnectionsHomeFormView);
