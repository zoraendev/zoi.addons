/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onPatched, onWillStart, onWillUnmount, useState } from "@odoo/owl";

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
    this._charts = new Map();
    this._chartResizeHandler = () => this.resizeCharts();
    this.state = useState({
      activeHub: "direction",
      commercialTab: "overview",
      commercialPayload: null,
      commercialLoading: false,
      coveragePayload: null,
      coverageLoading: false,
      selectedPortfolioUnit: "",
      portfolioExpanded: {},
    });
    onWillStart(async () => {
      await Promise.all([
        this.loadCommercialPayload(),
        this.loadCoveragePayload(),
      ]);
    });
    onMounted(() => {
      window.addEventListener("resize", this._chartResizeHandler);
      this.renderCharts();
    });
    onPatched(() => {
      this.renderCharts();
    });
    onWillUnmount(() => {
      window.removeEventListener("resize", this._chartResizeHandler);
      this.disposeCharts();
    });
  }

  async setActiveHub(hubKey) {
    this.state.activeHub = hubKey;
    if (hubKey === "commercial") {
      await Promise.all([
        this.loadCommercialPayload(),
        this.loadCoveragePayload(),
      ]);
    }
  }

  async setCommercialTab(tabKey) {
    this.state.commercialTab = tabKey;
    if (tabKey === "cobertura") {
      await this.loadCoveragePayload();
    }
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

  async loadCoveragePayload(force = false) {
    if (this.state.coveragePayload && !force) {
      return;
    }
    this.state.coverageLoading = true;
    try {
      this.state.coveragePayload = await this.orm.call(
        "zrn_analitics.home",
        "get_coverage_dashboard_data",
        []
      );
    } finally {
      this.state.coverageLoading = false;
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
      brand_catalog: [],
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

  get coveragePayload() {
    return this.state.coveragePayload || {
      summary_cards: [],
      coverage_by_channel: [],
      pdv_universe: { total: 0, by_channel: {}, by_municipio: {} },
      channel_brand_matrix: { brands: [], rows: [] },
      sku_distribution: [],
      portfolio_holes: { core_skus: [], rows: [] },
      clients_at_risk: [],
      notes_sources: [],
    };
  }

  get hasCommercialRevenueSeries() {
    return Boolean((this.commercialPayload.revenue_series || []).length);
  }

  get hasCommercialBrandMix() {
    return Boolean((this.commercialPayload.brand_mix || []).length);
  }

  get hasCommercialTopCustomers() {
    return Boolean((this.commercialPayload.top_customers || []).length);
  }

  get hasEchartsLibrary() {
    return Boolean(window.echarts);
  }

  get coverageMatrixMax() {
    const values = [];
    (this.coveragePayload.channel_brand_matrix.rows || []).forEach((row) => {
      (row.cells || []).forEach((cell) => values.push(Number(cell.revenue || 0)));
    });
    return Math.max(...values, 0);
  }

  getCoverageBarStyle(value, total) {
    const base = total || 1;
    const width = Math.max((Number(value || 0) / base) * 100, 4);
    return `width: ${width}%;`;
  }

  getCoverageMatrixCellStyle(value) {
    const max = this.coverageMatrixMax || 1;
    const ratio = Number(value || 0) / max;
    const opacity = Math.min(0.9, Math.max(0.08, ratio));
    return `background: rgba(31, 78, 140, ${opacity});`;
  }

  get commercialPortfolio() {
    return this.buildCommercialPortfolio();
  }

  get activePortfolioUnit() {
    const units = this.commercialPortfolio.units || [];
    if (!units.length) {
      return null;
    }
    return (
      units.find((unit) => unit.key === this.state.selectedPortfolioUnit) ||
      units[0]
    );
  }

  selectPortfolioUnit(unitKey) {
    this.state.selectedPortfolioUnit = unitKey;
  }

  togglePortfolioRow(rowKey) {
    const expanded = { ...this.state.portfolioExpanded };
    expanded[rowKey] = !expanded[rowKey];
    this.state.portfolioExpanded = expanded;
  }

  isPortfolioRowExpanded(rowKey) {
    return Boolean(this.state.portfolioExpanded[rowKey]);
  }

  isPortfolioRowVisible(row) {
    return (row.ancestor_keys || []).every((key) => this.isPortfolioRowExpanded(key));
  }

  getPortfolioUnitRevenueStyle(unit) {
    const total = this.commercialPortfolio.totalRevenue || 1;
    const width = Math.max((unit.revenue / total) * 100, 6);
    return `width: ${width}%;`;
  }

  getPortfolioBrandShareStyle(brand) {
    const unit = this.activePortfolioUnit;
    const total = unit?.revenue || 1;
    const width = Math.max((brand.revenue / total) * 100, 6);
    return `width: ${width}%;`;
  }

  buildCommercialPortfolio() {
    const brandMix = this.commercialPayload.brand_mix || [];
    const brandCatalog = this.commercialPayload.brand_catalog || [];
    const productRows = this.commercialPayload.top_products || [];
    const currencySymbol = this.commercialPayload.summary?.currency_symbol || "$";
    const businessUnits = [
      { key: "grab_go", name: "Grab and Go", color: "#bd1730" },
      { key: "food_service", name: "Food Service", color: "#f18f01" },
      { key: "sin_un", name: "Sin UN", color: "#9aa4b2" },
    ];
    const baseBrands = (brandMix.length ? brandMix : brandCatalog).map((brand, index) => ({
      key: `brand_${index + 1}`,
      name: brand.name,
      revenue: Number(brand.value || 0),
      percentage: Number(brand.percentage || 0),
      product_count: Number(brand.product_count || 0),
    }));
    if (!baseBrands.length) {
      return {
        hasBrands: false,
        hasRevenue: false,
        currencySymbol,
        totalRevenue: 0,
        units: [],
        drillRows: [],
      };
    }

    const brandProducts = new Map(baseBrands.map((brand) => [brand.key, []]));
    productRows.forEach((product, index) => {
      const targetBrand = baseBrands[index % baseBrands.length];
      brandProducts.get(targetBrand.key).push({
        name: product.name,
        category_name: product.category_name,
        quantity_sold: Number(product.quantity_sold || 0),
        sales_amount: Number(product.sales_amount || 0),
      });
    });

    const totalRevenue = baseBrands.reduce((sum, brand) => sum + brand.revenue, 0);
    const lineNames = ["Fresco", "Snacks", "Base", "Food Prep", "Servicios"];
    const units = businessUnits.map((definition, unitIndex) => {
      const assignedBrands = baseBrands
        .filter((_brand, brandIndex) => brandIndex % businessUnits.length === unitIndex)
        .map((brand, brandIndex) => {
          const products = brandProducts.get(brand.key) || [];
          const lineCount = Math.min(2, Math.max(products.length ? 2 : 1, 1));
          const lineShares = lineCount === 1 ? [1] : [0.62, 0.38];
          const lines = lineShares.map((share, lineIndex) => {
            const productSubset = products.filter((_, productIndex) => productIndex % lineCount === lineIndex);
            const revenue = Number((brand.revenue * share).toFixed(2));
            const unitsSold = productSubset.reduce((sum, product) => sum + product.quantity_sold, 0);
            const marginPct = 0.16 + ((unitIndex + brandIndex + lineIndex) % 4) * 0.035;
            return {
              key: `${brand.key}_line_${lineIndex + 1}`,
              name: lineNames[(unitIndex + brandIndex + lineIndex) % lineNames.length],
              revenue,
              mix_percentage: totalRevenue ? (revenue / totalRevenue) * 100 : 0,
              units_sold: unitsSold,
              billed_lines: Math.max(productSubset.length, 1),
              sku_count: Math.max(productSubset.length, brand.product_count ? 1 : 0),
              margin_amount: Number((revenue * marginPct).toFixed(2)),
              margin_pct: marginPct * 100,
              skus: productSubset.map((product) => ({
                key: `${brand.key}_sku_${product.name}`,
                name: product.name,
                revenue: product.sales_amount,
                mix_percentage: totalRevenue ? (product.sales_amount / totalRevenue) * 100 : 0,
                units_sold: product.quantity_sold,
              })),
            };
          });
          const revenue = lines.reduce((sum, line) => sum + line.revenue, 0);
          const marginAmount = lines.reduce((sum, line) => sum + line.margin_amount, 0);
          return {
            ...brand,
            lines,
            billed_lines: lines.reduce((sum, line) => sum + line.billed_lines, 0),
            sku_count: lines.reduce((sum, line) => sum + line.sku_count, 0),
            margin_amount: Number(marginAmount.toFixed(2)),
            margin_pct: revenue ? (marginAmount / revenue) * 100 : 0,
          };
        });

      const revenue = assignedBrands.reduce((sum, brand) => sum + brand.revenue, 0);
      const marginAmount = assignedBrands.reduce((sum, brand) => sum + brand.margin_amount, 0);
      return {
        ...definition,
        brands: assignedBrands,
        revenue: Number(revenue.toFixed(2)),
        mix_percentage: totalRevenue ? (revenue / totalRevenue) * 100 : 0,
        sku_count: assignedBrands.reduce((sum, brand) => sum + brand.sku_count, 0),
        brand_count: assignedBrands.length,
        billed_lines: assignedBrands.reduce((sum, brand) => sum + brand.billed_lines, 0),
        margin_amount: Number(marginAmount.toFixed(2)),
        margin_pct: revenue ? (marginAmount / revenue) * 100 : 0,
      };
    }).filter((unit) => unit.brands.length);

    const drillRows = [];
    units.forEach((unit) => {
      drillRows.push({
        key: unit.key,
        ancestor_keys: [],
        level: "unit",
        label: unit.name,
        revenue: unit.revenue,
        mix_percentage: unit.mix_percentage,
        units_sold: 0,
        billed_lines: unit.billed_lines,
        sku_count: unit.sku_count,
        margin_amount: unit.margin_amount,
        margin_pct: unit.margin_pct,
        color: unit.color,
      });
      unit.brands.forEach((brand) => {
        drillRows.push({
          key: brand.key,
          ancestor_keys: [unit.key],
          level: "brand",
          label: brand.name,
          revenue: brand.revenue,
          mix_percentage: totalRevenue ? (brand.revenue / totalRevenue) * 100 : 0,
          units_sold: 0,
          billed_lines: brand.billed_lines,
          sku_count: brand.sku_count,
          margin_amount: brand.margin_amount,
          margin_pct: brand.margin_pct,
        });
        brand.lines.forEach((line) => {
          drillRows.push({
            key: line.key,
            ancestor_keys: [unit.key, brand.key],
            level: "line",
            label: line.name,
            revenue: line.revenue,
            mix_percentage: line.mix_percentage,
            units_sold: line.units_sold,
            billed_lines: line.billed_lines,
            sku_count: line.sku_count,
            margin_amount: line.margin_amount,
            margin_pct: line.margin_pct,
          });
          line.skus.forEach((sku) => {
            drillRows.push({
              key: sku.key,
              ancestor_keys: [unit.key, brand.key, line.key],
              level: "sku",
              label: sku.name,
              revenue: sku.revenue,
              mix_percentage: sku.mix_percentage,
              units_sold: sku.units_sold,
              billed_lines: 0,
              sku_count: 1,
              margin_amount: 0,
              margin_pct: 0,
            });
          });
        });
      });
    });

    return {
      hasBrands: true,
      hasRevenue: totalRevenue > 0,
      currencySymbol,
      totalRevenue,
      units,
      drillRows,
    };
  }

  renderCharts() {
    if (!window.echarts || !this.el || this.state.activeHub !== "commercial") {
      return;
    }
    this.renderOverviewLineChart();
    this.renderOverviewDonutChart();
    this.renderOverviewCustomersChart();
  }

  getChart(themeKey) {
    const element = this.el?.querySelector(`[data-zrn-chart="${themeKey}"]`);
    if (!element || !element.offsetParent) {
      return null;
    }
    const existing = this._charts.get(themeKey);
    if (existing && existing.getDom() === element) {
      return existing;
    }
    if (existing) {
      existing.dispose();
    }
    const chart = window.echarts.getInstanceByDom(element) || window.echarts.init(element);
    this._charts.set(themeKey, chart);
    return chart;
  }

  renderOverviewLineChart() {
    if (this.state.commercialTab !== "overview") {
      return;
    }
    const series = this.commercialPayload.revenue_series || [];
    if (!series.length) {
      return;
    }
    const chart = this.getChart("overview-line");
    if (!chart) {
      return;
    }
    chart.setOption({
      animationDuration: 650,
      animationEasing: "cubicOut",
      grid: { top: 16, right: 20, bottom: 26, left: 24, containLabel: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "line" },
        valueFormatter: (value) => `${this.commercialPayload.summary.currency_symbol} ${this.formatMoney(value)}`,
      },
      xAxis: {
        type: "category",
        data: series.map((item) => item.label),
        boundaryGap: false,
        axisLine: { lineStyle: { color: "#d6deea" } },
        axisTick: { show: false },
        axisLabel: { color: "#5f6b7a", fontSize: 11 },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#edf2f8" } },
        axisLabel: {
          color: "#5f6b7a",
          fontSize: 11,
          formatter: (value) => this.formatMoney(value),
        },
      },
      series: [{
        type: "line",
        smooth: 0.25,
        symbol: "circle",
        symbolSize: 8,
        data: series.map((item) => Number(item.value || 0)),
        lineStyle: { color: "#bd1730", width: 3 },
        itemStyle: { color: "#bd1730", borderColor: "#ffffff", borderWidth: 2 },
        areaStyle: {
          color: new window.echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(31, 78, 140, 0.22)" },
            { offset: 1, color: "rgba(31, 78, 140, 0.04)" },
          ]),
        },
      }],
    }, true);
  }

  renderOverviewDonutChart() {
    if (this.state.commercialTab !== "overview") {
      return;
    }
    const mix = (this.commercialPayload.brand_mix || []).slice(0, 5);
    if (!mix.length) {
      return;
    }
    const chart = this.getChart("overview-donut");
    if (!chart) {
      return;
    }
    chart.setOption({
      animationDuration: 700,
      animationEasing: "cubicOut",
      color: ["#1f4e8c", "#2f65ad", "#78a7df", "#a9c7eb", "#d6e6f8"],
      tooltip: {
        trigger: "item",
        formatter: ({ name, value, percent }) =>
          `${name}<br/>${this.commercialPayload.summary.currency_symbol} ${this.formatMoney(value)}<br/>${percent}% del mix`,
      },
      legend: {
        orient: "vertical",
        right: 0,
        top: "middle",
        icon: "roundRect",
        itemWidth: 14,
        itemHeight: 10,
        textStyle: { color: "#5f6b7a", fontSize: 11 },
      },
      series: [{
        type: "pie",
        radius: ["48%", "72%"],
        center: ["32%", "50%"],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: "#ffffff", borderWidth: 2 },
        label: { show: false },
        emphasis: { scale: true, scaleSize: 7 },
        data: mix.map((item) => ({
          name: item.name,
          value: Number(item.value || 0),
        })),
      }],
    }, true);
  }

  renderOverviewCustomersChart() {
    if (this.state.commercialTab !== "overview") {
      return;
    }
    const customers = this.commercialPayload.top_customers || [];
    if (!customers.length) {
      return;
    }
    const chart = this.getChart("overview-customers");
    if (!chart) {
      return;
    }
    const reversed = [...customers].reverse();
    chart.setOption({
      animationDuration: 700,
      animationEasing: "cubicOut",
      grid: { top: 8, right: 16, bottom: 8, left: 120, containLabel: false },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        valueFormatter: (value) => `${this.commercialPayload.summary.currency_symbol} ${this.formatMoney(value)}`,
      },
      xAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#edf2f8" } },
        axisLabel: { color: "#5f6b7a", fontSize: 11, formatter: (value) => this.formatMoney(value) },
      },
      yAxis: {
        type: "category",
        data: reversed.map((item) => item.name),
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: {
          color: "#334155",
          fontSize: 11,
          width: 110,
          overflow: "truncate",
        },
      },
      series: [{
        type: "bar",
        data: reversed.map((item) => Number(item.total_amount || 0)),
        barWidth: 18,
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: new window.echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: "#e34c62" },
            { offset: 1, color: "#bd1730" },
          ]),
        },
        emphasis: { focus: "series" },
      }],
    }, true);
  }

  resizeCharts() {
    this._charts.forEach((chart) => chart.resize());
  }

  disposeCharts() {
    this._charts.forEach((chart) => chart.dispose());
    this._charts.clear();
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

  formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
  }
}

ZrnAnalyticsHubAction.template = "zrn_analitics.HubAction";

registry.category("actions").add("zrn_analitics.hubs", ZrnAnalyticsHubAction);
