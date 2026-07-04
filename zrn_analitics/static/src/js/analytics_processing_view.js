/** @odoo-module **/

import {
  QUERY_RESULT_LIMIT,
  SQL_TYPES,
  READ_ONLY_SQL_PATTERN,
  FORBIDDEN_SQL_PATTERN,
  aggregateValues,
  escapeHtml,
  getColumnLabel,
  quoteSqlIdentifier,
  sanitizeIdentifier,
  toChartNumber,
} from "./analytics_processing_utils";
import {
  parseGoogleSheetSource,
  parseLocalSource,
} from "./analytics_processing_sources";
import {
  buildDatasetRecords,
  buildTableStructure,
  createSheetState,
  createTableState,
  validateTableStructure,
} from "./analytics_processing_tables";

export class ZrnAnalyticsProcessingView {
  constructor() {
    this.root = null;
    this.listenersAttached = false;
    this.boundHandleRootEvent = this.handleRootEvent.bind(this);
    this.boundBeforeUnload = this.handleBeforeUnload.bind(this);
    this.boundDocumentClick = this.handleDocumentClick.bind(this);
    this.chartInstance = null;
    this.chartRenderToken = 0;
    this.registeredTableName = "";
    this.lastRegisteredSignature = "";
    this.navigationHandlers = {};
    this.preserveStateOnUnmount = false;
    this.state = this.getInitialState();
  }

  setNavigationHandlers(handlers) {
    this.navigationHandlers = handlers || {};
  }

  openWorkspaceRoute() {
    if (this.navigationHandlers.openWorkspace) {
      return this.navigationHandlers.openWorkspace();
    }
    const trigger = document.querySelector(".zrn_processing_workspace_trigger");
    if (trigger instanceof HTMLElement) {
      trigger.click();
      return Promise.resolve();
    }
    return Promise.resolve();
  }

  preserveStateOnce() {
    this.preserveStateOnUnmount = true;
  }

  cancelPreserveState() {
    this.preserveStateOnUnmount = false;
  }

  consumePreserveState() {
    const value = this.preserveStateOnUnmount;
    this.preserveStateOnUnmount = false;
    return value;
  }

  getInitialState() {
    return {
      sourceMeta: {
        type: "",
        name: "",
        extension: "",
        sizeLabel: "",
        iconClass: "fa-database",
        totalSheets: 0,
        loaded: false,
        url: "",
      },
      sourceInput: {
        googleSheetUrl: "",
        mode: "",
      },
      datasetConfig: {
        sheets: [],
        selectedSheetId: "",
        structureReady: false,
        structureDirty: false,
        statusLabel: "Sin origen",
      },
      queryState: {
        sql: "",
        running: false,
        error: "",
        columns: [],
        rows: [],
        json: "",
        totalRows: 0,
        activeView: "table",
        tableName: "",
      },
      queryBuilder: {
        selectedColumns: [],
        filters: [],
        limit: 20,
      },
      chartState: {
        type: "bar",
        categoryColumn: "",
        valueColumn: "",
        aggregate: "sum",
        error: "",
      },
      globalError: "",
    };
  }

  mount(root) {
    if (this.root !== root) {
      this.unmount();
      this.root = root;
      this.attachListeners();
    }
    this.render();
  }

  unmount() {
    if (!this.root) {
      return;
    }
    this.detachListeners();
    this.disposeChart();
    this.root.innerHTML = "";
    this.root = null;
  }

  destroy() {
    this.unmount();
    this.dropRegisteredTable();
    this.state = this.getInitialState();
  }

  attachListeners() {
    if (!this.root || this.listenersAttached) {
      return;
    }
    this.root.addEventListener("change", this.boundHandleRootEvent);
    this.root.addEventListener("input", this.boundHandleRootEvent);
    this.root.addEventListener("click", this.boundHandleRootEvent);
    window.addEventListener("beforeunload", this.boundBeforeUnload);
    document.addEventListener("click", this.boundDocumentClick, true);
    this.listenersAttached = true;
  }

  detachListeners() {
    if (!this.listenersAttached || !this.root) {
      return;
    }
    this.root.removeEventListener("change", this.boundHandleRootEvent);
    this.root.removeEventListener("input", this.boundHandleRootEvent);
    this.root.removeEventListener("click", this.boundHandleRootEvent);
    window.removeEventListener("beforeunload", this.boundBeforeUnload);
    document.removeEventListener("click", this.boundDocumentClick, true);
    this.listenersAttached = false;
  }

  get hasTransientData() {
    return Boolean(
      this.state.sourceMeta.loaded ||
        this.state.queryState.sql.trim() ||
        this.state.queryState.rows.length ||
        this.state.datasetConfig.sheets.length,
    );
  }

  get selectedSheet() {
    return (
      this.state.datasetConfig.sheets.find(
        (sheet) => sheet.id === this.state.datasetConfig.selectedSheetId,
      ) || null
    );
  }

  get selectedTable() {
    const sheet = this.selectedSheet;
    if (!sheet) {
      return null;
    }
    return sheet.tables.find((table) => table.id === sheet.selectedTableId) || null;
  }

  get activeTableName() {
    return this.selectedTable?.tableName || "dataset";
  }

  async confirmDiscardIfNeeded() {
    if (!this.hasTransientData) {
      return true;
    }
    return window.confirm(
      "El origen temporal y el trabajo de esta sesion se perderan al salir. Deseas continuar?",
    );
  }

  handleBeforeUnload(event) {
    if (!this.hasTransientData) {
      return;
    }
    event.preventDefault();
    event.returnValue = "";
  }

  handleDocumentClick(event) {
    if (!this.root || !this.hasTransientData || !(event.target instanceof Element)) {
      return;
    }
    const target = event.target.closest("button, a");
    if (!target) {
      return;
    }
    if (target.closest("[data-zrn-processing-root='1']")) {
      if (!target.closest(".zrn_processing_leave_btn")) {
        return;
      }
    } else if (
      !target.closest(
        ".zrn_processing_leave_btn, .o_control_panel, .o_main_navbar, .o_menu_sections, .o_breadcrumb, .o_pager",
      )
    ) {
      return;
    }

    const canLeave = window.confirm(
      "El origen temporal se perdera si sales de Procesamiento. Deseas continuar?",
    );
    if (!canLeave) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
    }
  }

  handleRootEvent(event) {
    const source = event.target.closest("[data-action]");
    const action = source?.dataset.action;
    if (!action) {
      return;
    }

    if (action === "file" && event.type === "change") {
      this.handleFileSelection(source);
      return;
    }
    if (action === "source-mode" && event.type === "click") {
      event.preventDefault();
      this.state.sourceInput.mode = source.dataset.mode || "";
      this.render();
      return;
    }
    if (action === "google-sheet-url" && event.type === "input") {
      this.state.sourceInput.googleSheetUrl = source.value;
      return;
    }
    if (action === "google-sheet-connect" && event.type === "click") {
      event.preventDefault();
      this.handleGoogleSheetConnect();
      return;
    }
    if (action === "back-to-processing" && event.type === "click") {
      event.preventDefault();
      if (this.navigationHandlers.openLanding) {
        this.navigationHandlers.openLanding();
      }
      return;
    }
    if (action === "sheet-select" && event.type === "change") {
      this.selectSheet(source.value);
      return;
    }
    if (action === "table-select" && (event.type === "change" || event.type === "click")) {
      this.selectTable(source.value);
      return;
    }
    if (action === "table-add" && event.type === "click") {
      event.preventDefault();
      this.addTableDefinition();
      return;
    }
    if (action === "table-remove" && event.type === "click") {
      event.preventDefault();
      this.removeTableDefinition(source.dataset.tableId);
      return;
    }
    if (action === "table-name" && event.type === "input") {
      this.updateTableMeta("name", source.value);
      return;
    }
    if (action === "table-sql-name" && event.type === "input") {
      this.updateTableMeta("tableName", source.value);
      return;
    }
    if (action === "table-start-row" && event.type === "change") {
      this.updateTableRange("tableStartRowIndex", Number(source.value || 1) - 1);
      return;
    }
    if (action === "table-end-row" && event.type === "change") {
      this.updateTableRange("tableEndRowIndex", Number(source.value || 1) - 1);
      return;
    }
    if (action === "table-start-column" && event.type === "change") {
      this.updateTableRange("tableStartColumnIndex", Number(source.value || 0));
      return;
    }
    if (action === "table-end-column" && event.type === "change") {
      this.updateTableRange("tableEndColumnIndex", Number(source.value || 0));
      return;
    }
    if (action === "apply-structure" && event.type === "click") {
      event.preventDefault();
      this.applyStructure();
      return;
    }
    if (action === "reset-source" && event.type === "click") {
      event.preventDefault();
      this.resetAll();
      return;
    }
    if (action === "builder-column" && event.type === "change") {
      this.toggleBuilderColumn(source.value, Boolean(source.checked));
      return;
    }
    if (action === "builder-add-filter" && event.type === "click") {
      event.preventDefault();
      this.addBuilderFilter();
      return;
    }
    if (action === "builder-remove-filter" && event.type === "click") {
      event.preventDefault();
      this.removeBuilderFilter(source.dataset.filterId);
      return;
    }
    if (action === "builder-filter-column" && event.type === "change") {
      this.updateBuilderFilter(source.dataset.filterId, "column", source.value);
      return;
    }
    if (action === "builder-filter-operator" && event.type === "change") {
      this.updateBuilderFilter(source.dataset.filterId, "operator", source.value);
      return;
    }
    if (action === "builder-filter-value" && event.type === "input") {
      this.updateBuilderFilter(source.dataset.filterId, "value", source.value);
      return;
    }
    if (action === "builder-filter-value-to" && event.type === "input") {
      this.updateBuilderFilter(source.dataset.filterId, "valueTo", source.value);
      return;
    }
    if (action === "builder-limit" && event.type === "input") {
      const nextLimit = Number(source.value || 20);
      this.state.queryBuilder.limit =
        Number.isFinite(nextLimit) && nextLimit > 0 ? nextLimit : 20;
      return;
    }
    if (action === "builder-generate" && event.type === "click") {
      event.preventDefault();
      this.applyNoCodeQuery();
      return;
    }
    if (action === "builder-clear" && event.type === "click") {
      event.preventDefault();
      this.resetNoCodeQuery();
      return;
    }
    if (action === "sql-input" && event.type === "input") {
      this.state.queryState.sql = source.value;
      return;
    }
    if (action === "run-query" && event.type === "click") {
      event.preventDefault();
      this.runQuery();
      return;
    }
    if (action === "column-use" && event.type === "change") {
      this.updateColumnSetting(Number(source.dataset.columnIndex), "use", Boolean(source.checked));
      return;
    }
    if (action === "column-alias" && event.type === "input") {
      this.updateColumnSetting(Number(source.dataset.columnIndex), "alias", source.value);
      return;
    }
    if (action === "column-type" && event.type === "change") {
      this.updateColumnSetting(Number(source.dataset.columnIndex), "type", source.value);
      return;
    }
    if (action === "result-view" && event.type === "click") {
      event.preventDefault();
      this.state.queryState.activeView = source.dataset.view || "table";
      this.render();
      return;
    }
    if (action === "chart-type" && event.type === "change") {
      this.state.chartState.type = source.value;
      this.render();
      return;
    }
    if (action === "chart-category" && event.type === "change") {
      this.state.chartState.categoryColumn = source.value;
      this.render();
      return;
    }
    if (action === "chart-value" && event.type === "change") {
      this.state.chartState.valueColumn = source.value;
      this.render();
      return;
    }
    if (action === "chart-aggregate" && event.type === "change") {
      this.state.chartState.aggregate = source.value;
      this.render();
    }
  }

  async handleFileSelection(input) {
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    if (this.state.sourceMeta.loaded) {
      const shouldReplace = window.confirm(
        "Cargar un nuevo origen reemplazara el dataset temporal actual. Deseas continuar?",
      );
      if (!shouldReplace) {
        input.value = "";
        return;
      }
    }
    try {
      await this.loadParsedSource(await parseLocalSource(file));
    } catch (error) {
      this.setErrorState(error);
    } finally {
      input.value = "";
    }
  }

  async handleGoogleSheetConnect() {
    if (this.state.sourceMeta.loaded) {
      const shouldReplace = window.confirm(
        "Conectar un Google Sheet reemplazara el dataset temporal actual. Deseas continuar?",
      );
      if (!shouldReplace) {
        return;
      }
    }
    try {
      await this.loadParsedSource(
        await parseGoogleSheetSource(this.state.sourceInput.googleSheetUrl),
      );
    } catch (error) {
      this.setErrorState(error);
    }
  }

  async loadParsedSource(parsedSource) {
    this.dropRegisteredTable();
    this.disposeChart();
    const sheets = (parsedSource.sheets || []).map((sheet, index) => createSheetState(sheet, index));
    if (!sheets.length) {
      throw new Error("El origen no genero hojas utilizables.");
    }
    this.state = this.getInitialState();
    this.state.sourceMeta = {
      type: parsedSource.sourceType,
      name: parsedSource.sourceLabel,
      extension: parsedSource.sourceMeta.extension,
      sizeLabel: parsedSource.sourceMeta.sizeLabel,
      iconClass: parsedSource.sourceMeta.iconClass,
      totalSheets: parsedSource.sourceMeta.totalSheets,
      loaded: true,
      url: parsedSource.sourceMeta.url || "",
    };
    this.state.sourceInput.googleSheetUrl = parsedSource.sourceMeta.url || "";
    this.state.datasetConfig.sheets = sheets;
    this.state.datasetConfig.selectedSheetId = sheets[0].id;
    this.state.datasetConfig.statusLabel = "Origen cargado";
    this.state.queryState.tableName = sheets[0].tables[0]?.tableName || "";
    this.syncQueryStateWithTable();
    if (this.screenMode === "landing") {
      await this.openWorkspaceRoute();
      return;
    }
    this.render();
  }

  setErrorState(error) {
    this.state = this.getInitialState();
    this.state.globalError = error.message || "No se pudo cargar el origen.";
    this.render();
  }

  selectSheet(sheetId) {
    this.state.datasetConfig.selectedSheetId = sheetId;
    const sheet = this.selectedSheet;
    if (!sheet) {
      return;
    }
    if (!sheet.selectedTableId && sheet.tables[0]) {
      sheet.selectedTableId = sheet.tables[0].id;
    }
    this.refreshDatasetStatus();
    this.clearQueryResults();
    this.syncQueryStateWithTable();
    this.render();
  }

  selectTable(tableId) {
    const sheet = this.selectedSheet;
    if (!sheet) {
      return;
    }
    sheet.selectedTableId = tableId;
    this.refreshDatasetStatus();
    this.clearQueryResults();
    this.syncQueryStateWithTable(true);
    this.render();
  }

  addTableDefinition() {
    const sheet = this.selectedSheet;
    if (!sheet) {
      return;
    }
    const index = sheet.tables.length;
    const baseTable = this.selectedTable;
    const newTable = createTableState(
      sheet.rawRows,
      sheet.name,
      {
        name: `tabla_${index + 1}`,
        tableStartRowIndex: baseTable?.tableStartRowIndex || 0,
        tableEndRowIndex: baseTable?.tableEndRowIndex || Math.max(1, sheet.rawRows.length - 1),
        tableStartColumnIndex: baseTable?.tableStartColumnIndex || 0,
        tableEndColumnIndex: baseTable?.tableEndColumnIndex || 0,
      },
      index,
    );
    sheet.tables.push(newTable);
    sheet.selectedTableId = newTable.id;
    this.refreshDatasetStatus();
    this.clearQueryResults();
    this.syncQueryStateWithTable(true);
    this.render();
  }

  removeTableDefinition(tableId) {
    const sheet = this.selectedSheet;
    if (!sheet || sheet.tables.length <= 1) {
      return;
    }
    const currentTable = this.selectedTable;
    if (
      currentTable?.id === tableId &&
      !window.confirm("Se eliminara la definicion de tabla seleccionada. Deseas continuar?")
    ) {
      return;
    }
    sheet.tables = sheet.tables.filter((table) => table.id !== tableId);
    if (!sheet.tables.some((table) => table.id === sheet.selectedTableId)) {
      sheet.selectedTableId = sheet.tables[0]?.id || "";
    }
    this.refreshDatasetStatus();
    this.clearQueryResults();
    this.syncQueryStateWithTable(true);
    this.render();
  }

  updateTableMeta(key, value) {
    const table = this.selectedTable;
    if (!table) {
      return;
    }
    if (key === "tableName") {
      table.tableName = sanitizeIdentifier(value, "dataset");
    } else {
      table[key] = value;
    }
    table.errors = validateTableStructure(table, this.selectedSheet?.rawRows || []);
    table.structureDirty = true;
    table.structureApplied = false;
    this.refreshDatasetStatus();
    this.syncQueryStateWithTable();
    this.render();
  }

  updateTableRange(key, value) {
    const table = this.selectedTable;
    const rawRows = this.selectedSheet?.rawRows;
    if (!table || !rawRows) {
      return;
    }
    table[key] = value;
    if (key === "tableStartColumnIndex" && table.tableEndColumnIndex < value) {
      table.tableEndColumnIndex = value;
    }
    if (key === "tableEndColumnIndex" && value < table.tableStartColumnIndex) {
      table.tableStartColumnIndex = value;
    }
    if (key === "tableStartRowIndex" && table.tableEndRowIndex <= value) {
      table.tableEndRowIndex = Math.min(rawRows.length - 1, value + 1);
    }
    if (key === "tableEndRowIndex" && value <= table.tableStartRowIndex) {
      table.tableStartRowIndex = Math.max(0, value - 1);
    }
    buildTableStructure(table, rawRows, { keepAliases: false });
    this.refreshDatasetStatus();
    this.clearQueryResults();
    this.syncQueryStateWithTable();
    this.render();
  }

  updateColumnSetting(index, key, value) {
    const table = this.selectedTable;
    const rawRows = this.selectedSheet?.rawRows;
    if (!table || !rawRows) {
      return;
    }
    const column = table.columns[index];
    if (!column) {
      return;
    }
    column[key] = value;
    table.errors = validateTableStructure(table, rawRows);
    table.structureDirty = true;
    table.structureApplied = false;
    this.refreshDatasetStatus();
    this.syncNoCodeQueryBuilder();
    if (key !== "alias") {
      this.render();
    }
  }

  refreshDatasetStatus() {
    const table = this.selectedTable;
    const ready = Boolean(
      table && table.structureApplied && !table.structureDirty && !table.errors.length,
    );
    this.state.datasetConfig.structureReady = ready;
    this.state.datasetConfig.structureDirty = Boolean(table?.structureDirty);
    this.state.datasetConfig.statusLabel = table?.errors.length
      ? "Requiere ajustes"
      : ready
        ? "Dataset listo"
        : this.state.sourceMeta.loaded
          ? "Pendiente de aplicar"
          : "Sin origen";
  }

  buildDatasetSignature(table) {
    return JSON.stringify({
      id: table.id,
      name: table.name,
      tableName: table.tableName,
      tableStartRowIndex: table.tableStartRowIndex,
      tableEndRowIndex: table.tableEndRowIndex,
      tableStartColumnIndex: table.tableStartColumnIndex,
      tableEndColumnIndex: table.tableEndColumnIndex,
      columns: table.columns.map((column) => ({
        use: column.use,
        alias: sanitizeIdentifier(column.alias, `column_${column.index + 1}`),
        type: column.type,
      })),
    });
  }

  dropRegisteredTable() {
    if (!window.alasql || !this.registeredTableName) {
      this.registeredTableName = "";
      this.lastRegisteredSignature = "";
      return;
    }
    try {
      window.alasql(`DROP TABLE IF EXISTS ${quoteSqlIdentifier(this.registeredTableName)}`);
    } catch {
      // Ignore stale temporary table errors.
    }
    this.registeredTableName = "";
    this.lastRegisteredSignature = "";
  }

  registerSelectedTable() {
    const table = this.selectedTable;
    const rawRows = this.selectedSheet?.rawRows;
    if (!table || !rawRows) {
      return;
    }
    if (!window.alasql) {
      throw new Error("La libreria SQL no esta disponible.");
    }
    const signature = this.buildDatasetSignature(table);
    if (this.registeredTableName === table.tableName && this.lastRegisteredSignature === signature) {
      return;
    }
    this.dropRegisteredTable();
    const records = buildDatasetRecords(table, rawRows);
    window.alasql(`CREATE TABLE ${quoteSqlIdentifier(table.tableName)}`);
    window.alasql.tables[table.tableName].data = records;
    this.registeredTableName = table.tableName;
    this.lastRegisteredSignature = signature;
  }

  validateReadOnlyQuery(sql) {
    const normalized = String(sql || "").trim();
    if (!normalized) {
      return "Escribe una consulta SQL para ejecutar.";
    }
    if (!READ_ONLY_SQL_PATTERN.test(normalized)) {
      return "Solo se permiten consultas SELECT en esta version.";
    }
    if (FORBIDDEN_SQL_PATTERN.test(normalized)) {
      return "La consulta contiene instrucciones no soportadas. Usa solo SQL de lectura.";
    }
    return "";
  }

  buildSampleQuery(tableName) {
    return `SELECT *\nFROM ${quoteSqlIdentifier(tableName)}\nLIMIT 20;`;
  }

  getBuilderColumns() {
    const table = this.selectedTable;
    return table?.columns.filter((column) => column.use) || [];
  }

  getBuilderColumnByAlias(alias) {
    return this.getBuilderColumns().find(
      (column) => sanitizeIdentifier(column.alias, `column_${column.index + 1}`) === alias,
    );
  }

  getBuilderOperators(type) {
    if (type === "number" || type === "date") {
      return [
        ["eq", "Igual"],
        ["gt", "Mayor que"],
        ["gte", "Mayor o igual"],
        ["lt", "Menor que"],
        ["lte", "Menor o igual"],
        ["between", "Entre"],
      ];
    }
    if (type === "boolean") {
      return [["eq", "Igual"]];
    }
    return [
      ["eq", "Igual"],
      ["like", "Contiene"],
      ["starts", "Empieza con"],
      ["ends", "Termina con"],
    ];
  }

  buildBuilderValue(column, value) {
    const normalized = String(value ?? "").trim();
    if (!normalized) {
      return "";
    }
    if (column?.type === "number") {
      const parsed = Number(normalized.replace(/,/g, ""));
      return Number.isFinite(parsed) ? String(parsed) : "";
    }
    if (column?.type === "boolean") {
      return /^(true|si|yes|1)$/i.test(normalized) ? "true" : "false";
    }
    return `'${normalized.replace(/'/g, "''")}'`;
  }

  syncNoCodeQueryBuilder() {
    const columns = this.getBuilderColumns();
    const allowedAliases = new Set(
      columns.map((column) => sanitizeIdentifier(column.alias, `column_${column.index + 1}`)),
    );
    const currentSelected = this.state.queryBuilder.selectedColumns.filter((alias) =>
      allowedAliases.has(alias),
    );
    this.state.queryBuilder.selectedColumns = currentSelected.length
      ? currentSelected
      : Array.from(allowedAliases);

    this.state.queryBuilder.filters = this.state.queryBuilder.filters
      .filter((filter) => allowedAliases.has(filter.column))
      .map((filter) => {
        const column = this.getBuilderColumnByAlias(filter.column);
        const operators = this.getBuilderOperators(column?.type);
        const hasOperator = operators.some(([operator]) => operator === filter.operator);
        return {
          ...filter,
          operator: hasOperator ? filter.operator : operators[0][0],
        };
      });
  }

  toggleBuilderColumn(alias, checked) {
    const current = new Set(this.state.queryBuilder.selectedColumns);
    if (checked) {
      current.add(alias);
    } else {
      current.delete(alias);
    }
    this.state.queryBuilder.selectedColumns = Array.from(current);
  }

  addBuilderFilter() {
    const firstColumn = this.getBuilderColumns()[0];
    if (!firstColumn) {
      return;
    }
    const alias = sanitizeIdentifier(firstColumn.alias, `column_${firstColumn.index + 1}`);
    const operator = this.getBuilderOperators(firstColumn.type)[0][0];
    this.state.queryBuilder.filters.push({
      id: `${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
      column: alias,
      operator,
      value: "",
      valueTo: "",
    });
    this.render();
  }

  removeBuilderFilter(filterId) {
    this.state.queryBuilder.filters = this.state.queryBuilder.filters.filter(
      (filter) => filter.id !== filterId,
    );
    this.render();
  }

  updateBuilderFilter(filterId, key, value) {
    const filter = this.state.queryBuilder.filters.find((item) => item.id === filterId);
    if (!filter) {
      return;
    }
    filter[key] = value;
    if (key === "column") {
      const column = this.getBuilderColumnByAlias(value);
      filter.operator = this.getBuilderOperators(column?.type)[0][0];
      filter.value = "";
      filter.valueTo = "";
    }
    this.render();
  }

  buildNoCodeQuery() {
    const columns = this.getBuilderColumns();
    const selectedColumns = this.state.queryBuilder.selectedColumns.length
      ? this.state.queryBuilder.selectedColumns
      : columns.map((column) => sanitizeIdentifier(column.alias, `column_${column.index + 1}`));
    const selectSql = selectedColumns.length
      ? selectedColumns.map((alias) => quoteSqlIdentifier(alias)).join(", ")
      : "*";

    const whereParts = this.state.queryBuilder.filters
      .map((filter) => {
        const column = this.getBuilderColumnByAlias(filter.column);
        if (!column) {
          return "";
        }
        const identifier = quoteSqlIdentifier(filter.column);
        const valueSql = this.buildBuilderValue(column, filter.value);
        const valueToSql = this.buildBuilderValue(column, filter.valueTo);
        if (!valueSql && filter.operator !== "between") {
          return "";
        }
        if (filter.operator === "eq") {
          return `${identifier} = ${valueSql}`;
        }
        if (filter.operator === "gt") {
          return `${identifier} > ${valueSql}`;
        }
        if (filter.operator === "gte") {
          return `${identifier} >= ${valueSql}`;
        }
        if (filter.operator === "lt") {
          return `${identifier} < ${valueSql}`;
        }
        if (filter.operator === "lte") {
          return `${identifier} <= ${valueSql}`;
        }
        if (filter.operator === "between") {
          if (!valueSql || !valueToSql) {
            return "";
          }
          return `${identifier} BETWEEN ${valueSql} AND ${valueToSql}`;
        }
        const rawValue = String(filter.value ?? "").trim().replace(/'/g, "''");
        if (!rawValue) {
          return "";
        }
        if (filter.operator === "starts") {
          return `${identifier} LIKE '${rawValue}%'`;
        }
        if (filter.operator === "ends") {
          return `${identifier} LIKE '%${rawValue}'`;
        }
        return `${identifier} LIKE '%${rawValue}%'`;
      })
      .filter(Boolean);

    const whereSql = whereParts.length ? `\nWHERE ${whereParts.join("\n  AND ")}` : "";
    const limitSql =
      this.state.queryBuilder.limit > 0 ? `\nLIMIT ${this.state.queryBuilder.limit};` : ";";
    return `SELECT ${selectSql}\nFROM ${quoteSqlIdentifier(this.activeTableName)}${whereSql}${limitSql}`;
  }

  applyNoCodeQuery() {
    this.state.queryState.sql = this.buildNoCodeQuery();
    this.runQuery();
  }

  resetNoCodeQuery() {
    this.state.queryBuilder.filters = [];
    this.state.queryBuilder.limit = 20;
    this.syncNoCodeQueryBuilder();
    this.state.queryState.sql = this.buildSampleQuery(this.activeTableName);
    this.render();
  }

  syncQueryStateWithTable(forceSql = false) {
    const table = this.selectedTable;
    this.state.queryState.tableName = table?.tableName || "";
    if (
      forceSql ||
      !this.state.queryState.sql.trim() ||
      this.state.queryState.sql.includes("FROM [")
    ) {
      this.state.queryState.sql = table ? this.buildSampleQuery(table.tableName) : "";
    }
    this.syncNoCodeQueryBuilder();
  }

  clearQueryResults() {
    this.state.queryState.error = "";
    this.state.queryState.columns = [];
    this.state.queryState.rows = [];
    this.state.queryState.json = "";
    this.state.queryState.totalRows = 0;
    this.state.chartState.error = "";
    this.disposeChart();
  }

  applyStructure(silent = false) {
    const table = this.selectedTable;
    const rawRows = this.selectedSheet?.rawRows;
    if (!table || !rawRows) {
      return;
    }
    try {
      table.errors = validateTableStructure(table, rawRows);
      if (table.errors.length) {
        this.refreshDatasetStatus();
        if (!silent) {
          this.render();
        }
        return;
      }
      this.registerSelectedTable();
      table.structureApplied = true;
      table.structureDirty = false;
      this.refreshDatasetStatus();
      this.state.queryState.tableName = table.tableName;
      if (!this.state.queryState.sql.trim()) {
        this.state.queryState.sql = this.buildSampleQuery(table.tableName);
      }
      if (!silent) {
        this.render();
      }
    } catch (error) {
      this.state.queryState.error = error.message || "No se pudo preparar el dataset temporal.";
      this.refreshDatasetStatus();
      if (!silent) {
        this.render();
      }
    }
  }

  runQuery() {
    const queryError = this.validateReadOnlyQuery(this.state.queryState.sql);
    if (queryError) {
      this.clearQueryResults();
      this.state.queryState.error = queryError;
      this.render();
      return;
    }

    try {
      this.state.queryState.running = true;
      this.state.queryState.error = "";
      this.applyStructure(true);
      if (!this.state.datasetConfig.structureReady) {
        return;
      }
      const rawResult = window.alasql(this.state.queryState.sql);
      const resultRows = Array.isArray(rawResult) ? rawResult : [{ resultado: rawResult }];
      const previewRows = resultRows.slice(0, QUERY_RESULT_LIMIT);
      this.state.queryState.columns = previewRows.length ? Object.keys(previewRows[0]) : [];
      this.state.queryState.rows = previewRows;
      this.state.queryState.json = JSON.stringify(previewRows, null, 2);
      this.state.queryState.totalRows = Array.isArray(rawResult) ? rawResult.length : 1;
      this.state.queryState.activeView = this.state.queryState.activeView || "table";
      this.syncChartDefaults();
      this.state.chartState.error = "";
    } catch (error) {
      this.clearQueryResults();
      this.state.queryState.error = error.message || "La consulta no pudo ejecutarse.";
    } finally {
      this.state.queryState.running = false;
      this.render();
    }
  }

  syncChartDefaults() {
    const chartColumns = this.state.queryState.columns;
    const numericColumns = chartColumns.filter((column) =>
      this.state.queryState.rows.some((row) => toChartNumber(row[column]) !== null),
    );
    if (!chartColumns.length || !numericColumns.length) {
      this.state.chartState.categoryColumn = "";
      this.state.chartState.valueColumn = "";
      return;
    }
    if (!chartColumns.includes(this.state.chartState.categoryColumn)) {
      this.state.chartState.categoryColumn = chartColumns[0];
    }
    if (!numericColumns.includes(this.state.chartState.valueColumn)) {
      this.state.chartState.valueColumn = numericColumns[0];
    }
  }

  getChartData() {
    if (!this.state.queryState.rows.length) {
      return { error: "Ejecuta una consulta para generar la grafica." };
    }
    const { categoryColumn, valueColumn, aggregate } = this.state.chartState;
    if (!categoryColumn || !valueColumn) {
      return { error: "Selecciona las columnas para configurar la grafica." };
    }
    const grouped = new Map();
    this.state.queryState.rows.forEach((row) => {
      const key = String(row[categoryColumn] ?? "(sin valor)");
      const current = grouped.get(key) || [];
      current.push(aggregate === "count" ? 1 : toChartNumber(row[valueColumn]));
      grouped.set(key, current);
    });
    const categories = [];
    const values = [];
    grouped.forEach((rawValues, key) => {
      categories.push(key);
      values.push(aggregateValues(rawValues, aggregate));
    });
    if (!categories.length) {
      return { error: "El resultado actual no contiene datos graficables." };
    }
    return { categories, values };
  }

  ensureChartRendered() {
    if (!this.root || this.state.queryState.activeView !== "chart") {
      this.disposeChart();
      return;
    }
    const chartHost = this.root.querySelector("[data-zrn-chart-root='1']");
    if (!chartHost || !window.echarts) {
      return;
    }
    const chartData = this.getChartData();
    this.state.chartState.error = chartData.error || "";
    if (chartData.error) {
      this.disposeChart();
      return;
    }

    const renderToken = ++this.chartRenderToken;
    window.requestAnimationFrame(() => {
      if (renderToken !== this.chartRenderToken || !this.root) {
        return;
      }
      this.chartInstance =
        window.echarts.getInstanceByDom(chartHost) ||
        window.echarts.init(chartHost, null, { renderer: "canvas" });
      this.chartInstance.setOption(this.buildChartOption(chartData), true);
      this.chartInstance.resize();
    });
  }

  buildChartOption(chartData) {
    const palette = ["#355d9a", "#5d8bd4", "#7aa9d8", "#6b8e5a", "#cf8d43", "#8f5d8a"];
    const { type, categoryColumn, valueColumn, aggregate } = this.state.chartState;
    if (type === "pie") {
      return {
        color: palette,
        tooltip: { trigger: "item" },
        legend: { bottom: 0 },
        series: [
          {
            type: "pie",
            radius: ["35%", "70%"],
            itemStyle: { borderRadius: 4 },
            data: chartData.categories.map((category, index) => ({
              name: category,
              value: chartData.values[index],
            })),
          },
        ],
      };
    }

    return {
      color: palette,
      tooltip: { trigger: "axis" },
      grid: { left: 48, right: 18, top: 20, bottom: 40, containLabel: true },
      xAxis: {
        type: "category",
        data: chartData.categories,
        axisLabel: { color: "#58709a" },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#58709a" },
      },
      series: [
        {
          name: `${aggregate.toUpperCase()} ${valueColumn}`,
          type,
          smooth: type === "line",
          data: chartData.values,
          barMaxWidth: 42,
        },
      ],
      toolbox: { right: 0, feature: { saveAsImage: {} } },
      title: {
        text: `${categoryColumn} vs ${aggregate.toUpperCase()} ${valueColumn}`,
        textStyle: { fontSize: 12, fontWeight: 700, color: "#355d9a" },
      },
    };
  }

  disposeChart() {
    if (this.chartInstance) {
      this.chartInstance.dispose();
      this.chartInstance = null;
    }
    this.chartRenderToken += 1;
  }

  resetAll() {
    if (
      this.hasTransientData &&
      !window.confirm("Se eliminara el origen temporal, la consulta y los resultados. Deseas continuar?")
    ) {
      return;
    }
    this.disposeChart();
    this.dropRegisteredTable();
    this.state = this.getInitialState();
    this.render();
  }

  get screenMode() {
    return this.root?.dataset?.zrnProcessingScreen || "workspace";
  }

  renderLanding() {
    const isLocal = this.state.sourceInput.mode === "local_file";
    const isGoogle = this.state.sourceInput.mode === "google_sheet";
    return `
      <div class="zrn_processing_landing">
        <section class="zrn_processing_panel">
          <div class="zrn_processing_panel_head">
            <strong>Origen temporal</strong>
            <span>Archivo local o Google Sheets publico</span>
          </div>
          <div class="zrn_processing_panel_body">
            <div class="zrn_processing_entry_bar">
              <label class="zrn_processing_source_tile ${isLocal ? "is-active" : ""}">
                <input type="file" data-action="file" accept=".csv,.json,.xml,.xls,.xlsx,.xlsm" />
                <span class="zrn_processing_source_tile_icon"><i class="fa fa-upload"></i></span>
                <strong>Cargar archivo</strong>
                <small>CSV, JSON, XML y Excel</small>
              </label>
              <button
                type="button"
                class="zrn_processing_source_tile ${isGoogle ? "is-active" : ""}"
                data-action="source-mode"
                data-mode="google_sheet"
              >
                <span class="zrn_processing_source_tile_icon"><i class="fa fa-table"></i></span>
                <strong>Google Sheet</strong>
                <small>URL publica por sesion</small>
              </button>
            </div>
            ${
              isGoogle
                ? `
                  <div class="zrn_processing_source_inline">
                    <div class="zrn_processing_field zrn_processing_source_url_field">
                      <label>URL publica</label>
                      <input
                        type="url"
                        class="form-control"
                        data-action="google-sheet-url"
                        value="${escapeHtml(this.state.sourceInput.googleSheetUrl)}"
                        placeholder="https://docs.google.com/spreadsheets/d/..."
                      />
                    </div>
                    <div class="zrn_processing_actions">
                      <button type="button" class="btn btn-primary" data-action="google-sheet-connect">Conectar</button>
                    </div>
                  </div>
                `
                : ""
            }
            <div class="zrn_processing_hint_strip">
              El origen vive solo en esta sesion del navegador. Si sales o recargas la pagina, se pierde.
            </div>
          </div>
        </section>
      </div>
    `;
  }

  renderOverviewPanel(sheet, table) {
    const sourceTypeLabel =
      this.state.sourceMeta.type === "google_sheet" ? "Google Sheets publico" : "Archivo local";
    const tableCount = sheet?.tables.length || 0;
    return `
      <section class="zrn_processing_panel zrn_processing_overview_panel">
        <div class="zrn_processing_panel_head">
          <strong>Origen activo</strong>
          <span>${sourceTypeLabel}</span>
        </div>
        <div class="zrn_processing_panel_body">
          <div class="zrn_processing_overview_top">
            <div class="zrn_processing_file_overview">
              <div class="zrn_processing_file_icon">
                <i class="fa ${escapeHtml(this.state.sourceMeta.iconClass)}"></i>
              </div>
              <div class="zrn_processing_file_copy">
                <div class="zrn_processing_file_name">${escapeHtml(this.state.sourceMeta.name)}</div>
                <div class="zrn_processing_helper">
                  ${escapeHtml(sourceTypeLabel)} / ${escapeHtml(this.state.sourceMeta.sizeLabel)} / ${this.state.sourceMeta.totalSheets} hoja(s)
                </div>
              </div>
            </div>
            <div class="zrn_processing_file_actions">
              <label class="btn btn-secondary zrn_processing_replace_btn">
                Reemplazar archivo
                <input type="file" data-action="file" accept=".csv,.json,.xml,.xls,.xlsx,.xlsm" />
              </label>
              <button type="button" class="btn btn-secondary" data-action="back-to-processing">Volver a carga</button>
              <button type="button" class="btn btn-secondary" data-action="reset-source">Limpiar sesion</button>
            </div>
          </div>
          <div class="zrn_processing_field_grid zrn_processing_overview_controls">
            <div class="zrn_processing_field">
              <label>Hoja activa</label>
              <select class="form-select" data-action="sheet-select">
                ${this.state.datasetConfig.sheets
                  .map(
                    (currentSheet) => `
                      <option value="${currentSheet.id}" ${this.state.datasetConfig.selectedSheetId === currentSheet.id ? "selected" : ""}>
                        ${escapeHtml(currentSheet.name)}
                      </option>
                    `,
                  )
                  .join("")}
              </select>
            </div>
            <div class="zrn_processing_field">
              <label>Tabla activa</label>
              <select class="form-select" data-action="table-select">
                ${(sheet?.tables || [])
                  .map(
                    (currentTable) => `
                      <option value="${currentTable.id}" ${sheet.selectedTableId === currentTable.id ? "selected" : ""}>
                        ${escapeHtml(currentTable.name)}
                      </option>
                    `,
                  )
                  .join("")}
              </select>
            </div>
            <div class="zrn_processing_field">
              <label>Tabla SQL</label>
              <input type="text" class="form-control" value="${escapeHtml(table?.tableName || "")}" disabled="disabled" />
            </div>
          </div>
          <div class="zrn_processing_file_details_wrap">
            <table class="o_list_table table table-sm zrn_processing_file_details_table">
              <tbody>
                <tr><th>Origen</th><td>${escapeHtml(this.state.sourceMeta.name)}</td></tr>
                <tr><th>Tipo</th><td>${escapeHtml(sourceTypeLabel)}</td></tr>
                <tr><th>Hoja</th><td>${escapeHtml(sheet?.name || "-")}</td></tr>
                <tr><th>Tablas detectadas</th><td>${tableCount}</td></tr>
                <tr><th>Tabla activa</th><td>${escapeHtml(table?.name || "-")}</td></tr>
                <tr><th>Estado</th><td>${escapeHtml(this.state.datasetConfig.statusLabel)}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    `;
  }

  renderDatasetPanel(sheet, table) {
    const tableErrors = table?.errors || [];
    const overviewStatusClass = tableErrors.length
      ? "is-danger"
      : this.state.datasetConfig.structureReady
        ? "is-ready"
        : this.state.sourceMeta.loaded
          ? "is-pending"
          : "";
    const maxSheetColumns = sheet
      ? Math.max(...sheet.rawRows.map((row) => row.length), 0)
      : 0;
    const startColumnOptions = table
      ? Array.from({ length: maxSheetColumns }, (_, index) => {
          const rowLabel = sheet.rawRows[table.tableStartRowIndex]?.[index];
          const optionLabel = rowLabel
            ? `${getColumnLabel(index)} / ${String(rowLabel).trim().slice(0, 36)}`
            : getColumnLabel(index);
          return `<option value="${index}" ${index === table.tableStartColumnIndex ? "selected" : ""}>${escapeHtml(optionLabel)}</option>`;
        }).join("")
      : "";
    const endColumnOptions = table
      ? Array.from({ length: maxSheetColumns }, (_, index) => {
          const rowLabel = sheet.rawRows[table.tableStartRowIndex]?.[index];
          const optionLabel = rowLabel
            ? `${getColumnLabel(index)} / ${String(rowLabel).trim().slice(0, 36)}`
            : getColumnLabel(index);
          return `<option value="${index}" ${index === table.tableEndColumnIndex ? "selected" : ""}>${escapeHtml(optionLabel)}</option>`;
        }).join("")
      : "";
    const tableList = (sheet?.tables || [])
      .map(
        (currentTable) => `
          <div class="zrn_processing_table_card ${currentTable.id === sheet.selectedTableId ? "is-active" : ""}">
            <button type="button" class="zrn_processing_table_card_main" data-action="table-select" value="${currentTable.id}">
              <strong>${escapeHtml(currentTable.name)}</strong>
              <small>${escapeHtml(currentTable.tableName)} · ${currentTable.dataRowsCount} filas</small>
            </button>
            ${
              sheet.tables.length > 1
                ? `<button type="button" class="btn btn-secondary btn-sm" data-action="table-remove" data-table-id="${currentTable.id}">Quitar</button>`
                : ""
            }
          </div>
        `,
      )
      .join("");
    const columnRows = table
      ? table.columns
          .map(
            (column, index) => `
              <tr>
                <td><input type="checkbox" data-action="column-use" data-column-index="${index}" ${column.use ? "checked" : ""} /></td>
                <td>${escapeHtml(column.columnLabel)} / ${escapeHtml(column.originalLabel)}</td>
                <td>
                  <input type="text" class="form-control" data-action="column-alias" data-column-index="${index}" value="${escapeHtml(column.alias)}" />
                </td>
                <td>
                  <select class="form-select" data-action="column-type" data-column-index="${index}">
                    ${SQL_TYPES.map(
                      (type) =>
                        `<option value="${type}" ${column.type === type ? "selected" : ""}>${type}</option>`,
                    ).join("")}
                  </select>
                </td>
              </tr>
            `,
          )
          .join("")
      : "";
    return `
      <section class="zrn_processing_panel">
        <div class="zrn_processing_panel_head">
          <strong>Dataset temporal</strong>
          <span>${table ? `${table.dataRowsCount} filas detectadas` : "Sin estructura"}</span>
        </div>
        <div class="zrn_processing_panel_body">
          ${
            table
              ? `
                ${tableErrors.length ? `<div class="zrn_processing_sheet_errors">${tableErrors.map((error) => escapeHtml(error)).join("<br/>")}</div>` : ""}
                <div class="zrn_processing_table_stack">
                  <div class="zrn_processing_table_stack_head">
                    <strong>Tablas de la hoja</strong>
                    <button type="button" class="btn btn-secondary" data-action="table-add">Crear tabla</button>
                  </div>
                  <div class="zrn_processing_table_list">${tableList}</div>
                </div>
                <div class="zrn_processing_range_grid zrn_processing_range_grid_extended">
                  <div class="zrn_processing_field">
                    <label>Nombre visible</label>
                    <input type="text" class="form-control" data-action="table-name" value="${escapeHtml(table.name)}" />
                  </div>
                  <div class="zrn_processing_field">
                    <label>Tabla SQL</label>
                    <input type="text" class="form-control" data-action="table-sql-name" value="${escapeHtml(table.tableName)}" />
                  </div>
                  <div class="zrn_processing_field">
                    <label>Fila de encabezado</label>
                    <input type="number" min="1" max="${sheet.rawRows.length || 1}" class="form-control" data-action="table-start-row" value="${table.tableStartRowIndex + 1}" />
                  </div>
                  <div class="zrn_processing_field">
                    <label>Fila final</label>
                    <input type="number" min="1" max="${sheet.rawRows.length || 1}" class="form-control" data-action="table-end-row" value="${table.tableEndRowIndex + 1}" />
                  </div>
                  <div class="zrn_processing_field">
                    <label>Columna inicial</label>
                    <select class="form-select" data-action="table-start-column">${startColumnOptions}</select>
                  </div>
                  <div class="zrn_processing_field">
                    <label>Columna final</label>
                    <select class="form-select" data-action="table-end-column">${endColumnOptions}</select>
                  </div>
                  <div class="zrn_processing_field">
                    <label>Estado</label>
                    <div class="zrn_processing_status_inline ${overviewStatusClass}">${escapeHtml(this.state.datasetConfig.statusLabel)}</div>
                  </div>
                </div>
                <div class="zrn_processing_actions">
                  <button type="button" class="btn btn-primary" data-action="apply-structure">Aplicar estructura</button>
                </div>
                <div class="zrn_processing_columns_wrap">
                  <table class="o_list_table table table-sm zrn_processing_columns">
                    <thead>
                      <tr>
                        <th>Usar</th>
                        <th>Origen</th>
                        <th>Alias SQL</th>
                        <th>Tipo</th>
                      </tr>
                    </thead>
                    <tbody>${columnRows}</tbody>
                  </table>
                </div>
              `
              : '<div class="zrn_processing_empty">Carga un origen para definir tablas y columnas.</div>'
          }
        </div>
      </section>
    `;
  }

  renderQueryPanel(table) {
    const builderColumns = this.getBuilderColumns();
    const builderColumnItems = builderColumns
      .map((column) => {
        const alias = sanitizeIdentifier(column.alias, `column_${column.index + 1}`);
        const checked = this.state.queryBuilder.selectedColumns.includes(alias);
        return `
          <label class="zrn_processing_builder_column">
            <input type="checkbox" data-action="builder-column" value="${escapeHtml(alias)}" ${checked ? "checked" : ""} />
            <span>${escapeHtml(alias)}</span>
            <small>${escapeHtml(column.originalLabel)}</small>
          </label>
        `;
      })
      .join("");
    const builderFilterRows = this.state.queryBuilder.filters
      .map((filter) => {
        const column = this.getBuilderColumnByAlias(filter.column) || builderColumns[0];
        const operators = this.getBuilderOperators(column?.type);
        const needsRange = filter.operator === "between";
        const valueInputType =
          column?.type === "number" ? "number" : column?.type === "date" ? "date" : "text";
        return `
          <div class="zrn_processing_builder_filter_row">
            <select class="form-select" data-action="builder-filter-column" data-filter-id="${filter.id}">
              ${builderColumns
                .map((item) => {
                  const alias = sanitizeIdentifier(item.alias, `column_${item.index + 1}`);
                  return `<option value="${escapeHtml(alias)}" ${filter.column === alias ? "selected" : ""}>${escapeHtml(alias)}</option>`;
                })
                .join("")}
            </select>
            <select class="form-select" data-action="builder-filter-operator" data-filter-id="${filter.id}">
              ${operators
                .map(
                  ([operator, label]) =>
                    `<option value="${operator}" ${filter.operator === operator ? "selected" : ""}>${label}</option>`,
                )
                .join("")}
            </select>
            <input type="${valueInputType}" class="form-control" data-action="builder-filter-value" data-filter-id="${filter.id}" value="${escapeHtml(filter.value)}" placeholder="Valor" />
            ${
              needsRange
                ? `<input type="${valueInputType}" class="form-control" data-action="builder-filter-value-to" data-filter-id="${filter.id}" value="${escapeHtml(filter.valueTo)}" placeholder="Hasta" />`
                : '<div class="zrn_processing_builder_filter_spacer"></div>'
            }
            <button type="button" class="btn btn-secondary" data-action="builder-remove-filter" data-filter-id="${filter.id}">Quitar</button>
          </div>
        `;
      })
      .join("");
    return `
      <section class="zrn_processing_panel">
        <div class="zrn_processing_panel_head">
          <strong>Consulta</strong>
          <span class="zrn_processing_head_meta">
            Constructor no-code y editor SQL
            <details class="zrn_processing_sql_help">
              <summary class="zrn_processing_sql_help_toggle" aria-label="Guia SQL">
                <i class="fa fa-info-circle"></i>
              </summary>
              <div class="zrn_processing_sql_help_popover">
                <strong>SQL permitido</strong>
                <span><code>SELECT</code>, <code>WHERE</code>, <code>GROUP BY</code>, <code>ORDER BY</code>, <code>LIMIT</code></span>
                <span>Una tabla activa por consulta en esta version.</span>
                <span>No se permiten <code>INSERT</code>, <code>UPDATE</code>, <code>DELETE</code>, <code>DROP</code>, <code>CREATE</code>, <code>ALTER</code>.</span>
              </div>
            </details>
          </span>
        </div>
        <div class="zrn_processing_panel_body">
          <div class="zrn_processing_query_workspace">
            <div class="zrn_processing_query_builder">
              <div class="zrn_processing_query_hint">
                Tabla disponible: <code>${escapeHtml(table?.tableName || "dataset")}</code>. Activa columnas y filtros sobre la tabla seleccionada.
              </div>
              <div class="zrn_processing_builder_section">
                <div class="zrn_processing_builder_title">Columnas a mostrar</div>
                <div class="zrn_processing_builder_columns">
                  ${builderColumnItems || '<div class="zrn_processing_empty">No hay columnas activas disponibles.</div>'}
                </div>
              </div>
              <div class="zrn_processing_builder_section">
                <div class="zrn_processing_builder_title">Filtros</div>
                <div class="zrn_processing_builder_filters">
                  ${builderFilterRows || '<div class="zrn_processing_empty">No hay filtros agregados.</div>'}
                </div>
                <div class="zrn_processing_actions">
                  <button type="button" class="btn btn-secondary" data-action="builder-add-filter">Agregar filtro</button>
                </div>
              </div>
              <div class="zrn_processing_builder_footer">
                <div class="zrn_processing_field">
                  <label>Limite</label>
                  <input type="number" min="1" class="form-control" data-action="builder-limit" value="${escapeHtml(this.state.queryBuilder.limit)}" />
                </div>
                <div class="zrn_processing_actions">
                  <button type="button" class="btn btn-primary" data-action="builder-generate">Construir y ejecutar</button>
                  <button type="button" class="btn btn-secondary" data-action="builder-clear">Limpiar builder</button>
                </div>
              </div>
            </div>
            <div class="zrn_processing_query_editor">
              <div class="zrn_processing_query_toolbar">
                <button
                  type="button"
                  class="btn btn-primary zrn_processing_query_play"
                  data-action="run-query"
                  ${this.state.sourceMeta.loaded ? "" : "disabled"}
                  aria-label="${this.state.queryState.running ? "Ejecutando" : "Ejecutar SQL"}"
                  title="${this.state.queryState.running ? "Ejecutando" : "Ejecutar SQL"}"
                >
                  <i class="fa fa-play"></i>
                </button>
              </div>
              <textarea class="zrn_processing_query_area" data-action="sql-input" placeholder="SELECT * FROM [dataset] LIMIT 20;">${escapeHtml(
                this.state.queryState.sql,
              )}</textarea>
              ${
                this.state.queryState.error
                  ? `<div class="zrn_processing_query_error">${escapeHtml(this.state.queryState.error)}</div>`
                  : ""
              }
            </div>
          </div>
        </div>
      </section>
    `;
  }

  renderResultPanel() {
    const resultColumns = this.state.queryState.columns;
    const resultRows = this.state.queryState.rows;
    const numericResultColumns = resultColumns.filter((column) =>
      resultRows.some((row) => toChartNumber(row[column]) !== null),
    );
    const resultTabs = [
      ["table", "Tabla"],
      ["json", "JSON"],
      ["chart", "Grafica"],
    ];
    const resultHead = resultColumns.map((column) => `<th>${escapeHtml(column)}</th>`).join("");
    const resultBody = resultRows
      .map((row) => {
        const cells = resultColumns
          .map((column) => `<td>${escapeHtml(row[column] ?? "")}</td>`)
          .join("");
        return `<tr>${cells}</tr>`;
      })
      .join("");
    const resultTabButtons = resultTabs
      .map(
        ([key, label]) => `
          <button
            type="button"
            class="btn zrn_processing_result_tab ${this.state.queryState.activeView === key ? "is-active" : ""}"
            data-action="result-view"
            data-view="${key}"
            ${key === "chart" && !resultRows.length ? "disabled" : ""}
          >
            ${label}
          </button>
        `,
      )
      .join("");
    const chartConfig = resultRows.length
      ? `
          <div class="zrn_processing_chart_form">
            <div class="zrn_processing_field">
              <label>Tipo</label>
              <select class="form-select" data-action="chart-type">
                <option value="bar" ${this.state.chartState.type === "bar" ? "selected" : ""}>Barra</option>
                <option value="line" ${this.state.chartState.type === "line" ? "selected" : ""}>Linea</option>
                <option value="pie" ${this.state.chartState.type === "pie" ? "selected" : ""}>Pie</option>
              </select>
            </div>
            <div class="zrn_processing_field">
              <label>Eje X</label>
              <select class="form-select" data-action="chart-category">
                ${resultColumns
                  .map(
                    (column) =>
                      `<option value="${escapeHtml(column)}" ${this.state.chartState.categoryColumn === column ? "selected" : ""}>${escapeHtml(column)}</option>`,
                  )
                  .join("")}
              </select>
            </div>
            <div class="zrn_processing_field">
              <label>Metrica Y</label>
              <select class="form-select" data-action="chart-value">
                ${numericResultColumns
                  .map(
                    (column) =>
                      `<option value="${escapeHtml(column)}" ${this.state.chartState.valueColumn === column ? "selected" : ""}>${escapeHtml(column)}</option>`,
                  )
                  .join("")}
              </select>
            </div>
            <div class="zrn_processing_field">
              <label>Agregacion</label>
              <select class="form-select" data-action="chart-aggregate">
                ${["sum", "avg", "count", "min", "max"]
                  .map(
                    (aggregate) =>
                      `<option value="${aggregate}" ${this.state.chartState.aggregate === aggregate ? "selected" : ""}>${aggregate.toUpperCase()}</option>`,
                  )
                  .join("")}
              </select>
            </div>
          </div>
        `
      : "";
    const chartPreview = this.state.queryState.activeView === "chart" ? this.getChartData() : null;
    this.state.chartState.error = chartPreview?.error || "";
    const resultContent =
      this.state.queryState.activeView === "json"
        ? this.state.queryState.json
          ? `<div class="zrn_processing_result_json_wrap"><pre class="zrn_processing_result_json">${escapeHtml(this.state.queryState.json)}</pre></div>`
          : '<div class="zrn_processing_result_empty">Ejecuta una consulta para ver el JSON.</div>'
        : this.state.queryState.activeView === "chart"
          ? `
              ${chartConfig}
              ${chartPreview?.error ? `<div class="zrn_processing_query_error">${escapeHtml(chartPreview.error)}</div>` : ""}
              ${chartPreview?.error ? "" : '<div class="zrn_processing_chart_canvas" data-zrn-chart-root="1"></div>'}
            `
          : resultColumns.length
            ? `
                <div class="zrn_processing_result_wrap">
                  <table class="o_list_table table table-sm zrn_processing_result_table">
                    <thead><tr>${resultHead}</tr></thead>
                    <tbody>${resultBody}</tbody>
                  </table>
                </div>
              `
            : '<div class="zrn_processing_result_empty">Ejecuta una consulta para ver resultados.</div>';
    return `
      <section class="zrn_processing_panel">
        <div class="zrn_processing_panel_head">
          <strong>Resultados</strong>
          <span>${this.state.queryState.totalRows} fila(s) / preview maximo ${QUERY_RESULT_LIMIT}</span>
        </div>
        <div class="zrn_processing_panel_body">
          <div class="zrn_processing_result_tabs">${resultTabButtons}</div>
          <div class="zrn_processing_result_stage">${resultContent}</div>
        </div>
      </section>
    `;
  }

  renderHelpPanel() {
    return `
      <section class="zrn_processing_panel">
        <div class="zrn_processing_panel_head">
          <strong>Ayuda SQL</strong>
          <span>Referencia rapida</span>
        </div>
        <div class="zrn_processing_panel_body">
          <ul class="zrn_processing_table_list_plain">
            <li><strong>Tabla:</strong> <code>${escapeHtml(this.state.queryState.tableName || "dataset")}</code></li>
            <li><strong>Permitido:</strong> SELECT, WHERE, GROUP BY, ORDER BY, LIMIT</li>
            <li><strong>Agregados:</strong> COUNT, SUM, AVG, MIN, MAX</li>
            <li><strong>No permitido:</strong> INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, ATTACH</li>
          </ul>
        </div>
      </section>
    `;
  }

  render() {
    if (!this.root) {
      return;
    }
    if (this.screenMode === "landing") {
      this.root.innerHTML = this.renderLanding();
      this.disposeChart();
      return;
    }

    const sheet = this.selectedSheet;
    const table = this.selectedTable;
    this.root.innerHTML = `
      <div class="zrn_processing_app">
        ${this.state.globalError ? `<div class="zrn_processing_global_error">${escapeHtml(this.state.globalError)}</div>` : ""}
        ${
          !this.state.sourceMeta.loaded
            ? `
              <section class="zrn_processing_panel">
                <div class="zrn_processing_panel_head">
                  <strong>Origen pendiente</strong>
                  <span>Sin dataset activo</span>
                </div>
                <div class="zrn_processing_panel_body">
                  <div class="zrn_processing_empty_state">
                    <div class="zrn_processing_empty">No hay origen temporal cargado en esta sesion.</div>
                    <div class="zrn_processing_actions">
                      <button type="button" class="btn btn-secondary" data-action="back-to-processing">Volver a carga</button>
                    </div>
                  </div>
                </div>
              </section>
            `
            : `
              ${this.renderOverviewPanel(sheet, table)}
              ${this.renderDatasetPanel(sheet, table)}
              ${this.renderQueryPanel(table)}
              ${this.renderResultPanel()}
              ${this.renderHelpPanel()}
            `
        }
      </div>
    `;

    this.ensureChartRendered();
  }
}

let sharedProcessingView = null;

export function getSharedProcessingView() {
  if (!sharedProcessingView) {
    sharedProcessingView = new ZrnAnalyticsProcessingView();
  }
  return sharedProcessingView;
}

function syncStandaloneProcessingRoot() {
  if (typeof document === "undefined") {
    return;
  }
  const root = document.querySelector("[data-zrn-processing-root='1']");
  const view = getSharedProcessingView();
  if (root && view.root !== root) {
    view.mount(root);
    return;
  }
  if (!root && view.root) {
    view.unmount();
  }
}

function bootstrapStandaloneProcessingRoot() {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return;
  }
  let scheduled = false;
  const scheduleSync = () => {
    if (scheduled) {
      return;
    }
    scheduled = true;
    window.requestAnimationFrame(() => {
      scheduled = false;
      syncStandaloneProcessingRoot();
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scheduleSync, { once: true });
  } else {
    scheduleSync();
  }

  const observerTarget = document.body || document.documentElement;
  if (!observerTarget) {
    return;
  }
  const observer = new MutationObserver(() => {
    scheduleSync();
  });
  observer.observe(observerTarget, { childList: true, subtree: true });
}

bootstrapStandaloneProcessingRoot();
