/** @odoo-module **/

import { TagsList } from "@web/core/tags_list/tags_list";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
  Component,
  onMounted,
  onPatched,
  onWillStart,
  onWillUnmount,
  useRef,
  useState,
} from "@odoo/owl";

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

const DEFAULT_FILTERS = Object.freeze({
  period_key: "ytd",
  channel_ids: [],
  brand_ids: [],
  category_ids: [],
  search: "",
});

function cloneDefaultFilters() {
  return {
    ...DEFAULT_FILTERS,
    channel_ids: [],
    brand_ids: [],
    category_ids: [],
  };
}

function normalizeFilterIds(values) {
  if (!Array.isArray(values)) {
    return [];
  }
  return [...new Set(
    values
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0),
  )];
}

class ZrnRelationalMultiSelect extends Component {
  setup() {
    this.orm = useService("orm");
  }

  get activeActions() {
    return {};
  }

  get tags() {
    return (this.props.records || []).map((record) => ({
      id: record.id,
      text: record.display_name,
      onDelete: () => this.removeRecord(record.id),
    }));
  }

  getDomain() {
    const baseDomain = [...(this.props.domain || [])];
    const currentIds = (this.props.records || [])
      .map((record) => record.id)
      .filter((id) => Number.isInteger(id));
    if (currentIds.length) {
      baseDomain.push(["id", "not in", currentIds]);
    }
    return baseDomain;
  }

  async resolveRecords(records) {
    const currentRecords = this.props.records || [];
    const orderedIds = [];
    const labelsById = new Map();

    [...currentRecords, ...(records || [])].forEach((record) => {
      const id = Number(record?.id);
      if (!Number.isInteger(id) || id <= 0 || orderedIds.includes(id)) {
        return;
      }
      orderedIds.push(id);
      const label =
        record.display_name || record.displayName || record.name || "";
      if (label) {
        labelsById.set(id, label);
      }
    });

    const missingIds = orderedIds.filter((id) => !labelsById.has(id));
    if (missingIds.length) {
      const nameRows = await this.orm.call(
        this.props.resModel,
        "name_get",
        [missingIds],
        { context: this.props.context || {} },
      );
      nameRows.forEach(([id, label]) => {
        labelsById.set(id, label || "");
      });
    }

    return orderedIds.map((id) => ({
      id,
      display_name: labelsById.get(id) || String(id),
    }));
  }

  async addRecords(records) {
    if (!records || !records.length) {
      return;
    }
    const nextRecords = await this.resolveRecords(records);
    this.props.onChange(nextRecords);
  }

  removeRecord(recordId) {
    const nextRecords = (this.props.records || []).filter(
      (record) => record.id !== recordId,
    );
    this.props.onChange(nextRecords);
  }
}
ZrnRelationalMultiSelect.template = "zrn_analitics.RelationalMultiSelect";
ZrnRelationalMultiSelect.components = {
  Many2XAutocomplete,
  TagsList,
};
ZrnRelationalMultiSelect.props = {
  records: { type: Array, optional: true },
  domain: { type: Array, optional: true },
  resModel: String,
  fieldString: String,
  placeholder: { type: String, optional: true },
  context: { type: Object, optional: true },
  onChange: Function,
};
ZrnRelationalMultiSelect.defaultProps = {
  records: [],
  domain: [],
  placeholder: "",
  context: {},
};

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
      coveragePayload: null,
      coverageLoading: false,
      channelPayload: null,
      channelLoading: false,
      selectedPortfolioUnit: "",
      portfolioExpanded: {},
      overviewFilters: cloneDefaultFilters(),
      portfolioFilters: cloneDefaultFilters(),
      coverageFilters: cloneDefaultFilters(),
      channelFilters: cloneDefaultFilters(),
      channelModalRow: null,
      analyticsDetailModal: null,
      sellinChain: "walmart",
      rfmFilterSegment: "",
      rfmFilterAbc: "",
      rfmFilterSearch: "",
      bcgFilter: "all",
      productChartType: "bar",
      sorts: {
        top_products: { column: "sales_amount", order: "desc" },
        coverage_by_channel: { column: "revenue", order: "desc" },
        sku_distribution: { column: "revenue", order: "desc" },
        portfolio_holes: { column: "gap_count", order: "desc" },
        clients_at_risk: { column: "days_since_last", order: "desc" },
        all_clients: { column: "rev", order: "desc" },
        rfm_clients: { column: "rev", order: "desc" },
        market_basket: { column: "lift", order: "desc" },
        cadence: { column: "rev", order: "desc" },
        ltv_forecast: { column: "forecast_total_3m", order: "desc" },
        all_products: { column: "rev", order: "desc" },
        growers: { column: "trend", order: "desc" },
        decliners: { column: "trend", order: "asc" },
        bcg_skus: { column: "r", order: "desc" },
        sellin_pdv: { column: "sellin_q", order: "desc" },
        sellin_sku: { column: "sellin_q", order: "desc" },
      },
    });
    onWillStart(async () => {
      await Promise.all([
        this.loadCommercialPayload(),
        this.loadCoveragePayload(),
      ]);
    });
    onMounted(() => {
      window.addEventListener("resize", this._chartResizeHandler);
      if (window.ResizeObserver && this.rootElement) {
        this._resizeObserver = new window.ResizeObserver(() =>
          this.resizeCharts(),
        );
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

  toggleSort(tableName, columnName) {
    const sort = this.state.sorts[tableName];
    if (!sort) {
      return;
    }
    if (sort.column === columnName) {
      sort.order = sort.order === "asc" ? "desc" : "asc";
    } else {
      sort.column = columnName;
      sort.order = "desc";
    }
  }

  sortData(list, col, order) {
    const sorted = [...(list || [])];
    sorted.sort((a, b) => {
      let valA = a?.[col];
      let valB = b?.[col];

      if (valA === undefined || valA === null) {
        valA = "";
      }
      if (valB === undefined || valB === null) {
        valB = "";
      }

      if (typeof valA === "string" || typeof valB === "string") {
        const strA = String(valA);
        const strB = String(valB);
        return order === "asc"
          ? strA.localeCompare(strB)
          : strB.localeCompare(strA);
      }
      return order === "asc" ? valA - valB : valB - valA;
    });
    return sorted;
  }

  get sortedTopProducts() {
    const sort = this.state.sorts.top_products;
    return this.sortData(this.commercialPayload.top_products || [], sort.column, sort.order);
  }

  get sortedCoverageByChannel() {
    const sort = this.state.sorts.coverage_by_channel;
    return this.sortData(this.coveragePayload.coverage_by_channel || [], sort.column, sort.order);
  }

  get sortedSkuDistribution() {
    const sort = this.state.sorts.sku_distribution;
    return this.sortData(this.coveragePayload.sku_distribution || [], sort.column, sort.order);
  }

  get sortedPortfolioHoles() {
    const sort = this.state.sorts.portfolio_holes;
    return this.sortData(
      this.coveragePayload.portfolio_holes?.rows || [],
      sort.column,
      sort.order,
    );
  }

  get sortedClientsAtRisk() {
    const sort = this.state.sorts.clients_at_risk;
    return this.sortData(this.coveragePayload.clients_at_risk || [], sort.column, sort.order);
  }

  get sortedAllClients() {
    const sort = this.state.sorts.all_clients;
    return this.sortData(this.commercialPayload?.all_clients || [], sort.column, sort.order);
  }

  get sortedRfmClients() {
    const sort = this.state.sorts.rfm_clients;
    let list = this.commercialPayload?.clients_rfm?.clients || [];
    if (this.state.rfmFilterSegment) {
      list = list.filter((c) => c.segment_key === this.state.rfmFilterSegment);
    }
    if (this.state.rfmFilterAbc) {
      list = list.filter((c) => c.abc === this.state.rfmFilterAbc);
    }
    if (this.state.rfmFilterSearch) {
      const q = this.state.rfmFilterSearch.toLowerCase();
      list = list.filter((c) => c.name.toLowerCase().includes(q));
    }
    return this.sortData(list, sort.column, sort.order);
  }

  get sortedMarketBasket() {
    const sort = this.state.sorts.market_basket;
    return this.sortData(this.commercialPayload?.market_basket?.pairs || [], sort.column, sort.order);
  }

  get sortedCadence() {
    const sort = this.state.sorts.cadence;
    return this.sortData(this.commercialPayload?.cadence?.clients || [], sort.column, sort.order);
  }

  get sortedLtvForecast() {
    const sort = this.state.sorts.ltv_forecast;
    return this.sortData(this.commercialPayload?.ltv_forecast?.clients || [], sort.column, sort.order);
  }

  get sortedAllProducts() {
    const sort = this.state.sorts.all_products;
    return this.sortData(this.commercialPayload?.all_products || [], sort.column, sort.order);
  }

  get sortedGrowers() {
    const sort = this.state.sorts.growers;
    return this.sortData(this.commercialPayload?.growers || [], sort.column, sort.order);
  }

  get sortedDecliners() {
    const sort = this.state.sorts.decliners;
    return this.sortData(this.commercialPayload?.decliners || [], sort.column, sort.order);
  }

  get sortedBcgSkus() {
    const sort = this.state.sorts.bcg_skus;
    let list = this.commercialPayload?.bcg_data?.skus || [];
    if (this.state.bcgFilter && this.state.bcgFilter !== "all") {
      list = list.filter((s) => s.q === this.state.bcgFilter);
    }
    return this.sortData(list, sort.column, sort.order);
  }

  get sortedSellinPdv() {
    const sort = this.state.sorts.sellin_pdv;
    const chain = this.state.sellinChain || "walmart";
    const data = this.commercialPayload?.sellin_vs_sellout?.[chain] || {};
    return this.sortData(data.by_pdv || [], sort.column, sort.order);
  }

  get sortedSellinSku() {
    const sort = this.state.sorts.sellin_sku;
    const chain = this.state.sellinChain || "walmart";
    const data = this.commercialPayload?.sellin_vs_sellout?.[chain] || {};
    return this.sortData(data.by_sku || [], sort.column, sort.order);
  }

  async setActiveHub(hubKey) {
    this.state.activeHub = hubKey;
    if (hubKey !== "commercial") {
      return;
    }
    await Promise.all([
      this.loadCommercialPayload(),
      this.loadCoveragePayload(),
    ]);
    if (this.state.commercialTab === "canal") {
      await this.loadChannelPayload();
    }
    this.queueChartRender();
  }

  async setCommercialTab(tabKey) {
    this.state.commercialTab = tabKey;
    this.state.channelModalRow = null;
    this.state.analyticsDetailModal = null;
    if (tabKey === "cobertura") {
      await this.loadCoveragePayload();
    } else if (tabKey === "canal") {
      await this.loadChannelPayload();
    } else {
      await this.loadCommercialPayload();
    }
    this.queueChartRender();
  }

  async loadCommercialPayload(force = false) {
    if (this.state.commercialPayload && !force) {
      return;
    }
    this.state.commercialLoading = true;
    try {
      const payload = await this.orm.call(
        "zrn_analitics.home",
        "get_commercial_hub_payload",
        [this.getCurrentCommercialFilters()],
      );
      this.state.commercialPayload = payload;
      this.syncCommercialFiltersFromPayload(payload);
      this.syncPortfolioStateFromPayload();
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
      const payload = await this.orm.call(
        "zrn_analitics.home",
        "get_coverage_dashboard_data",
        [this.state.coverageFilters],
      );
      this.state.coveragePayload = payload;
      this.syncCoverageFiltersFromPayload(payload);
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
      const payload = await this.orm.call(
        "zrn_analitics.home",
        "get_channel_dashboard_data",
        [this.state.channelFilters],
      );
      this.state.channelPayload = payload;
      this.syncChannelFiltersFromPayload(payload);
    } finally {
      this.state.channelLoading = false;
    }
  }

  getCurrentCommercialFilters() {
    if (this.state.commercialTab === "portafolio") {
      return this.state.portfolioFilters;
    }
    return this.state.overviewFilters;
  }

  syncCommercialFiltersFromPayload(payload) {
    const activeFilters = payload?.active_filters || {};
    const nextFilters = {
      period_key: activeFilters.period_key || DEFAULT_FILTERS.period_key,
      channel_ids: normalizeFilterIds(activeFilters.channel_ids),
      brand_ids: normalizeFilterIds(activeFilters.brand_ids),
      category_ids: normalizeFilterIds(activeFilters.category_ids),
      search: activeFilters.search || "",
    };
    this.state.overviewFilters = { ...nextFilters };
    this.state.portfolioFilters = { ...nextFilters };
  }

  syncCoverageFiltersFromPayload(payload) {
    const activeFilters = payload?.active_filters || {};
    this.state.coverageFilters = {
      period_key: activeFilters.period_key || DEFAULT_FILTERS.period_key,
      channel_ids: normalizeFilterIds(activeFilters.channel_ids),
      brand_ids: normalizeFilterIds(activeFilters.brand_ids),
      category_ids: normalizeFilterIds(activeFilters.category_ids),
      search: activeFilters.search || "",
    };
  }

  syncChannelFiltersFromPayload(payload) {
    const activeFilters = payload?.active_filters || {};
    this.state.channelFilters = {
      period_key: activeFilters.period_key || DEFAULT_FILTERS.period_key,
      channel_ids: normalizeFilterIds(activeFilters.channel_ids),
      brand_ids: normalizeFilterIds(activeFilters.brand_ids),
      category_ids: normalizeFilterIds(activeFilters.category_ids),
      search: activeFilters.search || "",
    };
  }

  syncPortfolioStateFromPayload() {
    const units = this.commercialPortfolio.units || [];
    const defaultUnit = units[0]?.key || "";
    this.state.selectedPortfolioUnit =
      units.find((unit) => unit.key === this.state.selectedPortfolioUnit)?.key ||
      defaultUnit;
    if (defaultUnit && this.state.portfolioExpanded[defaultUnit] === undefined) {
      this.state.portfolioExpanded = {
        ...this.state.portfolioExpanded,
        [defaultUnit]: true,
      };
    }
  }

  updateOverviewFilter(key, value) {
    console.log("[ZRN DEBUG] updateOverviewFilter", key, value);
    this.state.overviewFilters = {
      ...this.state.overviewFilters,
      [key]:
        key === "channel_ids" || key === "brand_ids" || key === "category_ids"
          ? normalizeFilterIds(value)
          : value ?? "",
    };
    console.log("[ZRN DEBUG] overviewFilters now:", JSON.stringify(this.state.overviewFilters));
  }

  updatePortfolioFilter(key, value) {
    this.state.portfolioFilters = {
      ...this.state.portfolioFilters,
      [key]:
        key === "channel_ids" || key === "brand_ids" || key === "category_ids"
          ? normalizeFilterIds(value)
          : value ?? "",
    };
  }

  updateCoverageFilter(key, value) {
    this.state.coverageFilters = {
      ...this.state.coverageFilters,
      [key]:
        key === "channel_ids" || key === "brand_ids" || key === "category_ids"
          ? normalizeFilterIds(value)
          : value ?? "",
    };
  }

  updateChannelFilter(key, value) {
    this.state.channelFilters = {
      ...this.state.channelFilters,
      [key]:
        key === "channel_ids" || key === "brand_ids" || key === "category_ids"
          ? normalizeFilterIds(value)
          : value ?? "",
    };
  }

  onOverviewPeriodSelect(value) {
    console.log("[ZRN DEBUG] onOverviewPeriodSelect called with:", value);
    this.updateOverviewFilter("period_key", value);
  }

  onOverviewBrandsChange(records) {
    this.updateOverviewFilter("brand_ids", records.map((r) => r.id));
  }

  onOverviewCategoriesChange(records) {
    this.updateOverviewFilter("category_ids", records.map((r) => r.id));
  }

  onOverviewChannelsChange(records) {
    this.updateOverviewFilter("channel_ids", records.map((r) => r.id));
  }

  onPortfolioPeriodSelect(value) {
    this.updatePortfolioFilter("period_key", value);
  }

  onPortfolioBrandsChange(records) {
    this.updatePortfolioFilter("brand_ids", records.map((r) => r.id));
  }

  onPortfolioCategoriesChange(records) {
    this.updatePortfolioFilter("category_ids", records.map((r) => r.id));
  }

  onPortfolioChannelsChange(records) {
    this.updatePortfolioFilter("channel_ids", records.map((r) => r.id));
  }

  onCoveragePeriodSelect(value) {
    this.updateCoverageFilter("period_key", value);
  }

  onCoverageChannelsChange(records) {
    this.updateCoverageFilter("channel_ids", records.map((r) => r.id));
  }

  onCoverageBrandsChange(records) {
    this.updateCoverageFilter("brand_ids", records.map((r) => r.id));
  }

  onCoverageCategoriesChange(records) {
    this.updateCoverageFilter("category_ids", records.map((r) => r.id));
  }

  onChannelPeriodSelect(value) {
    this.updateChannelFilter("period_key", value);
  }

  onChannelChannelsChange(records) {
    this.updateChannelFilter("channel_ids", records.map((r) => r.id));
  }

  onChannelBrandsChange(records) {
    this.updateChannelFilter("brand_ids", records.map((r) => r.id));
  }

  onChannelCategoriesChange(records) {
    this.updateChannelFilter("category_ids", records.map((r) => r.id));
  }

  getOptionDomain(options) {
    const ids = (options || [])
      .map((option) => Number(option.id))
      .filter((id) => Number.isInteger(id));
    return ids.length ? [["id", "in", ids]] : [["id", "=", 0]];
  }

  getSelectedOptionRecords(options, selectedIds) {
    const selectedSet = new Set(normalizeFilterIds(selectedIds));
    return (options || [])
      .filter((option) => selectedSet.has(Number(option.id)))
      .map((option) => ({
        id: Number(option.id),
        display_name: option.name,
      }));
  }

  async applyOverviewFilters() {
    await this.loadCommercialPayload(true);
  }

  async applyPortfolioFilters() {
    await this.loadCommercialPayload(true);
  }

  async applyCoverageFilters() {
    await this.loadCoveragePayload(true);
  }

  async applyChannelFilters() {
    await this.loadChannelPayload(true);
  }

  async clearOverviewFilters() {
    this.state.overviewFilters = cloneDefaultFilters();
    await this.loadCommercialPayload(true);
  }

  async clearPortfolioFilters() {
    this.state.portfolioFilters = cloneDefaultFilters();
    await this.loadCommercialPayload(true);
  }

  async clearCoverageFilters() {
    this.state.coverageFilters = cloneDefaultFilters();
    await this.loadCoveragePayload(true);
  }

  async clearChannelFilters() {
    this.state.channelFilters = cloneDefaultFilters();
    await this.loadChannelPayload(true);
  }

  onOverviewSearchKeydown(ev) {
    if (ev.key === "Enter") {
      this.applyOverviewFilters();
    }
  }

  onPortfolioSearchKeydown(ev) {
    if (ev.key === "Enter") {
      this.applyPortfolioFilters();
    }
  }

  onCoverageSearchKeydown(ev) {
    if (ev.key === "Enter") {
      this.applyCoverageFilters();
    }
  }

  onChannelSearchKeydown(ev) {
    if (ev.key === "Enter") {
      this.applyChannelFilters();
    }
  }

  openRecordModal(model, resId) {
    if (!resId) {
      return;
    }
    this.actionService.doAction({
      type: "ir.actions.act_window",
      res_model: model,
      res_id: resId,
      views: [[false, "form"]],
      target: "new",
      context: {},
    });
  }

  openAnalyticsDetailModal(detail) {
    if (!detail) {
      return;
    }
    this.state.analyticsDetailModal = detail;
  }

  openCustomerDetailById(partnerId) {
    if (!partnerId) {
      return;
    }
    const client = this.commercialPayload?.all_clients?.find(c => c.id === partnerId);
    if (client && client.detail) {
      this.openAnalyticsDetailModal(client.detail);
    } else {
      this.openRecordModal("res.partner", partnerId);
    }
  }

  closeAnalyticsDetailModal() {
    this.state.analyticsDetailModal = null;
  }

  formatDetailCard(detail, card) {
    if (!card) {
      return "";
    }
    if (card.format === "money") {
      return `${detail.currency_symbol || "$"} ${this.formatMoney(card.value)}`;
    }
    if (card.format === "text") {
      return String(card.value || "");
    }
    return this.formatCount(card.value);
  }

  onPortfolioRowClick(row) {
    if (row.level === "brand" || row.level === "line" || row.level === "sku") {
      this.openAnalyticsDetailModal(row.detail);
    }
  }

  openChannelModal(row) {
    this.state.channelModalRow = row;
  }

  closeChannelModal() {
    this.state.channelModalRow = null;
  }

  openHome() {
    return this.actionService.doAction(
      "zrn_analitics.action_zrn_analitics_home",
    );
  }

  get activeHub() {
    return (
      this.hubs.find((hub) => hub.key === this.state.activeHub) || this.hubs[0]
    );
  }

  get activeCommercialTab() {
    return (
      this.commercialTabs.find((tab) => tab.key === this.state.commercialTab) ||
      this.commercialTabs[0]
    );
  }

  get activeHubSummary() {
    if (this.state.commercialTab === "cobertura") {
      return this.coveragePayload.summary || {};
    }
    if (this.state.commercialTab === "canal") {
      return this.channelPayload.summary || {};
    }
    return this.commercialPayload.summary || {};
  }

  get commercialPayload() {
    return (
      this.state.commercialPayload || {
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
        active_filters: cloneDefaultFilters(),
        filter_options: {
          periods: [],
          channels: [],
          brands: [],
          categories: [],
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
      }
    );
  }

  get coveragePayload() {
    return (
      this.state.coveragePayload || {
        summary: {
          sync_label: "",
          period_label: "",
          currency_symbol: "$",
        },
        active_filters: cloneDefaultFilters(),
        filter_options: {
          periods: [],
          channels: [],
          brands: [],
          categories: [],
        },
        summary_cards: [],
        coverage_by_channel: [],
        pdv_universe: { total: 0, channel_rows: [], municipio_rows: [] },
        channel_brand_matrix: { brands: [], rows: [] },
        sku_distribution: [],
        portfolio_holes: { core_skus: [], rows: [] },
        clients_at_risk: [],
        notes_sources: [],
      }
    );
  }

  get channelPayload() {
    return (
      this.state.channelPayload || {
        summary: {
          sync_label: "",
          period_label: "",
          currency_symbol: "$",
        },
        active_filters: cloneDefaultFilters(),
        filter_options: {
          periods: [],
          channels: [],
          brands: [],
          categories: [],
        },
        summary_cards: [],
        rows: [],
        empty_message: "",
      }
    );
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
      (row.cells || []).forEach((cell) =>
        values.push(Number(cell.revenue || 0)),
      );
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
    const rows = this.commercialPayload.portfolio_rows || [];
    const currencySymbol = this.commercialPayload.summary?.currency_symbol || "$";
    const brandCatalog = new Map(
      (this.commercialPayload.brand_catalog || []).map((brand) => [
        brand.name,
        brand.id,
      ]),
    );
    if (!rows.length) {
      return {
        hasBrands: false,
        hasRevenue: false,
        currencySymbol,
        totalRevenue: 0,
        units: [],
        drillRows: [],
      };
    }

    const totalRevenue = rows.reduce(
      (sum, row) => sum + Number(row.revenue || 0),
      0,
    );
    const brands = rows.map((brand) => {
      const categories = (brand.categories || []).map((category) => {
        const products = (category.products || []).map((product) => ({
          key: product.key,
          resId: this.extractNumericKey(product.key),
          name: product.name,
          revenue: Number(product.revenue || 0),
          mix_percentage: totalRevenue
            ? (Number(product.revenue || 0) / totalRevenue) * 100
            : 0,
          units_sold: Number(product.quantity_sold || 0),
          detail: product.detail || null,
        }));
        return {
          key: category.key,
          name: category.name,
          revenue: Number(category.revenue || 0),
          mix_percentage: totalRevenue
            ? (Number(category.revenue || 0) / totalRevenue) * 100
            : 0,
          units_sold: Number(category.quantity_sold || 0),
          billed_lines: 0,
          sku_count: Number(category.product_count || 0),
          margin_amount: 0,
          margin_pct: 0,
          skus: products,
          detail: category.detail || null,
        };
      });
      return {
        key: brand.key,
        resId: brandCatalog.get(brand.name) || false,
        name: brand.name,
        revenue: Number(brand.revenue || 0),
        mix_percentage: totalRevenue
          ? (Number(brand.revenue || 0) / totalRevenue) * 100
          : 0,
        units_sold: Number(brand.quantity_sold || 0),
        billed_lines: 0,
        sku_count: Number(brand.product_count || 0),
        margin_amount: 0,
        margin_pct: 0,
        lines: categories,
        detail: brand.detail || null,
      };
    });

    const unit = {
      key: "portfolio_general",
      name: "Portafolio Comercial",
      color: "#1f4e8c",
      brands,
      revenue: totalRevenue,
      mix_percentage: totalRevenue ? 100 : 0,
      sku_count: brands.reduce((sum, brand) => sum + Number(brand.sku_count || 0), 0),
      brand_count: brands.length,
      billed_lines: 0,
      margin_amount: 0,
      margin_pct: 0,
    };

    const drillRows = [
      {
        key: unit.key,
        ancestor_keys: [],
        level: "unit",
        label: unit.name,
        revenue: unit.revenue,
        mix_percentage: unit.mix_percentage,
        units_sold: 0,
        billed_lines: unit.billed_lines,
        sku_count: unit.sku_count,
        margin_amount: 0,
        margin_pct: 0,
        color: unit.color,
        detail: null,
      },
    ];

    brands.forEach((brand) => {
      drillRows.push({
        key: brand.key,
        resId: brand.resId,
        ancestor_keys: [unit.key],
        level: "brand",
        label: brand.name,
        revenue: brand.revenue,
        mix_percentage: brand.mix_percentage,
        units_sold: brand.units_sold,
        billed_lines: 0,
        sku_count: brand.sku_count,
        margin_amount: 0,
        margin_pct: 0,
        detail: brand.detail,
      });
      (brand.lines || []).forEach((line) => {
        drillRows.push({
          key: line.key,
          ancestor_keys: [unit.key, brand.key],
          level: "line",
          label: line.name,
          revenue: line.revenue,
          mix_percentage: line.mix_percentage,
          units_sold: line.units_sold,
          billed_lines: 0,
          sku_count: line.sku_count,
          margin_amount: 0,
          margin_pct: 0,
          detail: line.detail,
        });
        (line.skus || []).forEach((sku) => {
          drillRows.push({
            key: sku.key,
            resId: sku.resId,
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
            detail: sku.detail,
          });
        });
      });
    });

    return {
      hasBrands: true,
      hasRevenue: totalRevenue > 0,
      currencySymbol,
      totalRevenue,
      units: [unit],
      drillRows,
    };
  }

  get activePortfolioUnit() {
    const units = this.commercialPortfolio.units || [];
    if (!units.length) {
      return null;
    }
    return units.find((unit) => unit.key === this.state.selectedPortfolioUnit) || units[0];
  }

  selectPortfolioUnit(unitKey) {
    this.state.selectedPortfolioUnit = unitKey;
  }

  togglePortfolioRow(rowKey) {
    this.state.portfolioExpanded = {
      ...this.state.portfolioExpanded,
      [rowKey]: !this.isPortfolioRowExpanded(rowKey),
    };
  }

  isPortfolioRowExpanded(rowKey) {
    if (this.state.portfolioExpanded[rowKey] !== undefined) {
      return Boolean(this.state.portfolioExpanded[rowKey]);
    }
    return rowKey === this.commercialPortfolio.units?.[0]?.key;
  }

  isPortfolioRowVisible(row) {
    return (row.ancestor_keys || []).every((key) =>
      this.isPortfolioRowExpanded(key),
    );
  }

  getSelectChoices(options, emptyLabel) {
    const choices = [{ value: "", label: emptyLabel }];
    (options || []).forEach((option) => {
      choices.push({
        value: option,
        label: option,
      });
    });
    return choices;
  }

  getPeriodChoices(options) {
    // FIX: El backend en Python envía las opciones de periodo usando la estructura {'value': ..., 'label': ...}.
    // Se mapea con option.value y se mantiene fallback a option.key para compatibilidad.
    return (options || []).map((option) => ({
      value: option.value || option.key,
      label: option.label,
    }));
  }

  extractNumericKey(value) {
    const match = String(value || "").match(/(\d+)$/);
    return match ? Number(match[1]) : false;
  }

  queueChartRender() {
    if (this._chartRenderFrame) {
      cancelAnimationFrame(this._chartRenderFrame);
    }
    this._chartRenderTimeouts.forEach((timeoutId) => clearTimeout(timeoutId));
    this._chartRenderTimeouts = [];
    this._chartRenderFrame = requestAnimationFrame(() => {
      this._chartRenderFrame = 0;
      this.renderCharts();
      this.resizeCharts();
      this._chartRenderTimeouts.push(setTimeout(() => this.resizeCharts(), 80));
      this._chartRenderTimeouts.push(
        setTimeout(() => this.resizeCharts(), 220),
      );
    });
  }

  renderCharts() {
    if (
      !window.echarts ||
      !this.rootElement ||
      this.state.activeHub !== "commercial"
    ) {
      return;
    }
    try {
      this.renderOverviewLineChart();
      this.renderOverviewDonutChart();
      this.renderOverviewCustomersChart();
      this.renderPortfolioUnitsChart();
      this.renderPortfolioBrandsChart();
      this.renderCoverageChannelChart();
      this.renderCoverageSkuChart();
      this.renderRfmParetoChart();
      this.renderInsightsCadenceChart();
      this.renderSellinSelloutChart();
      this.renderProductChart();
    } catch (error) {
      console.error("ZRN commercial chart error", error);
    }
  }

  getChart(themeKey) {
    const element = this.rootElement?.querySelector(
      `[data-zrn-chart="${themeKey}"]`,
    );
    if (!element) {
      return null;
    }
    const rect = element.getBoundingClientRect();
    const parentRect = element.parentElement?.getBoundingClientRect?.() || {
      width: 0,
      height: 0,
    };
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
    const chart =
      window.echarts.getInstanceByDom(element) ||
      window.echarts.init(element, null, {
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
    chart.setOption(
      {
        animationDuration: 650,
        animationEasing: "cubicOut",
        grid: { top: 16, right: 20, bottom: 26, left: 24, containLabel: true },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "line" },
          valueFormatter: (value) =>
            `${this.commercialPayload.summary.currency_symbol} ${this.formatMoney(value)}`,
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
        series: [
          {
            type: "line",
            smooth: 0.25,
            symbol: "circle",
            symbolSize: 8,
            data: series.map((item) => Number(item.value || 0)),
            lineStyle: { color: "#bd1730", width: 3 },
            itemStyle: {
              color: "#bd1730",
              borderColor: "#ffffff",
              borderWidth: 2,
            },
            areaStyle: {
              color: new window.echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "rgba(31, 78, 140, 0.22)" },
                { offset: 1, color: "rgba(31, 78, 140, 0.04)" },
              ]),
            },
          },
        ],
      },
      true,
    );
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
    chart.setOption(
      {
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
        series: [
          {
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
          },
        ],
      },
      true,
    );
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
    chart.setOption(
      {
        animationDuration: 700,
        animationEasing: "cubicOut",
        grid: { top: 8, right: 16, bottom: 8, left: 120, containLabel: false },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          valueFormatter: (value) =>
            `${this.commercialPayload.summary.currency_symbol} ${this.formatMoney(value)}`,
        },
        xAxis: {
          type: "value",
          splitLine: { lineStyle: { color: "#edf2f8" } },
          axisLabel: {
            color: "#5f6b7a",
            fontSize: 11,
            formatter: (value) => this.formatMoney(value),
          },
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
        series: [
          {
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
          },
        ],
      },
      true,
    );
  }

  renderPortfolioUnitsChart() {
    if (this.state.commercialTab !== "portafolio") {
      return;
    }
    const units = this.commercialPortfolio.units || [];
    if (!units.length) {
      return;
    }
    const chart = this.getChart("portfolio-units");
    if (!chart) {
      return;
    }
    chart.setOption(
      {
        animationDuration: 650,
        grid: { top: 18, right: 20, bottom: 30, left: 24, containLabel: true },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          valueFormatter: (value) =>
            `${this.commercialPortfolio.currencySymbol} ${this.formatMoney(value)}`,
        },
        xAxis: {
          type: "category",
          data: units.map((unit) => unit.name),
          axisTick: { show: false },
          axisLine: { lineStyle: { color: "#d6deea" } },
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
        series: [
          {
            type: "bar",
            data: units.map((unit) => Number(unit.revenue || 0)),
            barMaxWidth: 56,
            itemStyle: { color: "#1f4e8c", borderRadius: [6, 6, 0, 0] },
          },
        ],
      },
      true,
    );
  }

  renderPortfolioBrandsChart() {
    if (this.state.commercialTab !== "portafolio") {
      return;
    }
    const brands = this.activePortfolioUnit?.brands || [];
    if (!brands.length) {
      return;
    }
    const chart = this.getChart("portfolio-brands");
    if (!chart) {
      return;
    }
    const reversed = [...brands].reverse();
    chart.setOption(
      {
        animationDuration: 650,
        grid: { top: 8, right: 16, bottom: 8, left: 140, containLabel: false },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          valueFormatter: (value) =>
            `${this.commercialPortfolio.currencySymbol} ${this.formatMoney(value)}`,
        },
        xAxis: {
          type: "value",
          splitLine: { lineStyle: { color: "#edf2f8" } },
          axisLabel: {
            color: "#5f6b7a",
            fontSize: 11,
            formatter: (value) => this.formatMoney(value),
          },
        },
        yAxis: {
          type: "category",
          data: reversed.map((brand) => brand.name),
          axisTick: { show: false },
          axisLine: { show: false },
          axisLabel: {
            color: "#334155",
            fontSize: 11,
            width: 130,
            overflow: "truncate",
          },
        },
        series: [
          {
            type: "bar",
            data: reversed.map((brand) => Number(brand.revenue || 0)),
            barWidth: 18,
            itemStyle: { color: "#bd1730", borderRadius: [0, 6, 6, 0] },
          },
        ],
      },
      true,
    );
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
    chart.setOption(
      {
        animationDuration: 650,
        grid: { top: 18, right: 20, bottom: 30, left: 24, containLabel: true },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
        },
        legend: {
          data: ["Activos", "Red total"],
          textStyle: { color: "#5f6b7a", fontSize: 11 },
        },
        xAxis: {
          type: "category",
          data: rows.map((row) => row.channel),
          axisTick: { show: false },
          axisLine: { lineStyle: { color: "#d6deea" } },
          axisLabel: { color: "#5f6b7a", fontSize: 11 },
        },
        yAxis: {
          type: "value",
          splitLine: { lineStyle: { color: "#edf2f8" } },
          axisLabel: { color: "#5f6b7a", fontSize: 11 },
        },
        series: [
          {
            name: "Activos",
            type: "bar",
            data: rows.map((row) => Number(row.active || 0)),
            itemStyle: { color: "#1f4e8c", borderRadius: [6, 6, 0, 0] },
          },
          {
            name: "Red total",
            type: "bar",
            data: rows.map((row) => Number(row.network_total || 0)),
            itemStyle: { color: "#a9c7eb", borderRadius: [6, 6, 0, 0] },
          },
        ],
      },
      true,
    );
  }

  renderCoverageSkuChart() {
    if (this.state.commercialTab !== "cobertura") {
      return;
    }
    const rows = (this.coveragePayload.sku_distribution || []).slice(0, 8);
    if (!rows.length) {
      return;
    }
    const chart = this.getChart("coverage-sku");
    if (!chart) {
      return;
    }
    const reversed = [...rows].reverse();
    chart.setOption(
      {
        animationDuration: 650,
        grid: { top: 8, right: 16, bottom: 8, left: 180, containLabel: false },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          valueFormatter: (value) => `${Number(value || 0).toFixed(1)}%`,
        },
        xAxis: {
          type: "value",
          max: 100,
          splitLine: { lineStyle: { color: "#edf2f8" } },
          axisLabel: {
            color: "#5f6b7a",
            fontSize: 11,
            formatter: (value) => `${value}%`,
          },
        },
        yAxis: {
          type: "category",
          data: reversed.map((row) => row.sku),
          axisTick: { show: false },
          axisLine: { show: false },
          axisLabel: {
            color: "#334155",
            fontSize: 11,
            width: 170,
            overflow: "truncate",
          },
        },
        series: [
          {
            type: "bar",
            data: reversed.map((row) => Number(row.pdv_pct || 0)),
            barWidth: 18,
            itemStyle: { color: "#bd1730", borderRadius: [0, 6, 6, 0] },
          },
        ],
      },
      true,
    );
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
    if (card?.type === "currency") {
      return `${this.channelPayload.summary.currency_symbol} ${this.formatMoney(card.value)}`;
    }
    return this.formatCount(card?.value);
  }

  onRfmFilterSegmentSelect(ev) {
    this.state.rfmFilterSegment = ev.target.value;
  }

  onRfmFilterAbcSelect(ev) {
    this.state.rfmFilterAbc = ev.target.value;
  }

  onRfmFilterSearchInput(ev) {
    this.state.rfmFilterSearch = ev.target.value;
  }

  setBcgFilter(q) {
    this.state.bcgFilter = q;
  }

  setSellinChain(chain) {
    this.state.sellinChain = chain;
    this.queueChartRender();
  }

  renderRfmParetoChart() {
    if (this.state.commercialTab !== "rfm") {
      return;
    }
    const rfm = this.commercialPayload?.clients_rfm || {};
    const pareto = rfm.pareto || [];
    if (!pareto.length) {
      return;
    }
    const chart = this.getChart("rfm-pareto");
    if (!chart) {
      return;
    }
    chart.setOption({
      animationDuration: 600,
      grid: { top: 30, right: 30, bottom: 40, left: 45, containLabel: true },
      tooltip: {
        trigger: "axis",
        formatter: (params) => {
          const idx = params[0].dataIndex;
          const pt = pareto[idx];
          return `Top ${pt.x} clientes (${pt.x_pct}%)<br/>% Rev acum: <b>${pt.cum_pct}%</b>`;
        }
      },
      xAxis: {
        type: "category",
        name: "% Clientes",
        nameLocation: "middle",
        nameGap: 24,
        data: pareto.map((p) => `${Math.round(p.x_pct)}%`),
        axisLine: { lineStyle: { color: "#d6deea" } },
        axisLabel: { color: "#5f6b7a", fontSize: 10 },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: "#edf2f8" } },
        axisLabel: { color: "#5f6b7a", formatter: "{value}%" },
      },
      series: [
        {
          type: "line",
          smooth: true,
          symbol: "none",
          data: pareto.map((p) => p.cum_pct),
          lineStyle: { color: "#22c55e", width: 2.5 },
          areaStyle: {
            color: new window.echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(34, 197, 94, 0.25)" },
              { offset: 1, color: "rgba(34, 197, 94, 0.03)" },
            ]),
          },
        }
      ]
    });
  }

  renderInsightsCadenceChart() {
    if (this.state.commercialTab !== "insights") {
      return;
    }
    const cadence = this.commercialPayload?.cadence || {};
    const segments = cadence.segments || {};
    const chart = this.getChart("insights-cadence");
    if (!chart) {
      return;
    }
    const data = [
      { value: segments.regular?.count || 0, name: "Regular" },
      { value: segments.bimensual?.count || 0, name: "Bimensual" },
      { value: segments.esporádico?.count || 0, name: "Esporádico" },
      { value: segments.único?.count || 0, name: "Único" },
    ];
    chart.setOption({
      animationDuration: 600,
      tooltip: {
        trigger: "item",
        formatter: "{b}: <b>{c} clientes</b> ({d}%)"
      },
      legend: {
        orient: "horizontal",
        bottom: 0,
        left: "center",
        textStyle: { color: "#5f6b7a", fontSize: 11 }
      },
      series: [
        {
          type: "pie",
          radius: ["40%", "70%"],
          center: ["50%", "45%"],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 6,
            borderColor: "#fff",
            borderWidth: 2
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 12,
              fontWeight: "bold"
            }
          },
          data: data,
          color: ["#16a34a", "#2563eb", "#eab308", "#64748b"]
        }
      ]
    });
  }

  renderSellinSelloutChart() {
    if (this.state.commercialTab !== "gap") {
      return;
    }
    const chain = this.state.sellinChain || "walmart";
    const data = this.commercialPayload?.sellin_vs_sellout?.[chain] || {};
    const byMonth = data.by_month || [];
    if (!byMonth.length) {
      return;
    }
    const chart = this.getChart("sellin-sellout");
    if (!chart) {
      return;
    }
    chart.setOption({
      animationDuration: 600,
      grid: { top: 35, right: 20, bottom: 25, left: 35, containLabel: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        valueFormatter: (value) =>
          `${this.commercialPayload.summary.currency_symbol} ${this.formatMoney(value)}`
      },
      legend: {
        data: ["Sell-in (Facturado)", "Sell-out (Simulado)"],
        textStyle: { color: "#5f6b7a" }
      },
      xAxis: {
        type: "category",
        data: byMonth.map((m) => m.label),
        axisLine: { lineStyle: { color: "#d6deea" } },
        axisLabel: { color: "#5f6b7a" },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#edf2f8" } },
        axisLabel: { color: "#5f6b7a", formatter: (val) => this.formatMoney(val) },
      },
      series: [
        {
          name: "Sell-in (Facturado)",
          type: "bar",
          data: byMonth.map((m) => m.sellin_q),
          color: "#2563eb",
          barMaxWidth: 24,
        },
        {
          name: "Sell-out (Simulado)",
          type: "bar",
          data: byMonth.map((m) => m.sellout_q),
          color: "#16a34a",
          barMaxWidth: 24,
        }
      ]
    });
  }

  setProductChartType(type) {
    this.state.productChartType = type;
    this.queueChartRender();
  }

  renderProductChart() {
    if (this.state.commercialTab !== "producto") {
      return;
    }
    const products = this.commercialPayload?.all_products || [];
    if (!products.length) {
      return;
    }
    const chart = this.getChart("product-chart");
    if (!chart) {
      return;
    }
    // Take top 10 products
    const top10 = products.slice(0, 10);
    const chartType = this.state.productChartType || "bar";
    const symbol = this.commercialPayload.summary?.currency_symbol || "$";

    if (chartType === "pie") {
      const pieData = top10.map((p) => ({
        name: p.name,
        value: p.rev,
      }));
      chart.setOption({
        animationDuration: 600,
        tooltip: {
          trigger: "item",
          formatter: ({ name, value, percent }) =>
            `${name}<br/>${symbol} ${this.formatMoney(value)}<br/>${percent}% del Top 10`,
        },
        legend: {
          orient: "vertical",
          right: 10,
          top: "center",
          type: "scroll",
          textStyle: { color: "#5f6b7a", fontSize: 11 },
        },
        series: [
          {
            type: "pie",
            radius: ["40%", "70%"],
            center: ["40%", "50%"],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 6, borderColor: "#ffffff", borderWidth: 2 },
            label: { show: false },
            emphasis: { scale: true, scaleSize: 6 },
            data: pieData,
            color: ["#bd1730", "#1f4e8c", "#16a34a", "#eab308", "#64748b", "#3b82f6", "#10b981", "#8b5cf6", "#f43f5e", "#f59e0b"]
          }
        ]
      }, true);
    } else {
      // Bar or Line
      const categories = top10.map((p) => p.name);
      const data = top10.map((p) => p.rev);

      chart.setOption({
        animationDuration: 600,
        grid: { top: 35, right: 30, bottom: 40, left: 55, containLabel: true },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          valueFormatter: (val) => `${symbol} ${this.formatMoney(val)}`
        },
        xAxis: {
          type: "category",
          data: categories,
          axisLine: { lineStyle: { color: "#d6deea" } },
          axisTick: { show: false },
          axisLabel: {
            color: "#5f6b7a",
            fontSize: 10,
            interval: 0,
            rotate: 20,
            width: 100,
            overflow: "truncate"
          },
        },
        yAxis: {
          type: "value",
          splitLine: { lineStyle: { color: "#edf2f8" } },
          axisLabel: {
            color: "#5f6b7a",
            fontSize: 10,
            formatter: (val) => this.formatMoney(val)
          },
        },
        series: [
          {
            name: "Revenue",
            type: chartType,
            data: data,
            barMaxWidth: 30,
            smooth: chartType === "line" ? 0.25 : false,
            symbol: chartType === "line" ? "circle" : "none",
            symbolSize: 6,
            itemStyle: {
              color: "#bd1730",
              borderRadius: chartType === "bar" ? [4, 4, 0, 0] : [0, 0, 0, 0]
            },
            areaStyle: chartType === "line" ? {
              color: new window.echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "rgba(189, 23, 48, 0.2)" },
                { offset: 1, color: "rgba(189, 23, 48, 0.02)" },
              ]),
            } : null
          }
        ]
      }, true);
    }
  }
}

ZrnAnalyticsHubAction.template = "zrn_analitics.HubAction";
ZrnAnalyticsHubAction.components = {
  Many2XAutocomplete,
  SelectMenu,
  TagsList,
  ZrnRelationalMultiSelect,
};

registry.category("actions").add("zrn_analitics.hubs", ZrnAnalyticsHubAction);
