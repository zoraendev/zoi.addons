/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

const HUBS = [
  { key: "direction", label: "Direccion" },
  { key: "commercial", label: "Comercial" },
  { key: "financial", label: "Financiero" },
  { key: "operations", label: "Operaciones" },
  { key: "pdv", label: "PDV / Cobertura" },
  { key: "rrhh", label: "RRHH" },
];

class ZrnAnalyticsHubAction extends Component {
  setup() {
    this.actionService = useService("action");
    this.hubs = HUBS;
    this.state = useState({
      activeHub: "direction",
    });
  }

  setActiveHub(hubKey) {
    this.state.activeHub = hubKey;
  }

  openHome() {
    return this.actionService.doAction("zrn_analitics.action_zrn_analitics_home");
  }

  get activeHub() {
    return this.hubs.find((hub) => hub.key === this.state.activeHub) || this.hubs[0];
  }
}

ZrnAnalyticsHubAction.template = "zrn_analitics.HubAction";

registry.category("actions").add("zrn_analitics.hubs", ZrnAnalyticsHubAction);
