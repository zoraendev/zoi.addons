/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class ZrnPlanningFormController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
    this._chartPayload = null;
    this._chartInstances = new Map();
    this._homeChartResizeHandler = () => this.resizeHomeCharts();
    this._boundHomeChartClick = (event) => this.onHomeChartClick(event);
    this._boundReconciliationHeaderClick = (event) => this.onReconciliationHeaderClick(event);
    this._currentHomeResId = null;

    onMounted(() => {
      if (this.isPlanningHome) {
        window.addEventListener("resize", this._homeChartResizeHandler);
        this.rootRef.el?.addEventListener("click", this._boundHomeChartClick);
        this.loadAndRenderHomeCharts();
      }
      if (this.isInventoryReconciliation) {
        this.rootRef.el?.addEventListener("click", this._boundReconciliationHeaderClick);
        this.renderSelectAllHeaderCheckbox();
      }
    });

    onPatched(() => {
      if (this.isPlanningHome) {
        this.loadAndRenderHomeCharts();
      }
      if (this.isInventoryReconciliation) {
        this.renderSelectAllHeaderCheckbox();
      }
    });

    onWillUnmount(() => {
      if (this.isPlanningHome) {
        window.removeEventListener("resize", this._homeChartResizeHandler);
        this.rootRef.el?.removeEventListener("click", this._boundHomeChartClick);
        this.disposeHomeCharts();
      }
      if (this.isInventoryReconciliation) {
        this.rootRef.el?.removeEventListener("click", this._boundReconciliationHeaderClick);
      }
    });
  }

  get modelParams() {
    const modelParams = super.modelParams;
    const multiRecordModels = [
      "zrn_planning.home",
      "zrn_planning.production.planning",
    ];
    if (multiRecordModels.includes(this.props.resModel)) {
      const activeIds = this.props.context?.active_ids || [];
      if (activeIds.length > 1) {
        modelParams.config.resIds = activeIds;
        modelParams.config.resId =
          this.props.resId || this.props.context?.active_id || activeIds[0];
      }
    }
    return modelParams;
  }

  async openPlanningAction(methodName) {
    const action = await this.orm.call(this.props.resModel, methodName, [
      [this.model.root.resId],
    ]);
    await this.actionService.doAction(action);
  }

  openButton1() {
    return this.openPlanningAction("action_open_button_1");
  }

  openButton2() {
    return this.openPlanningAction("action_open_button_2");
  }

  openButton3() {
    return this.openPlanningAction("action_open_button_3");
  }

  openButton4() {
    return this.openPlanningAction("action_open_button_4");
  }

  openButton5() {
    return this.openPlanningAction("action_open_button_5");
  }

  get isPlanningHome() {
    return this.props.resModel === "zrn_planning.home";
  }

  get isInventoryReconciliation() {
    return this.props.resModel === "zrn_planning.inventory.reconciliation";
  }

  renderSelectAllHeaderCheckbox() {
    const headerCell = this.rootRef.el?.querySelector("th[data-name='is_selected']");
    if (!headerCell) {
      return;
    }
    const selectedCount = this.model?.root?.data?.selected_line_count || 0;
    const isChecked = selectedCount > 0;

    // Si ya existe, solo actualizar el icono
    const existing = headerCell.querySelector(".zrn_select_all_header_wrapper");
    if (existing) {
      const icon = existing.querySelector("i");
      if (icon) {
        icon.className = isChecked ? "fa fa-check-square-o" : "fa fa-square-o";
      }
      return;
    }

    // Primera vez: limpiar contenido del th y crear el wrapper
    headerCell.innerHTML = "";
    const wrapper = document.createElement("div");
    wrapper.className = "zrn_select_all_header_wrapper";

    const icon = document.createElement("i");
    icon.className = isChecked ? "fa fa-check-square-o" : "fa fa-square-o";

    wrapper.appendChild(icon);
    headerCell.appendChild(wrapper);
  }

  async onReconciliationHeaderClick(event) {
    const wrapper = event.target.closest(".zrn_select_all_header_wrapper");
    if (!wrapper) {
      return;
    }
    // No detenemos stopPropagation/preventDefault para que el framework de Odoo no pierda rastro del evento si lo necesita,
    // pero evitamos efectos nativos no deseados.
    event.preventDefault();

    const resId = this.model?.root?.resId;
    if (!resId) {
      return;
    }

    // Leemos el selected_line_count actual directamente del modelo de datos de Odoo
    const selectedCount = this.model.root.data.selected_line_count || 0;

    try {
      if (selectedCount === 0) {
        await this.orm.call("zrn_planning.inventory.reconciliation", "action_select_visible_lots", [[resId]]);
      } else {
        await this.orm.call("zrn_planning.inventory.reconciliation", "action_deselect_all_lots", [[resId]]);
      }
      // En Odoo 17, recargar el registro raiz del formulario se hace llamando a load() o reload() en la raíz.
      // Odoo actualiza la vista tras recargar el record.
      await this.model.root.load();
    } catch (err) {
      console.error("Error toggling reconciliation selection:", err);
    }
  }

  async loadAndRenderHomeCharts() {
    const resId = this.model?.root?.resId;
    if (!resId || !this.isPlanningHome) {
      return;
    }
    if (this._currentHomeResId !== resId || !this._chartPayload) {
      this._currentHomeResId = resId;
      this._chartPayload = await this.orm.call(
        "zrn_planning.home",
        "get_home_chart_payload",
        [[resId]],
      );
    }
    window.requestAnimationFrame(() => this.renderHomeCharts());
  }

  onHomeChartClick(event) {
    const button = event.target.closest(".zrn_planning_home_chart_type");
    if (!button || !this.rootRef.el?.contains(button)) {
      return;
    }
    event.preventDefault();
    const switcher = button.closest(".zrn_planning_home_chart_switch");
    if (!switcher) {
      return;
    }
    switcher
      .querySelectorAll(".zrn_planning_home_chart_type")
      .forEach((item) => item.classList.toggle("is-active", item === button));
    this.renderHomeCharts();
  }

  renderHomeCharts() {
    const rootEl = this.rootRef.el;
    if (!this.isPlanningHome || !rootEl) {
      return;
    }
    if (!window.echarts) {
      this.toggleEmptyState("production", true);
      this.toggleEmptyState("supply", true);
      return;
    }
    ["production", "supply"].forEach((chartKey) => {
      const payload = this._chartPayload?.[chartKey];
      const container = rootEl.querySelector(
        `[data-zrn-planning-chart="${chartKey}"]`,
      );
      if (!container) {
        return;
      }
      const hasData = Boolean(payload?.labels?.length);
      this.toggleEmptyState(chartKey, !hasData);
      if (!hasData) {
        this.disposeHomeChart(chartKey);
        return;
      }
      const chartType = this.getChartType(chartKey);
      let chart = this._chartInstances.get(chartKey);
      if (!chart) {
        chart = window.echarts.init(container, null, {
          width: 'auto',
          height: 320
        });
        this._chartInstances.set(chartKey, chart);
      }
      chart.setOption(this.buildHomeChartOption(payload, chartType), true);
      chart.resize();
    });
  }

  getChartType(chartKey) {
    const activeButton = this.rootRef.el?.querySelector(
      `[data-chart-key="${chartKey}"] .zrn_planning_home_chart_type.is-active`,
    );
    return activeButton?.dataset?.zrnChartType || "bar";
  }

  buildHomeChartOption(payload, chartType) {
    const generatedLabel = `${payload.order_label} generadas`;
    const completedLabel = `${payload.order_label} finalizadas`;
    const generatedTotal = (payload.orders_generated || []).reduce(
      (total, value) => total + value,
      0,
    );
    const completedTotal = (payload.orders_completed || []).reduce(
      (total, value) => total + value,
      0,
    );
    if (chartType === "pie") {
      return {
        color: ["#875A7B", "#5f8dd3", "#22a06b"],
        tooltip: { trigger: "item" },
        legend: { bottom: 0, left: "center" },
        series: [
          {
            type: "pie",
            radius: ["45%", "72%"],
            avoidLabelOverlap: true,
            label: { formatter: "{b}: {c}" },
            data: [
              { value: payload.plan_count || 0, name: "Planes creados" },
              { value: generatedTotal, name: generatedLabel },
              { value: completedTotal, name: completedLabel },
            ],
          },
        ],
      };
    }
    return {
      color: ["#5f8dd3", "#22a06b"],
      tooltip: { trigger: "axis" },
      legend: { top: 0, left: "left" },
      grid: { top: 42, right: 12, bottom: 54, left: 44, containLabel: true },
      xAxis: {
        type: "category",
        data: payload.labels,
        axisLabel: {
          interval: 0,
          rotate: 15,
          formatter: function (value) {
            if (!value) return '';
            // Si el nombre es muy largo, lo dividimos en palabras y saltamos línea cada 3 palabras
            const words = value.split(' ');
            let formatted = '';
            for (let i = 0; i < words.length; i++) {
              formatted += words[i] + ' ';
              if ((i + 1) % 3 === 0) {
                formatted += '\n';
              }
            }
            return formatted.trim();
          },
          fontSize: 10,
        },
      },
      yAxis: { type: "value" },
      series: [
        {
          name: generatedLabel,
          type: chartType,
          smooth: chartType === "line",
          showSymbol: true,
          symbol: "circle",
          symbolSize: 8,
          data: payload.orders_generated,
        },
        {
          name: completedLabel,
          type: chartType,
          smooth: chartType === "line",
          showSymbol: true,
          symbol: "circle",
          symbolSize: 8,
          data: payload.orders_completed,
        },
      ],
    };
  }

  toggleEmptyState(chartKey, isEmpty) {
    const container = this.rootRef.el?.querySelector(
      `[data-zrn-planning-chart="${chartKey}"]`,
    );
    const empty = this.rootRef.el?.querySelector(
      `[data-zrn-planning-chart-empty="${chartKey}"]`,
    );
    container?.classList.toggle("d-none", isEmpty);
    empty?.classList.toggle("d-none", !isEmpty);
  }

  resizeHomeCharts() {
    this._chartInstances.forEach((chart) => chart.resize());
  }

  disposeHomeChart(chartKey) {
    const chart = this._chartInstances.get(chartKey);
    if (chart) {
      chart.dispose();
      this._chartInstances.delete(chartKey);
    }
  }

  disposeHomeCharts() {
    this._chartInstances.forEach((chart) => chart.dispose());
    this._chartInstances.clear();
  }
}

ZrnPlanningFormController.template = "web.FormView";

export const ZrnPlanningFormView = {
  ...formView,
  Controller: ZrnPlanningFormController,
};

registry.category("views").add("zrn_planning_form", ZrnPlanningFormView);
