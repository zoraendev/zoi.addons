/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const HUBS = [
  { key: "direction", label: "Direccion" },
  { key: "commercial", label: "Comercial" },
  { key: "financial", label: "Financiero" },
  { key: "operations", label: "Operaciones" },
  { key: "pdv", label: "PDV / Cobertura" },
  { key: "rrhh", label: "RRHH" },
];

const COMMERCIAL_TABS = [
  { key: "overview", label: "Overview", icon: "fa-home" },
  { key: "portafolio", label: "Portafolio", icon: "fa-archive" },
  { key: "cobertura", label: "Cobertura", icon: "fa-crosshairs" },
  { key: "mapa", label: "Mapa PDV", icon: "fa-map-marker" },
  { key: "canal", label: "Por Canal", icon: "fa-sitemap" },
  { key: "cliente", label: "Por Cliente / PDV", icon: "fa-users" },
  { key: "rfm", label: "Clientes RFM", icon: "fa-line-chart" },
  { key: "insights", label: "Cliente Insights", icon: "fa-lightbulb-o" },
  { key: "producto", label: "Por Producto", icon: "fa-cube" },
  { key: "unidades", label: "Unidades & Precio", icon: "fa-balance-scale" },
  { key: "tendencias", label: "Tendencias", icon: "fa-area-chart" },
  { key: "gap", label: "Sell-in vs Sell-out", icon: "fa-exchange" },
  { key: "inteligencia", label: "Inteligencia", icon: "fa-compass" },
  { key: "alertas", label: "Alertas & Acciones", icon: "fa-bell-o" },
  { key: "bcg", label: "Matriz BCG", icon: "fa-th-large" },
];

class ZrnAnalyticsHubAction extends Component {
  setup() {
    this.actionService = useService("action");
    this.orm = useService("orm");
    this.hubs = HUBS;
    this.commercialTabs = COMMERCIAL_TABS;
    this.state = useState({
      activeHub: "direction",
      commercialTab: "overview",
      commercialPayload: null,
      commercialLoading: false,
    });
    onWillStart(async () => {
      await this.loadCommercialPayload();
    });
  }

  async setActiveHub(hubKey) {
    this.state.activeHub = hubKey;
    if (hubKey === "commercial") {
      await this.loadCommercialPayload();
    }
  }

  setCommercialTab(tabKey) {
    this.state.commercialTab = tabKey;
  }

  async loadCommercialPayload(force = false) {
    if (this.state.commercialPayload && !force) {
      return;
    }
    this.state.commercialLoading = true;
    try {
      this.state.commercialPayload = await this.orm.call(
        "zrn_analitics.home",
        "get_commercial_hub_payload",
        []
      );
    } finally {
      this.state.commercialLoading = false;
    }
  }

  openHome() {
    return this.actionService.doAction("zrn_analitics.action_zrn_analitics_home");
  }

  get activeHub() {
    return this.hubs.find((hub) => hub.key === this.state.activeHub) || this.hubs[0];
  }

  get commercialPayload() {
    return this.state.commercialPayload || {
      summary: {
        sync_label: "",
        period_label: "",
        total_amount: 0,
        order_count: 0,
        customer_count: 0,
        point_count: 0,
        product_count: 0,
        brand_count: 0,
        average_ticket: 0,
        currency_symbol: "$",
      },
      has_brands: false,
      empty_message: "",
      revenue_series: [],
      brand_mix: [],
      top_customers: [],
      top_channels: [],
      top_products: [],
    };
  }

  get activeCommercialTab() {
    return (
      this.commercialTabs.find((tab) => tab.key === this.state.commercialTab) ||
      this.commercialTabs[0]
    );
  }

  get commercialSeriesMax() {
    const values = (this.commercialPayload.revenue_series || []).map((item) => item.value || 0);
    return Math.max(...values, 0);
  }

  get commercialCustomerMax() {
    const values = (this.commercialPayload.top_customers || []).map((item) => item.total_amount || 0);
    return Math.max(...values, 0);
  }

  getCommercialPolylinePoints() {
    const series = this.commercialPayload.revenue_series || [];
    if (!series.length) {
      return "";
    }
    const maxValue = this.commercialSeriesMax || 1;
    const width = 440;
    const height = 210;
    const xStep = series.length > 1 ? width / (series.length - 1) : width / 2;
    return series
      .map((item, index) => {
        const x = series.length > 1 ? index * xStep : width / 2;
        const y = height - (item.value / maxValue) * 170 - 20;
        return `${x},${y}`;
      })
      .join(" ");
  }

  getCommercialAreaPoints() {
    const linePoints = this.getCommercialPolylinePoints();
    if (!linePoints) {
      return "";
    }
    return `0,210 ${linePoints} 440,210`;
  }

  getCommercialDonutStyle() {
    const mix = this.commercialPayload.brand_mix || [];
    if (!mix.length) {
      return '';
    }
    let current = 0;
    const segments = mix
      .slice(0, 5)
      .map((item, index) => {
        const start = current;
        current += item.percentage;
        const colors = ["#1f4e8c", "#2f65ad", "#78a7df", "#a9c7eb", "#d6e6f8"];
        return `${colors[index % colors.length]} ${start}% ${current}%`;
      })
      .join(", ");
    return `background: conic-gradient(${segments});`;
  }

  getCommercialBarStyle(value) {
    const max = this.commercialCustomerMax || 1;
    const width = Math.max((value / max) * 100, 4);
    return `width: ${width}%;`;
  }

  formatMoney(value) {
    const amount = Number(value || 0);
    return new Intl.NumberFormat("es-GT", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(amount);
  }

  formatCount(value) {
    return new Intl.NumberFormat("es-GT", {
      maximumFractionDigits: 0,
    }).format(Number(value || 0));
  }
}

ZrnAnalyticsHubAction.template = "zrn_analitics.HubAction";

registry.category("actions").add("zrn_analitics.hubs", ZrnAnalyticsHubAction);
