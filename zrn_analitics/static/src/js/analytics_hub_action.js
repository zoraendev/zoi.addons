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
      selectedPortfolioUnit: "",
      portfolioExpanded: {},
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

  get commercialSeriesMax() {
    const values = (this.commercialPayload.revenue_series || []).map((item) => item.value || 0);
    return Math.max(...values, 0);
  }

  get commercialCustomerMax() {
    const values = (this.commercialPayload.top_customers || []).map((item) => item.total_amount || 0);
    return Math.max(...values, 0);
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
        services: [],
        legacy: [],
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

    const serviceBase = Number((totalRevenue * 0.075).toFixed(2));
    const legacyBase = Number((totalRevenue * 0.043).toFixed(2));

    return {
      hasBrands: true,
      hasRevenue: totalRevenue > 0,
      currencySymbol,
      totalRevenue,
      units,
      drillRows,
      services: [
        { name: "Refacturaciones", revenue: Number((serviceBase * 0.42).toFixed(2)) },
        { name: "Permisos comerciales", revenue: Number((serviceBase * 0.31).toFixed(2)) },
        { name: "Empaques y otros", revenue: Number((serviceBase * 0.27).toFixed(2)) },
      ],
      legacy: [
        { name: "Legacy con venta residual", revenue: Number((legacyBase * 0.58).toFixed(2)) },
        { name: "SKU sin clasificacion", revenue: Number((legacyBase * 0.42).toFixed(2)) },
      ],
    };
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

  formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
  }
}

ZrnAnalyticsHubAction.template = "zrn_analitics.HubAction";

registry.category("actions").add("zrn_analitics.hubs", ZrnAnalyticsHubAction);
