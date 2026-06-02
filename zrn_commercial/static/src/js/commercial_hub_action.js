/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

const HUBS = [
  { key: "direction", label: "Direccion", template: "zrn_commercial.HubDirection" },
  { key: "commercial", label: "Comercial", template: "zrn_commercial.HubCommercial" },
  { key: "financial", label: "Financiero", template: "zrn_commercial.HubFinancial" },
  { key: "operations", label: "Operaciones", template: "zrn_commercial.HubOperations" },
  { key: "pdv", label: "PDV / Cobertura", template: "zrn_commercial.HubPdv" },
  { key: "rrhh", label: "RRHH", template: "zrn_commercial.HubRrhh" },
];

class ZrnCommercialHubAction extends Component {
  setup() {
    this.hubs = HUBS;
    this.state = useState({
      activeHub: "commercial",
    });
  }

  setActiveHub(hubKey) {
    this.state.activeHub = hubKey;
  }

  get activeHub() {
    return this.hubs.find((hub) => hub.key === this.state.activeHub) || this.hubs[0];
  }
}

ZrnCommercialHubAction.template = "zrn_commercial.HubAction";

registry.category("actions").add("zrn_commercial.hubs", ZrnCommercialHubAction);
