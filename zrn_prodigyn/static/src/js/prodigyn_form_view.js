/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

const PRODIGYN_VIEW_TITLES = {
  "zrn_prodigyn.inicio": "Prodigyn",
  "zrn_prodigyn.production.planning": "Planeacion de produccion/fabricacion",
  "zrn_prodigyn.production.planning.wizard": "Filtros de fabricacion",
  "zrn_prodigyn.purchase.planning": "Planeacion de Insumos / Compras",
  "zrn_prodigyn.delivery.planning": "Planeacion de Entregas",
};

class ZrnProdigynFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
  }

  getControlPanelTitle() {
    const modelName = this.props.resModel;
    if (modelName === "zrn_prodigyn.internal.tool") {
      return this.model?.root?.data?.name || "Prodigyn";
    }
    return PRODIGYN_VIEW_TITLES[modelName] || this.model?.root?.data?.name || "Prodigyn";
  }

  displayName() {
    return this.getControlPanelTitle();
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
