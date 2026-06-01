/** @odoo-module **/

const ROOT_SELECTOR = ".zrn_prodigyn_reporting_commercial_view";
const BRAND = "#355eff";
const BRAND_SOFT = "#c9d6ff";
const BRAND_MID = "#88a4ff";
const BRAND_DEEP = "#1e3a8a";
const LINE = "#d7dee8";
const TEXT = "#10233d";
const MUTED = "#64748b";

function parseChartPayload(root, fieldName) {
  const source = root.querySelector(`[data-chart-data-field="${fieldName}"]`);
  if (!source) {
    return null;
  }
  const input = source.querySelector("textarea, input");
  const rawValue = input ? input.value : source.textContent;
  if (!rawValue) {
    return null;
  }
  try {
    return JSON.parse(rawValue.trim());
  } catch {
    return null;
  }
}

function getBaseOption() {
  return {
    animationDuration: 280,
    textStyle: {
      color: TEXT,
      fontFamily: "Inter, sans-serif",
    },
    grid: {
      left: 56,
      right: 22,
      top: 24,
      bottom: 44,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: LINE,
      borderWidth: 1,
      textStyle: {
        color: TEXT,
      },
    },
  };
}

function buildHorizontalBarOption(payload) {
  const option = getBaseOption();
  option.grid.left = 144;
  option.xAxis = {
    type: "value",
    axisLabel: { color: MUTED },
    splitLine: { lineStyle: { color: "#eef2f7" } },
  };
  option.yAxis = {
    type: "category",
    data: payload.labels || [],
    axisTick: { show: false },
    axisLabel: { color: TEXT, fontSize: 11 },
    axisLine: { lineStyle: { color: LINE } },
  };
  option.series = [{
    type: "bar",
    data: payload.values || [],
    barWidth: 18,
    itemStyle: {
      color: BRAND,
      borderRadius: [0, 4, 4, 0],
    },
  }];
  return option;
}

function buildStackedBarOption(payload) {
  const option = getBaseOption();
  option.legend = {
    top: 0,
    textStyle: { color: MUTED, fontSize: 11 },
  };
  option.grid.top = 48;
  option.xAxis = {
    type: "category",
    data: payload.labels || [],
    axisLabel: { color: MUTED, fontSize: 11, interval: 0, rotate: 12 },
    axisLine: { lineStyle: { color: LINE } },
  };
  option.yAxis = {
    type: "value",
    axisLabel: { color: MUTED },
    splitLine: { lineStyle: { color: "#eef2f7" } },
  };
  option.series = (payload.series || []).map((series, index) => ({
    ...series,
    barMaxWidth: 32,
    itemStyle: {
      color: [BRAND, BRAND_DEEP, BRAND_MID, BRAND_SOFT][index % 4],
    },
  }));
  return option;
}

function buildParetoOption(payload) {
  const option = getBaseOption();
  option.legend = {
    top: 0,
    textStyle: { color: MUTED, fontSize: 11 },
  };
  option.grid.top = 46;
  option.xAxis = {
    type: "category",
    data: payload.labels || [],
    axisLabel: { color: MUTED, fontSize: 11, interval: 0, rotate: 16 },
    axisLine: { lineStyle: { color: LINE } },
  };
  option.yAxis = [
    {
      type: "value",
      name: "Venta",
      nameTextStyle: { color: MUTED, fontSize: 11 },
      axisLabel: { color: MUTED },
      splitLine: { lineStyle: { color: "#eef2f7" } },
    },
    {
      type: "value",
      name: "%",
      min: 0,
      max: 100,
      nameTextStyle: { color: MUTED, fontSize: 11 },
      axisLabel: { color: MUTED, formatter: "{value}%" },
      splitLine: { show: false },
    },
  ];
  option.series = [
    {
      name: "Venta",
      type: "bar",
      data: payload.bar_values || [],
      itemStyle: {
        color: BRAND_MID,
        borderRadius: [4, 4, 0, 0],
      },
    },
    {
      name: "Acumulado",
      type: "line",
      yAxisIndex: 1,
      smooth: true,
      data: payload.line_values || [],
      lineStyle: { color: BRAND_DEEP, width: 2 },
      itemStyle: { color: BRAND_DEEP },
    },
  ];
  return option;
}

function buildHeatmapOption(payload) {
  return {
    animationDuration: 280,
    tooltip: {
      position: "top",
      backgroundColor: "#ffffff",
      borderColor: LINE,
      borderWidth: 1,
      textStyle: { color: TEXT },
      formatter(params) {
        return `${payload.day_labels?.[params.value[1]] || ""} / ${payload.week_labels?.[params.value[0]] || ""}: ${params.value[2]} pedidos`;
      },
    },
    grid: {
      left: 72,
      right: 22,
      top: 24,
      bottom: 36,
    },
    xAxis: {
      type: "category",
      data: payload.week_labels || [],
      splitArea: { show: true },
      axisLine: { lineStyle: { color: LINE } },
      axisLabel: { color: MUTED, fontSize: 11 },
    },
    yAxis: {
      type: "category",
      data: payload.day_labels || [],
      splitArea: { show: true },
      axisLine: { lineStyle: { color: LINE } },
      axisLabel: { color: MUTED, fontSize: 11 },
    },
    visualMap: {
      min: 0,
      max: Math.max(...(payload.data || []).map((item) => item[2]), 1),
      calculable: false,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      textStyle: { color: MUTED, fontSize: 11 },
      inRange: {
        color: ["#edf2ff", "#c9d6ff", "#88a4ff", "#4f73ff", "#1e3a8a"],
      },
    },
    series: [{
      name: "Pedidos",
      type: "heatmap",
      data: payload.data || [],
      label: { show: false },
      emphasis: {
        itemStyle: {
          shadowBlur: 4,
          shadowColor: "rgba(15, 23, 42, 0.16)",
        },
      },
    }],
  };
}

function buildDonutOption(payload) {
  return {
    animationDuration: 280,
    tooltip: {
      trigger: "item",
      backgroundColor: "#ffffff",
      borderColor: LINE,
      borderWidth: 1,
      textStyle: { color: TEXT },
    },
    legend: {
      orient: "vertical",
      right: 12,
      top: "middle",
      textStyle: { color: MUTED, fontSize: 11 },
    },
    series: [{
      type: "pie",
      radius: ["50%", "72%"],
      center: ["34%", "50%"],
      avoidLabelOverlap: true,
      itemStyle: {
        borderColor: "#ffffff",
        borderWidth: 2,
      },
      label: { show: false },
      emphasis: {
        label: {
          show: true,
          fontSize: 12,
          color: TEXT,
          formatter: "{b}\n{d}%",
        },
      },
      data: payload.series || [],
      color: [BRAND, BRAND_DEEP, BRAND_MID, "#9fb5ff", "#d6e0ff", "#7b92d9"],
    }],
  };
}

function buildScatterOption(payload) {
  return {
    animationDuration: 280,
    tooltip: {
      trigger: "item",
      backgroundColor: "#ffffff",
      borderColor: LINE,
      borderWidth: 1,
      textStyle: { color: TEXT },
      formatter(params) {
        return `${params.data.name}<br/>Ticket: ${params.data.value[0]}<br/>Pedidos: ${params.data.value[1]}<br/>Venta: ${params.data.value[2]}`;
      },
    },
    grid: {
      left: 58,
      right: 24,
      top: 24,
      bottom: 46,
    },
    xAxis: {
      type: "value",
      name: "Ticket promedio",
      nameTextStyle: { color: MUTED, fontSize: 11 },
      axisLabel: { color: MUTED },
      splitLine: { lineStyle: { color: "#eef2f7" } },
    },
    yAxis: {
      type: "value",
      name: "Pedidos",
      nameTextStyle: { color: MUTED, fontSize: 11 },
      axisLabel: { color: MUTED },
      splitLine: { lineStyle: { color: "#eef2f7" } },
    },
    series: [{
      type: "scatter",
      symbolSize(data) {
        return Math.max(14, Math.min(42, data[2] / 3500));
      },
      itemStyle: {
        color: BRAND_MID,
        borderColor: BRAND,
        borderWidth: 1.5,
        opacity: 0.9,
      },
      data: payload.points || [],
    }],
  };
}

function getChartOption(kind, payload) {
  if (!payload) {
    return null;
  }
  if (kind === "horizontal-bar") {
    return buildHorizontalBarOption(payload);
  }
  if (kind === "stacked-bar") {
    return buildStackedBarOption(payload);
  }
  if (kind === "pareto") {
    return buildParetoOption(payload);
  }
  if (kind === "heatmap") {
    return buildHeatmapOption(payload);
  }
  if (kind === "donut") {
    return buildDonutOption(payload);
  }
  if (kind === "scatter") {
    return buildScatterOption(payload);
  }
  return null;
}

function renderECharts(root) {
  if (!window.echarts) {
    return;
  }
  const canvases = Array.from(root.querySelectorAll("[data-echart-kind][data-echart-source]"));
  const chartEntries = [];

  canvases.forEach((canvas) => {
    const kind = canvas.dataset.echartKind;
    const source = canvas.dataset.echartSource;
    const payload = parseChartPayload(root, source);
    const option = getChartOption(kind, payload);
    if (!option) {
      return;
    }
    const chart = window.echarts.getInstanceByDom(canvas) || window.echarts.init(canvas);
    chart.setOption(option, true);
    chartEntries.push({ element: canvas, chart });
  });

  root.__commercialCharts = chartEntries;
}

function resizeVisibleCharts(root) {
  const chartEntries = root.__commercialCharts || [];
  chartEntries.forEach(({ element, chart }) => {
    if (element.offsetParent) {
      chart.resize();
    }
  });
}

function mountCommercialTabs(root) {
  if (root.dataset.commercialTabsMounted === "1") {
    return;
  }

  const tabButtons = Array.from(
    root.querySelectorAll("[data-commercial-chart-tabs='1'] [data-chart-tab]")
  );
  const tabPanels = Array.from(root.querySelectorAll("[data-chart-panel]"));

  if (!tabButtons.length || !tabPanels.length) {
    return;
  }

  renderECharts(root);

  const activateTab = (tabName) => {
    tabButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.chartTab === tabName);
    });
    tabPanels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.chartPanel === tabName);
    });
    requestAnimationFrame(() => resizeVisibleCharts(root));
  };

  tabButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      activateTab(button.dataset.chartTab);
    });
  });

  window.addEventListener("resize", () => resizeVisibleCharts(root));
  activateTab(tabButtons[0].dataset.chartTab);
  root.dataset.commercialTabsMounted = "1";
}

function scan(target = document) {
  target.querySelectorAll(ROOT_SELECTOR).forEach(mountCommercialTabs);
}

function startObserver() {
  scan();
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType !== 1) {
          continue;
        }
        if (node.matches?.(ROOT_SELECTOR)) {
          mountCommercialTabs(node);
          continue;
        }
        scan(node);
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startObserver, { once: true });
} else {
  startObserver();
}
