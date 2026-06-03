/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onPatched, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";

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
    this.rootRef = useRef("hubRoot");
    this.hubs = HUBS;
    this.commercialTabs = COMMERCIAL_TABS;
    this._charts = new Map();
    this._chartRenderTimeouts = [];
    this._chartRenderFrame = 0;
    this._resizeObserver = null;
    this._chartResizeHandler = () => this.resizeCharts();
    this.state = useState({
      activeHub: "direction",
      commercialTab: "overview",
      commercialPayload: null,
      commercialLoading: false,
      overviewFilters: {
        period_key: "ytd",
        channel: "",
        brand: "",
        category: "",
        search: "",
      },
      portfolioFilters: {
        period_key: "ytd",
        channel: "",
        brand: "",
        category: "",
        search: "",
      },
      channelPayload: null,
      channelLoading: false,
      channelFilters: {
        period_key: "ytd",
        channel: "",
        brand: "",
        category: "",
        search: "",
      },
      channelModalRow: null,
      coveragePayload: null,
      coverageLoading: false,
      coverageFilters: {
        period_key: "ytd",
        channel: "",
        brand: "",
        category: "",
        search: "",
      },
      selectedPortfolioUnit: "",
      portfolioExpanded: {},
    });
    onWillStart(async () => {
      await Promise.all([
        this.loadCommercialPayload(),
        this.loadCoveragePayload(),
        this.loadChannelPayload(),
      ]);
    });
    onMounted(() => {
      window.addEventListener("resize", this._chartResizeHandler);
      if (window.ResizeObserver && this.rootElement) {
        this._resizeObserver = new window.ResizeObserver(() => this.resizeCharts());
        this._resizeObserver.observe(this.rootElement);
      }
      this.queueChartRender();
    });
    onPatched(() => {
      this.queueChartRender();
    });
    onWillUnmount(() => {
      window.removeEventListener("resize", this._chartResizeHandler);
      if (this._resizeObserver) {
        this._resizeObserver.disconnect();
      }
      if (this._chartRenderFrame) {
        cancelAnimationFrame(this._chartRenderFrame);
      }
      this._chartRenderTimeouts.forEach((timeoutId) => clearTimeout(timeoutId));
      this.disposeCharts();
    });
  }

  async setActiveHub(hubKey) {
    this.state.activeHub = hubKey;
    if (hubKey === "commercial") {
      await Promise.all([
        this.loadCommercialPayload(),
        this.loadChannelPayload(),
        this.loadCoveragePayload(),
      ]);
      this.queueChartRender();
    }
  }

  async setCommercialTab(tabKey) {
    this.state.commercialTab = tabKey;
    if (tabKey === "overview" || tabKey === "portafolio") {
      await this.loadCommercialPayload(true);
    }
    if (tabKey === "canal") {
      await this.loadChannelPayload(true);
    }
    if (tabKey === "cobertura") {
      await this.loadCoveragePayload(true);
    }
    this.queueChartRender();
  }

  getCurrentCommercialFilters() {
    return this.state.commercialTab === "portafolio"
      ? this.state.portfolioFilters
      : this.state.overviewFilters;
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
        [this.getCurrentCommercialFilters()]
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
        [this.state.coverageFilters]
      );
    } finally {
      this.state.coverageLoading = false;
    }
  }

  async loadChannelPayload(force = false) {
    if (this.state.channelPayload && !force) {
      return;
    }
    this.state.channelLoading = true;
    try {
      this.state.channelPayload = await this.orm.call(
        "zrn_analitics.home",
        "get_channel_dashboard_data",
        [this.state.channelFilters]
      );
    } finally {
      this.state.channelLoading = false;
    }
  }

  updateChannelFilter(fieldName, value) {
    this.state.channelFilters = {
      ...this.state.channelFilters,
      [fieldName]: value,
    };
  }

  updateOverviewFilter(fieldName, value) {
    this.state.overviewFilters = {
      ...this.state.overviewFilters,
      [fieldName]: value,
    };
  }

  updatePortfolioFilter(fieldName, value) {
    this.state.portfolioFilters = {
      ...this.state.portfolioFilters,
      [fieldName]: value,
    };
  }

  updateCoverageFilter(fieldName, value) {
    this.state.coverageFilters = {
      ...this.state.coverageFilters,
      [fieldName]: value,
    };
  }

  async applyOverviewFilters() {
    this.state.commercialPayload = null;
    await this.loadCommercialPayload(true);
  }

  async clearOverviewFilters() {
    this.state.overviewFilters = { period_key: "ytd", channel: "", brand: "", category: "", search: "" };
    this.state.commercialPayload = null;
    await this.loadCommercialPayload(true);
  }

  async applyPortfolioFilters() {
    this.state.commercialPayload = null;
    await this.loadCommercialPayload(true);
  }

  async clearPortfolioFilters() {
    this.state.portfolioFilters = { period_key: "ytd", channel: "", brand: "", category: "", search: "" };
    this.state.commercialPayload = null;
    await this.loadCommercialPayload(true);
  }

  async applyCoverageFilters() {
    this.state.coveragePayload = null;
    await this.loadCoveragePayload(true);
  }

  async clearCoverageFilters() {
    this.state.coverageFilters = { period_key: "ytd", channel: "", brand: "", category: "", search: "" };
    this.state.coveragePayload = null;
    await this.loadCoveragePayload(true);
  }

  onOverviewSearchKeydown(ev) {
    if (ev.key === "Enter") {
      ev.preventDefault();
      this.applyOverviewFilters();
    }
  }

  onPortfolioSearchKeydown(ev) {
    if (ev.key === "Enter") {
      ev.preventDefault();
      this.applyPortfolioFilters();
    }
  }

  onCoverageSearchKeydown(ev) {
    if (ev.key === "Enter") {
      ev.preventDefault();
      this.applyCoverageFilters();
    }
  }

  async applyChannelFilters() {
    this.state.channelModalRow = null;
    this.state.channelPayload = null;
    await this.loadChannelPayload(true);
  }

  async clearChannelFilters() {
    this.state.channelFilters = {
      period_key: "ytd",
      channel: "",
      brand: "",
      category: "",
      search: "",
    };
    this.state.channelModalRow = null;
    this.state.channelPayload = null;
    await this.loadChannelPayload(true);
  }

  onChannelSearchKeydown(ev) {
    if (ev.key === "Enter") {
      ev.preventDefault();
      this.applyChannelFilters();
    }
  }

  openChannelModal(row) {
    this.state.channelModalRow = row;
  }

  closeChannelModal() {
    this.state.channelModalRow = null;
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
      portfolio_rows: [],
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
      summary: {
        sync_label: "",
        period_label: "",
        currency_symbol: "$",
      },
      active_filters: {
        period_key: "ytd",
        channel: "",
        brand: "",
        category: "",
        search: "",
      },
      filter_options: {
        periods: [],
        channels: [],
        brands: [],
        categories: [],
      },
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

  get channelPayload() {
    return this.state.channelPayload || {
      summary: {
        sync_label: "",
        period_label: "",
        currency_symbol: "$",
      },
      active_filters: {
        period_key: "ytd",
        channel: "",
        brand: "",
        category: "",
        search: "",
      },
      filter_options: {
        periods: [],
        channels: [],
        brands: [],
        categories: [],
      },
      summary_cards: [],
      rows: [],
      empty_message: "",
    };
  }

  get activeHubSummary() {
    if (this.state.commercialTab === "cobertura") {
      return this.coveragePayload.summary;
    }
    if (this.state.commercialTab === "canal") {
      return this.channelPayload.summary;
    }
    return this.commercialPayload.summary;
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

  get hasChannelRows() {
    return Boolean((this.channelPayload.rows || []).length);
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
    const brandRows = this.commercialPayload.portfolio_rows || [];
    const currencySymbol = this.commercialPayload.summary?.currency_symbol || "$";
    const palette = ["#bd1730", "#f18f01", "#1f4e8c", "#2f855a", "#6b7280", "#0f766e"];
    if (!brandRows.length) {
      return {
        hasBrands: false,
        hasRevenue: false,
        currencySymbol,
        totalRevenue: 0,
        units: [],
        drillRows: [],
      };
    }
    const totalRevenue = brandRows.reduce((sum, brand) => sum + Number(brand.revenue || 0), 0);
    const units = brandRows.map((brand, index) => ({
      key: brand.key || `brand_${index + 1}`,
      name: brand.name,
      color: palette[index % palette.length],
      brands: (brand.categories || []).map((category, categoryIndex) => ({
        key: category.key || `${brand.key}_category_${categoryIndex + 1}`,
        name: category.name,
        revenue: Number(category.revenue || 0),
        lines: [{
          key: `${category.key || `${brand.key}_category_${categoryIndex + 1}`}_skus`,
          name: "SKUs",
          revenue: Number(category.revenue || 0),
          mix_percentage: totalRevenue ? (Number(category.revenue || 0) / totalRevenue) * 100 : 0,
          units_sold: Number(category.quantity_sold || 0),
          billed_lines: 0,
          sku_count: Number(category.product_count || 0),
          margin_amount: 0,
          margin_pct: 0,
          skus: (category.products || []).map((product, productIndex) => ({
            key: product.key || `${category.key}_sku_${productIndex + 1}`,
            name: product.name,
            revenue: Number(product.revenue || 0),
            mix_percentage: totalRevenue ? (Number(product.revenue || 0) / totalRevenue) * 100 : 0,
            units_sold: Number(product.quantity_sold || 0),
          })),
        }],
        billed_lines: 0,
        sku_count: Number(category.product_count || 0),
        margin_amount: 0,
        margin_pct: 0,
      })),
      revenue: Number(brand.revenue || 0),
      mix_percentage: totalRevenue ? (Number(brand.revenue || 0) / totalRevenue) * 100 : 0,
      sku_count: Number(brand.product_count || 0),
      brand_count: (brand.categories || []).length,
      billed_lines: 0,
      margin_amount: 0,
      margin_pct: 0,
    }));

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

  getSelectChoices(options, emptyLabel) {
    return [{ value: "", label: emptyLabel }, ...(options || []).map((option) => ({ value: option, label: option }))];
  }

  getPeriodChoices(options) {
    return options || [];
  }

  queueChartRender() {
    if (this._chartRenderFrame) {
      cancelAnimationFrame(this._chartRenderFrame);
    }
    this._chartRenderTimeouts.forEach((timeoutId) => clearTimeout(timeoutId));
    this._chartRenderTimeouts = [];
    const renderAndResize = () => {
      this.renderCharts();
      this.resizeCharts();
    };
    this._chartRenderFrame = requestAnimationFrame(() => {
      this._chartRenderFrame = 0;
      renderAndResize();
      this._chartRenderTimeouts.push(setTimeout(() => renderAndResize(), 80));
      this._chartRenderTimeouts.push(setTimeout(() => renderAndResize(), 220));
      this._chartRenderTimeouts.push(setTimeout(() => renderAndResize(), 480));
    });
  }

  renderCharts() {
    if (!window.echarts || !this.rootElement || this.state.activeHub !== "commercial") {
      return;
    }
    if (this.state.commercialTab === "overview") {
      try {
        this.renderOverviewLineChart();
      } catch (error) {
        console.error("ZRN overview line chart error", error);
      }
      try {
        this.renderOverviewDonutChart();
      } catch (error) {
        console.error("ZRN overview donut chart error", error);
      }
      try {
        this.renderOverviewCustomersChart();
      } catch (error) {
        console.error("ZRN overview customers chart error", error);
      }
    }
    if (this.state.commercialTab === "portafolio") {
      try {
        this.renderPortfolioUnitsChart();
      } catch (error) {
        console.error("ZRN portfolio units chart error", error);
      }
      try {
        this.renderPortfolioBrandsChart();
      } catch (error) {
        console.error("ZRN portfolio brands chart error", error);
      }
    }
    if (this.state.commercialTab === "cobertura") {
      try {
        this.renderCoverageChannelChart();
      } catch (error) {
        console.error("ZRN coverage channel chart error", error);
      }
      try {
        this.renderCoverageSkuChart();
      } catch (error) {
        console.error("ZRN coverage sku chart error", error);
      }
    }
  }

  getChart(themeKey) {
    const element = this.rootElement?.querySelector(`[data-zrn-chart="${themeKey}"]`);
    if (!element) {
      return null;
    }
    const rect = element.getBoundingClientRect();
    const parentRect = element.parentElement?.getBoundingClientRect?.() || { width: 0, height: 0 };
    const width = Math.round(rect.width || parentRect.width || 0);
    const height = Math.round(rect.height || parentRect.height || 0);
    if (width < 80 || height < 80) {
      return null;
    }
    const existing = this._charts.get(themeKey);
    if (existing && existing.getDom() === element) {
      existing.resize({ width, height });
      return existing;
    }
    if (existing) {
      existing.dispose();
    }
    const chart = window.echarts.getInstanceByDom(element) || window.echarts.init(element, null, {
      renderer: "canvas",
      width,
      height,
    });
    chart.resize({ width, height });
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

  renderPortfolioUnitsChart() {
    if (this.state.commercialTab !== "portafolio") {
      return;
    }
    const units = this.commercialPortfolio.units || [];
    if (!units.length || !this.commercialPortfolio.hasRevenue) {
      return;
    }
    const chart = this.getChart("portfolio-units");
    if (!chart) {
      return;
    }
    const reversed = [...units].reverse();
    chart.setOption({
      animationDuration: 700,
      animationEasing: "cubicOut",
      grid: { top: 10, right: 20, bottom: 12, left: 120, containLabel: false },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (params) => {
          const item = reversed[params[0].dataIndex];
          return [
            `<strong>${item.name}</strong>`,
            `${this.commercialPortfolio.currencySymbol} ${this.formatMoney(item.revenue)}`,
            `${this.formatPercent(item.mix_percentage)} del mix`,
            `${this.formatCount(item.sku_count)} SKU`,
          ].join("<br/>");
        },
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
        axisLabel: { color: "#334155", fontSize: 11 },
      },
      series: [{
        type: "bar",
        data: reversed.map((item) => ({
          value: Number(item.revenue || 0),
          itemStyle: { color: item.color || "#bd1730", borderRadius: [0, 6, 6, 0] },
        })),
        barWidth: 18,
        emphasis: { focus: "series" },
      }],
    }, true);
  }

  renderPortfolioBrandsChart() {
    if (this.state.commercialTab !== "portafolio") {
      return;
    }
    const unit = this.activePortfolioUnit;
    const brands = unit?.brands || [];
    if (!brands.length || !this.commercialPortfolio.hasRevenue) {
      return;
    }
    const chart = this.getChart("portfolio-brands");
    if (!chart) {
      return;
    }
    const reversed = [...brands].sort((left, right) => left.revenue - right.revenue);
    chart.setOption({
      animationDuration: 700,
      animationEasing: "cubicOut",
      grid: { top: 10, right: 20, bottom: 12, left: 130, containLabel: false },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (params) => {
          const item = reversed[params[0].dataIndex];
          const share = unit?.revenue ? (item.revenue / unit.revenue) * 100 : 0;
          return [
            `<strong>${item.name}</strong>`,
            `${this.commercialPortfolio.currencySymbol} ${this.formatMoney(item.revenue)}`,
            `${this.formatPercent(share)} de la marca`,
            `${this.formatCount(item.sku_count)} SKU`,
          ].join("<br/>");
        },
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
          width: 120,
          overflow: "truncate",
        },
      },
      series: [{
        type: "bar",
        data: reversed.map((item) => Number(item.revenue || 0)),
        barWidth: 18,
        itemStyle: { color: "#bd1730", borderRadius: [0, 6, 6, 0] },
        emphasis: { focus: "series" },
      }],
    }, true);
  }

  renderCoverageChannelChart() {
    if (this.state.commercialTab !== "cobertura") {
      return;
    }
    const rows = this.coveragePayload.coverage_by_channel || [];
    if (!rows.length) {
      return;
    }
    const chart = this.getChart("coverage-channel");
    if (!chart) {
      return;
    }
    const reversed = [...rows].sort((left, right) => left.coverage_pct - right.coverage_pct);
    chart.setOption({
      animationDuration: 700,
      animationEasing: "cubicOut",
      grid: { top: 10, right: 18, bottom: 12, left: 110, containLabel: false },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (params) => {
          const item = reversed[params[0].dataIndex];
          return [
            `<strong>${item.channel}</strong>`,
            `${this.formatPercent(item.coverage_pct)} cobertura`,
            `${this.formatCount(item.active)} activos de ${this.formatCount(item.network_total)}`,
            `${this.commercialPayload.summary.currency_symbol} ${this.formatMoney(item.revenue)} revenue`,
          ].join("<br/>");
        },
      },
      xAxis: {
        type: "value",
        max: 100,
        splitLine: { lineStyle: { color: "#edf2f8" } },
        axisLabel: { color: "#5f6b7a", fontSize: 11, formatter: (value) => `${value}%` },
      },
      yAxis: {
        type: "category",
        data: reversed.map((item) => item.channel),
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { color: "#334155", fontSize: 11 },
      },
      series: [{
        type: "bar",
        data: reversed.map((item) => Number(item.coverage_pct || 0)),
        barWidth: 18,
        itemStyle: { color: "#bd1730", borderRadius: [0, 6, 6, 0] },
        emphasis: { focus: "series" },
        label: {
          show: true,
          position: "right",
          color: "#5f6b7a",
          fontSize: 11,
          formatter: ({ value }) => `${Number(value || 0).toFixed(0)}%`,
        },
      }],
    }, true);
  }

  renderCoverageSkuChart() {
    if (this.state.commercialTab !== "cobertura") {
      return;
    }
    const rows = [...(this.coveragePayload.sku_distribution || [])]
      .sort((left, right) => Number(right.pdv_pct || 0) - Number(left.pdv_pct || 0))
      .slice(0, 8);
    if (!rows.length) {
      return;
    }
    const chart = this.getChart("coverage-sku");
    if (!chart) {
      return;
    }
    const reversed = [...rows].reverse();
    chart.setOption({
      animationDuration: 720,
      animationEasing: "cubicOut",
      grid: { top: 10, right: 18, bottom: 12, left: 180, containLabel: false },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (params) => {
          const item = reversed[params[0].dataIndex];
          return [
            `<strong>${item.sku}</strong>`,
            `${this.formatPercent(item.pdv_pct)} penetracion`,
            `${this.formatCount(item.pdv_count)} PDVs`,
            `${this.commercialPayload.summary.currency_symbol} ${this.formatMoney(item.revenue)} revenue`,
          ].join("<br/>");
        },
      },
      xAxis: {
        type: "value",
        max: 100,
        splitLine: { lineStyle: { color: "#edf2f8" } },
        axisLabel: { color: "#5f6b7a", fontSize: 11, formatter: (value) => `${value}%` },
      },
      yAxis: {
        type: "category",
        data: reversed.map((item) => item.sku),
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: {
          color: "#334155",
          fontSize: 11,
          width: 170,
          overflow: "truncate",
        },
      },
      series: [{
        type: "bar",
        data: reversed.map((item) => Number(item.pdv_pct || 0)),
        barWidth: 18,
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: new window.echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: "#e34c62" },
            { offset: 1, color: "#bd1730" },
          ]),
        },
        emphasis: { focus: "series" },
        label: {
          show: true,
          position: "right",
          color: "#5f6b7a",
          fontSize: 11,
          formatter: ({ value }) => `${Number(value || 0).toFixed(0)}%`,
        },
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

  get rootElement() {
    return this.rootRef?.el instanceof Element ? this.rootRef.el : null;
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

  formatChannelCardValue(card) {
    if (!card) {
      return "";
    }
    if (card.type === "currency") {
      return `${this.channelPayload.summary.currency_symbol} ${this.formatMoney(card.value)}`;
    }
    return this.formatCount(card.value);
  }
}

ZrnAnalyticsHubAction.template = "zrn_analitics.HubAction";
ZrnAnalyticsHubAction.components = { SelectMenu };

registry.category("actions").add("zrn_analitics.hubs", ZrnAnalyticsHubAction);
