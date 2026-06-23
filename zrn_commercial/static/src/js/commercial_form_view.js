/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

// Identificadores de los paneles del dashboard
const CHART_KEYS = ["prospects", "opportunities", "brands", "channels"];

// Paleta de colores predefinida de Zoraen para mantener sobriedad
const CHART_COLORS_SINGLE = ["#5f8dd3", "#875A7B", "#22a06b", "#d9a21b", "#e45f5c", "#6cc3d5"];
const CHART_COLORS_DUAL = ["#5f8dd3", "#22a06b"];

/**
 * ZrnCommercialHomeController
 * Controlador para la vista de dashboard principal de Zoraen Commercial.
 * Inicializa y maneja instancias de gráficas ECharts cargadas dinámicamente.
 * 
 * Reutiliza las clases CSS provistas por zrn_planning para uniformidad visual
 * pero utiliza selectores específicos (`data-zrn-commercial-chart`) para evitar conflictos.
 */
class ZrnCommercialHomeController extends FormController {
  setup() {
    super.setup();
    this.orm = useService("orm");
    this._chartPayload = null; // Cache del payload de datos obtenido de Python
    this._chartInstances = new Map(); // Mapa de key -> instancia de ECharts
    this._chartResizeHandler = () => this.resizeCharts();
    this._boundChartClick = (event) => this.onChartSwitchClick(event);
    this._currentResId = null;

    // Ciclo de vida Owl: montaje de vista en el DOM
    onMounted(() => {
      window.addEventListener("resize", this._chartResizeHandler);
      this.el?.addEventListener("click", this._boundChartClick);
      this.loadAndRenderCharts();
    });

    // Ciclo de vida Owl: actualización/re-renderizado del componente
    onPatched(() => {
      this.loadAndRenderCharts();
    });

    // Ciclo de vida Owl: destrucción del componente, limpieza de listeners e instancias
    onWillUnmount(() => {
      window.removeEventListener("resize", this._chartResizeHandler);
      this.el?.removeEventListener("click", this._boundChartClick);
      this.disposeAllCharts();
    });
  }

  /**
   * Carga el payload del backend vía RPC y renderiza las gráficas
   */
  async loadAndRenderCharts() {
    const resId = this.model?.root?.resId;
    if (!resId) {
      return;
    }
    // Optimización: Solo llamar a RPC si cambia el ID del registro o no hay caché
    if (this._currentResId !== resId || !this._chartPayload) {
      this._currentResId = resId;
      this._chartPayload = await this.orm.call(
        "zrn_commercial.home",
        "get_home_chart_payload",
        [[resId]],
      );
    }
    // Ejecutar renderizado en el siguiente frame de animación para asegurar DOM listo
    window.requestAnimationFrame(() => this.renderCharts());
  }

  /**
   * Manejador de clic para los selectores de tipo de gráfico (Barras/Línea/Pie)
   */
  onChartSwitchClick(event) {
    const button = event.target.closest(".zrn_planning_home_chart_type");
    if (!button || !this.el?.contains(button)) {
      return;
    }
    event.preventDefault();
    const switcher = button.closest(".zrn_planning_home_chart_switch");
    if (!switcher) {
      return;
    }
    // Intercambiar clase activa
    switcher
      .querySelectorAll(".zrn_planning_home_chart_type")
      .forEach((item) => item.classList.toggle("is-active", item === button));
    this.renderCharts();
  }

  /**
   * Instancia/Actualiza cada una de las 4 gráficas del dashboard con los datos del payload
   */
  renderCharts() {
    if (!this.el || !window.echarts) {
      CHART_KEYS.forEach((key) => this.toggleEmptyState(key, true));
      return;
    }
    CHART_KEYS.forEach((chartKey) => {
      const payload = this._chartPayload?.[chartKey];
      const container = this.el.querySelector(
        `[data-zrn-commercial-chart="${chartKey}"]`,
      );
      if (!container) {
        return;
      }
      
      // Control de estados vacíos (cuando no hay leads, marcas o canales cargados)
      const hasData = Boolean(payload?.labels?.length);
      this.toggleEmptyState(chartKey, !hasData);
      if (!hasData) {
        this.disposeChart(chartKey);
        return;
      }
      
      const chartType = this.getChartType(chartKey);
      let chart = this._chartInstances.get(chartKey);
      if (!chart) {
        chart = window.echarts.init(container);
        this._chartInstances.set(chartKey, chart);
      }
      
      // Construir opciones dependiendo de si el payload es multiserie (dual) o simple (single)
      const option = payload.series
        ? this.buildDualSeriesOption(payload, chartType)
        : this.buildSingleSeriesOption(payload, chartType);
      
      chart.setOption(option, true);
      chart.resize();
    });
  }

  /**
   * Obtiene el tipo de gráfica actualmente seleccionado para una key dada
   */
  getChartType(chartKey) {
    const activeButton = this.el?.querySelector(
      `[data-chart-key="${chartKey}"] .zrn_planning_home_chart_type.is-active`,
    );
    return activeButton?.dataset?.zrnChartType || "bar";
  }

  /**
   * Construye el setOption de ECharts para datos unidimensionales (Prospectos/Oportunidades)
   */
  buildSingleSeriesOption(payload, chartType) {
    if (chartType === "pie") {
      return {
        color: CHART_COLORS_SINGLE,
        tooltip: { trigger: "item" },
        legend: { bottom: 0, left: "center" },
        series: [
          {
            type: "pie",
            radius: ["45%", "72%"],
            avoidLabelOverlap: true,
            label: { formatter: "{b}: {c}" },
            data: payload.labels.map((label, i) => ({
              value: payload.values[i],
              name: label,
            })),
          },
        ],
      };
    }
    return {
      color: CHART_COLORS_SINGLE,
      tooltip: { trigger: "axis" },
      grid: { top: 30, right: 12, bottom: 28, left: 44, containLabel: true },
      xAxis: {
        type: "category",
        data: payload.labels,
        axisLabel: {
          interval: 0,
          rotate: payload.labels.length > 4 ? 20 : 0, // Rotar etiquetas si son muchas
        },
      },
      yAxis: { type: "value" },
      series: [
        {
          name: payload.series_label,
          type: chartType,
          smooth: chartType === "line",
          data: payload.values,
        },
      ],
    };
  }

  /**
   * Construye el setOption de ECharts para datos multiserie (Marcas/Canales)
   */
  buildDualSeriesOption(payload, chartType) {
    if (chartType === "pie") {
      // Para Pie, consolidamos totales de las series para evitar superposición
      const totals = payload.series.map((s) =>
        (s.data || []).reduce((acc, v) => acc + v, 0),
      );
      return {
        color: CHART_COLORS_DUAL,
        tooltip: { trigger: "item" },
        legend: { bottom: 0, left: "center" },
        series: [
          {
            type: "pie",
            radius: ["45%", "72%"],
            avoidLabelOverlap: true,
            label: { formatter: "{b}: {c}" },
            data: payload.series.map((s, i) => ({
              value: totals[i],
              name: s.name,
            })),
          },
        ],
      };
    }
    return {
      color: CHART_COLORS_DUAL,
      tooltip: { trigger: "axis" },
      legend: { top: 0, left: "left" },
      grid: { top: 42, right: 12, bottom: 28, left: 44, containLabel: true },
      xAxis: {
        type: "category",
        data: payload.labels,
        axisLabel: {
          interval: 0,
          rotate: payload.labels.length > 4 ? 20 : 0,
        },
      },
      yAxis: { type: "value" },
      series: payload.series.map((s) => ({
        name: s.name,
        type: chartType,
        smooth: chartType === "line",
        data: s.data,
      })),
    };
  }

  /**
   * Alterna la visibilidad del contenedor de la gráfica y el mensaje "Sin datos"
   */
  toggleEmptyState(chartKey, isEmpty) {
    const container = this.el?.querySelector(
      `[data-zrn-commercial-chart="${chartKey}"]`,
    );
    const empty = this.el?.querySelector(
      `[data-zrn-commercial-chart-empty="${chartKey}"]`,
    );
    container?.classList.toggle("d-none", isEmpty);
    empty?.classList.toggle("d-none", !isEmpty);
  }

  /**
   * Redimensiona todas las gráficas activas (llamado en resize del navegador)
   */
  resizeCharts() {
    this._chartInstances.forEach((chart) => chart.resize());
  }

  /**
   * Destruye una gráfica individual y libera memoria
   */
  disposeChart(chartKey) {
    const chart = this._chartInstances.get(chartKey);
    if (chart) {
      chart.dispose();
      this._chartInstances.delete(chartKey);
    }
  }

  /**
   * Destruye todas las gráficas
   */
  disposeAllCharts() {
    this._chartInstances.forEach((chart) => chart.dispose());
    this._chartInstances.clear();
  }
}

// Vincula la plantilla base de formulario de Odoo
ZrnCommercialHomeController.template = "web.FormView";

export const ZrnCommercialHomeView = {
  ...formView,
  Controller: ZrnCommercialHomeController,
};

// Registra la vista en el registro global de vistas de Odoo Backend
registry.category("views").add("zrn_commercial_home", ZrnCommercialHomeView);
