/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

const CHART_KEYS = ["channelRevenue", "categoryProducts", "brandProducts"];
const CHART_COLORS = ["#6f5d9a", "#2f80a7", "#2f8f6f", "#c58b2b", "#9a5f6d", "#5c6f82"];

class ZrnCommercialHomeDashboardController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
    this.payload = null;
    this.currentResId = null;
    this.charts = new Map();
    this.resizeCharts = () => this.charts.forEach((chart) => chart.resize());

    onMounted(() => {
      window.addEventListener("resize", this.resizeCharts);
      this.loadDashboard();
    });
    onPatched(() => this.loadDashboard());
    onWillUnmount(() => {
      window.removeEventListener("resize", this.resizeCharts);
      this.charts.forEach((chart) => chart.dispose());
      this.charts.clear();
    });
  }

  async loadDashboard() {
    const resId = this.model?.root?.resId;
    if (!resId || !window.echarts) {
      return;
    }
    if (this.currentResId !== resId || !this.payload) {
      this.currentResId = resId;
      this.payload = await this.orm.call(
        "zrn_commercial.home",
        "get_dashboard_payload",
        [[resId]],
      );
    }
    window.requestAnimationFrame(() => this.renderCharts());
  }

  renderCharts() {
    CHART_KEYS.forEach((key) => {
      const chartEl = this.rootRef.el?.querySelector(`[data-zrn-commercial-chart="${key}"]`);
      if (!chartEl) {
        return;
      }
      const payload = this.payload?.[key] || {};
      const labels = payload.labels || [];
      const values = payload.values || [];
      const hasData = values.some((value) => Number(value) > 0);
      this.toggleEmpty(key, !hasData);
      if (!hasData) {
        this.disposeChart(key);
        return;
      }
      const chart = this.getChart(key, chartEl);
      const option = key === "channelRevenue"
        ? this.buildChannelRevenueOption(payload)
        : this.buildProductOption(payload, key);
      chart.setOption(option, true);
      chart.resize();
    });
  }

  getChart(key, chartEl) {
    if (!this.charts.has(key)) {
      this.charts.set(key, window.echarts.init(chartEl));
    }
    return this.charts.get(key);
  }

  disposeChart(key) {
    const chart = this.charts.get(key);
    if (chart) {
      chart.dispose();
      this.charts.delete(key);
    }
  }

  toggleEmpty(key, isEmpty) {
    const chartEl = this.rootRef.el?.querySelector(`[data-zrn-commercial-chart="${key}"]`);
    const emptyEl = this.rootRef.el?.querySelector(`[data-zrn-commercial-chart-empty="${key}"]`);
    chartEl?.classList.toggle("d-none", isEmpty);
    emptyEl?.classList.toggle("d-none", !isEmpty);
  }

  buildChannelRevenueOption(payload) {
    const currency = this.payload?.currency || "";
    return {
      color: [CHART_COLORS[0]],
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (params) => {
          const item = params[0];
          const orderCount = payload.counts?.[item.dataIndex] || 0;
          return `${item.name}<br/>Ingresos: ${currency}${Number(item.value).toLocaleString()}<br/>Ordenes: ${orderCount}`;
        },
      },
      grid: { top: 14, right: 24, bottom: 28, left: 130, containLabel: true },
      xAxis: { type: "value" },
      yAxis: { type: "category", data: payload.labels, inverse: true },
      series: [{
        name: "Ingresos",
        type: "bar",
        barMaxWidth: 22,
        data: payload.values,
      }],
    };
  }

  buildProductOption(payload, key) {
    const chartType = key === "brandProducts" ? "pie" : "bar";
    if (chartType === "pie") {
      return {
        color: CHART_COLORS,
        tooltip: { trigger: "item" },
        legend: { bottom: 0, left: "center" },
        series: [{
          type: "pie",
          radius: ["45%", "72%"],
          data: payload.labels.map((label, index) => ({
            name: label,
            value: payload.values[index],
          })),
        }],
      };
    }
    return {
      color: [CHART_COLORS[1]],
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      grid: { top: 14, right: 18, bottom: 50, left: 44, containLabel: true },
      xAxis: {
        type: "category",
        data: payload.labels,
        axisLabel: { interval: 0, rotate: payload.labels.length > 4 ? 24 : 0 },
      },
      yAxis: { type: "value", minInterval: 1 },
      series: [{
        name: "Productos",
        type: "bar",
        barMaxWidth: 28,
        data: payload.values,
      }],
    };
  }
}

ZrnCommercialHomeDashboardController.template = "web.FormView";

registry.category("views").add("zrn_commercial_home_dashboard", {
  ...formView,
  Controller: ZrnCommercialHomeDashboardController,
});
