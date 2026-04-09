/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class PbiConnectionsHomeFormController extends FormController {
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
