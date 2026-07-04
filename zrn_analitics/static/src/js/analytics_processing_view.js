/** @odoo-module **/

const HEADER_SCAN_LIMIT = 25;
const PREVIEW_ROW_LIMIT = 8;
const QUERY_RESULT_LIMIT = 200;
const SQL_TYPES = ["text", "number", "date", "boolean"];
const READ_ONLY_SQL_PATTERN = /^\s*select\b/i;
const FORBIDDEN_SQL_PATTERN = /\b(insert|update|delete|drop|create|alter|attach|truncate|replace|merge|grant|revoke)\b/i;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function sanitizeIdentifier(value, fallback = "column") {
  let normalized = String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Za-z0-9_]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
  if (!normalized) {
    normalized = fallback;
  }
  if (/^[0-9]/.test(normalized)) {
    normalized = `${fallback}_${normalized}`;
  }
  return normalized;
}

function quoteSqlIdentifier(value) {
  return `[${String(value ?? "").replace(/]/g, "]]")}]`;
}

function buildRowSnippet(row = []) {
  return row
    .slice(0, 5)
    .map((cell) => String(cell ?? "").trim())
    .filter(Boolean)
    .join(" | ");
}

function isRowEmpty(row = []) {
  return !row.some((cell) => String(cell ?? "").trim() !== "");
}

function formatBytes(size) {
  const units = ["B", "KB", "MB", "GB"];
  let value = Number(size || 0);
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value >= 100 || unitIndex === 0 ? Math.round(value) : value.toFixed(1)} ${units[unitIndex]}`;
}

function getColumnLabel(index) {
  let value = index + 1;
  let label = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    value = Math.floor((value - 1) / 26);
  }
  return label;
}

function getLastNonEmptyColumnIndex(row = []) {
  for (let index = row.length - 1; index >= 0; index -= 1) {
    if (String(row[index] ?? "").trim()) {
      return index;
    }
  }
  return -1;
}

function getFirstNonEmptyColumnIndex(row = []) {
  for (let index = 0; index < row.length; index += 1) {
    if (String(row[index] ?? "").trim()) {
      return index;
    }
  }
  return 0;
}

function inferColumnType(values) {
  for (const rawValue of values) {
    const value = String(rawValue ?? "").trim();
    if (!value) {
      continue;
    }
    if (/^(true|false|si|no|yes)$/i.test(value)) {
      return "boolean";
    }
    if (!Number.isNaN(Number(value.replace(/,/g, "")))) {
      return "number";
    }
    if (/^\d{4}[-/]\d{1,2}[-/]\d{1,2}$/.test(value) || /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/.test(value)) {
      return "date";
    }
    return "text";
  }
  return "text";
}

function normalizeCellValue(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function parseCsvLine(line) {
  const row = [];
  let current = "";
  let inQuotes = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (character === '"') {
      if (inQuotes && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (character === "," && !inQuotes) {
      row.push(current);
      current = "";
      continue;
    }
    current += character;
  }
  row.push(current);
  return row;
}

function parseCsvText(text) {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .filter((line) => line.length || text.includes("\n"))
    .map((line) => parseCsvLine(line));
}

function buildRowsFromObjects(records) {
  const columns = [];
  const seen = new Set();
  for (const record of records) {
    for (const key of Object.keys(record || {})) {
      if (!seen.has(key)) {
        seen.add(key);
        columns.push(key);
      }
    }
  }
  return [
    columns,
    ...records.map((record) => columns.map((column) => normalizeCellValue(record?.[column]))),
  ];
}

function extractJsonRows(text) {
  const payload = JSON.parse(text);
  if (Array.isArray(payload)) {
    if (payload.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      return buildRowsFromObjects(payload);
    }
    return [["value"], ...payload.map((item) => [normalizeCellValue(item)])];
  }
  if (payload && typeof payload === "object") {
    const objectArray = Object.values(payload).find(
      (value) =>
        Array.isArray(value) &&
        value.every((item) => item && typeof item === "object" && !Array.isArray(item))
    );
    if (objectArray) {
      return buildRowsFromObjects(objectArray);
    }
    return buildRowsFromObjects([payload]);
  }
  return [["value"], [normalizeCellValue(payload)]];
}

function extractXmlRows(text) {
  const xml = new DOMParser().parseFromString(text, "application/xml");
  if (xml.querySelector("parsererror")) {
    throw new Error("No se pudo interpretar el XML.");
  }
  const root = xml.documentElement;
  const directChildren = Array.from(root.children);
  if (!directChildren.length) {
    return [[root.nodeName], [root.textContent?.trim() || ""]];
  }
  const counts = directChildren.reduce((accumulator, node) => {
    accumulator[node.nodeName] = (accumulator[node.nodeName] || 0) + 1;
    return accumulator;
  }, {});
  const repeatedName = Object.keys(counts).find((name) => counts[name] > 1);
  const rowNodes = repeatedName
    ? directChildren.filter((node) => node.nodeName === repeatedName)
    : directChildren;
  return buildRowsFromObjects(
    rowNodes.map((node) => {
      const record = {};
      const children = Array.from(node.children);
      if (!children.length) {
        record.value = node.textContent?.trim() || "";
        return record;
      }
      for (const child of children) {
        record[child.nodeName] = child.textContent?.trim() || "";
      }
      return record;
    })
  );
}

function coerceValueByType(value, type) {
  const normalized = String(value ?? "").trim();
  if (!normalized) {
    return null;
  }
  if (type === "number") {
    const parsed = Number(normalized.replace(/,/g, ""));
    return Number.isNaN(parsed) ? null : parsed;
  }
  if (type === "boolean") {
    if (/^(true|si|yes|1)$/i.test(normalized)) {
      return true;
    }
    if (/^(false|no|0)$/i.test(normalized)) {
      return false;
    }
    return normalized;
  }
  return normalized;
}

function cloneRows(rows) {
  return rows.map((row) => [...row]);
}

function buildFileIcon(extension) {
  if (["xls", "xlsx", "xlsm"].includes(extension)) {
    return "fa-file-excel-o";
  }
  if (["json", "xml"].includes(extension)) {
    return "fa-file-code-o";
  }
  if (extension === "csv") {
    return "fa-table";
  }
  return "fa-file-o";
}

function aggregateValues(values, aggregate) {
  const numericValues = values.filter((value) => typeof value === "number" && !Number.isNaN(value));
  if (aggregate === "count") {
    return values.length;
  }
  if (!numericValues.length) {
    return 0;
  }
  if (aggregate === "avg") {
    return numericValues.reduce((sum, value) => sum + value, 0) / numericValues.length;
  }
  if (aggregate === "min") {
    return Math.min(...numericValues);
  }
  if (aggregate === "max") {
    return Math.max(...numericValues);
  }
  return numericValues.reduce((sum, value) => sum + value, 0);
}

function toChartNumber(value) {
  if (typeof value === "number") {
    return value;
  }
  const parsed = Number(String(value ?? "").replace(/,/g, ""));
  return Number.isNaN(parsed) ? null : parsed;
}

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
      fileMeta: {
        name: "",
        extension: "",
        sizeLabel: "",
        iconClass: "fa-file-o",
        activeSheetName: "",
        totalSheets: 0,
        loaded: false,
      },
      datasetConfig: {
        sheets: [],
        selectedSheetId: "",
        structureReady: false,
        structureDirty: false,
        statusLabel: "Sin archivo",
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
      this.state.fileMeta.loaded ||
        this.state.queryState.sql.trim() ||
        this.state.queryState.rows.length ||
        this.state.datasetConfig.sheets.length
    );
  }

  get selectedSheet() {
    return (
      this.state.datasetConfig.sheets.find(
        (sheet) => sheet.id === this.state.datasetConfig.selectedSheetId
      ) || null
    );
  }

  get activeTableName() {
    return this.selectedSheet?.tableName || "dataset";
  }

  async confirmDiscardIfNeeded() {
    if (!this.hasTransientData) {
      return true;
    }
    return window.confirm(
      "El archivo temporal y el trabajo de esta sesion se perderan al salir. Deseas continuar?"
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
        ".zrn_processing_leave_btn, .o_control_panel, .o_main_navbar, .o_menu_sections, .o_breadcrumb, .o_pager"
      )
    ) {
      return;
    }

    const canLeave = window.confirm(
      "El archivo temporal se perdera si sales de Procesamiento. Deseas continuar?"
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
    if (action === "table-start-row" && event.type === "change") {
      this.updateTableRange("tableStartRowIndex", Number(source.value || 1) - 1);
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
    if (action === "reset-file" && event.type === "click") {
      event.preventDefault();
      this.resetAll();
      return;
    }
    if (action === "sample-query" && event.type === "click") {
      event.preventDefault();
      this.loadSampleQuery();
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
    if (this.state.fileMeta.loaded) {
      const shouldReplace = window.confirm(
        "Solo se permite un archivo por sesion. Cargar uno nuevo reemplazara el actual. Deseas continuar?"
      );
      if (!shouldReplace) {
        input.value = "";
        return;
      }
    }

    try {
      this.dropRegisteredTable();
      this.disposeChart();
      const extension = (file.name.split(".").pop() || "").toLowerCase();
      const parsedSheets = await this.parseFile(file, extension);
      if (!parsedSheets.length) {
        throw new Error("El archivo no genero una tabla utilizable.");
      }

      const sheets = parsedSheets.map((sheet, index) => this.createSheetState(sheet, index));
      this.state = this.getInitialState();
      this.state.fileMeta = {
        name: file.name,
        extension,
        sizeLabel: formatBytes(file.size),
        iconClass: buildFileIcon(extension),
        activeSheetName: sheets[0].name,
        totalSheets: sheets.length,
        loaded: true,
      };
      this.state.datasetConfig.sheets = sheets;
      this.state.datasetConfig.selectedSheetId = sheets[0].id;
      this.state.datasetConfig.statusLabel = "Archivo cargado";
      this.state.queryState.tableName = sheets[0].tableName;
      this.buildSheetStructure(sheets[0], { keepAliases: false });
      this.state.datasetConfig.structureDirty = true;
      this.state.queryState.sql = this.buildSampleQuery(sheets[0].tableName);
      this.syncQueryStateWithSheet();
      if (this.screenMode === "landing") {
        await this.openWorkspaceRoute();
        return;
      }
      this.render();
    } catch (error) {
      this.state = this.getInitialState();
      this.state.globalError = error.message || "No se pudo procesar el archivo.";
      this.render();
    } finally {
      input.value = "";
    }
  }

  async parseFile(file, extension) {
    if (["xls", "xlsx", "xlsm"].includes(extension)) {
      return this.parseWorkbook(await file.arrayBuffer());
    }
    if (extension === "csv") {
      return [
        {
          name: file.name.replace(/\.[^.]+$/, "") || "dataset",
          rawRows: parseCsvText(await file.text()),
        },
      ];
    }
    if (extension === "json") {
      return [
        {
          name: file.name.replace(/\.[^.]+$/, "") || "dataset",
          rawRows: extractJsonRows(await file.text()),
        },
      ];
    }
    if (extension === "xml") {
      return [
        {
          name: file.name.replace(/\.[^.]+$/, "") || "dataset",
          rawRows: extractXmlRows(await file.text()),
        },
      ];
    }
    throw new Error("Formato no soportado. Usa csv, json, xml, xls, xlsx o xlsm.");
  }

  parseWorkbook(arrayBuffer) {
    if (!window.XLSX) {
      throw new Error("La libreria de hojas de calculo no esta disponible.");
    }
    const workbook = window.XLSX.read(arrayBuffer, { type: "array", cellDates: false });
    return workbook.SheetNames.map((sheetName) => ({
      name: sheetName,
      rawRows: window.XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], {
        header: 1,
        raw: false,
        defval: "",
        blankrows: true,
      }),
    }));
  }

  createSheetState(sheet, index) {
    const tableName = sanitizeIdentifier(sheet.name || `dataset_${index + 1}`, "dataset");
    const detectedStartRowIndex = this.detectHeaderRow(sheet.rawRows || []);
    const detectedHeaderRow = (sheet.rawRows || [])[detectedStartRowIndex] || [];
    const detectedStartColumnIndex = getFirstNonEmptyColumnIndex(detectedHeaderRow);
    const detectedEndColumnIndex = Math.max(
      detectedStartColumnIndex,
      getLastNonEmptyColumnIndex(detectedHeaderRow)
    );
    return {
      id: `${Date.now()}_${index}`,
      name: sheet.name || `Hoja ${index + 1}`,
      tableName,
      rawRows: cloneRows(sheet.rawRows || []),
      tableStartRowIndex: detectedStartRowIndex,
      tableStartColumnIndex: detectedStartColumnIndex,
      tableEndColumnIndex: detectedEndColumnIndex,
      columns: [],
      previewRows: [],
      dataRowsCount: 0,
      errors: [],
      structureApplied: false,
      structureDirty: true,
    };
  }

  detectHeaderRow(rawRows) {
    let bestIndex = 0;
    let bestScore = -1;
    rawRows.slice(0, HEADER_SCAN_LIMIT).forEach((row, index) => {
      const nonEmptyCells = row.filter((cell) => String(cell ?? "").trim() !== "").length;
      if (!nonEmptyCells) {
        return;
      }
      const score = nonEmptyCells + Math.min(buildRowSnippet(row).length / 40, 1);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = index;
      }
    });
    return bestIndex;
  }

  buildSheetStructure(sheet, { keepAliases }) {
    const headerRow = sheet.rawRows[sheet.tableStartRowIndex] || [];
    const startColumnIndex = Math.max(0, Number(sheet.tableStartColumnIndex || 0));
    const endColumnIndex = Math.max(startColumnIndex, Number(sheet.tableEndColumnIndex || startColumnIndex));
    const selectedColumnIndexes = Array.from(
      { length: endColumnIndex - startColumnIndex + 1 },
      (_, index) => startColumnIndex + index
    );
    const dataRows = sheet.rawRows
      .slice(sheet.tableStartRowIndex + 1)
      .filter((row) =>
        selectedColumnIndexes.some((columnIndex) => String(row[columnIndex] ?? "").trim() !== "")
      );
    const maxColumns = selectedColumnIndexes.length;
    const previousColumns = new Map((sheet.columns || []).map((column) => [column.index, column]));
    sheet.columns = Array.from({ length: maxColumns }).map((_, index) => {
      const sourceIndex = selectedColumnIndexes[index];
      const previous = previousColumns.get(sourceIndex);
      const originalLabel = String(headerRow[sourceIndex] ?? "").trim() || `Columna ${getColumnLabel(sourceIndex)}`;
      const sampleValues = dataRows.slice(0, 20).map((row) => row[sourceIndex]);
      return {
        index: sourceIndex,
        tablePosition: index,
        columnLabel: getColumnLabel(sourceIndex),
        originalLabel,
        use: previous ? previous.use : true,
        alias:
          keepAliases && previous
            ? previous.alias
            : sanitizeIdentifier(originalLabel, `column_${index + 1}`),
        type: previous?.type || inferColumnType(sampleValues),
      };
    });
    sheet.previewRows = dataRows.slice(0, PREVIEW_ROW_LIMIT);
    sheet.dataRowsCount = dataRows.length;
    sheet.errors = this.validateSheetStructure(sheet);
    sheet.structureDirty = true;
    this.state.datasetConfig.statusLabel = sheet.errors.length ? "Requiere ajustes" : "Pendiente de aplicar";
    this.state.datasetConfig.structureReady = false;
  }

  validateSheetStructure(sheet) {
    const errors = [];
    if (!sheet.rawRows.length) {
      errors.push("La hoja esta vacia.");
      return errors;
    }
    if (sheet.tableStartRowIndex < 0 || sheet.tableStartRowIndex >= sheet.rawRows.length) {
      errors.push("Configura una fila inicial valida para la tabla.");
    }
    if (sheet.tableStartColumnIndex < 0 || sheet.tableEndColumnIndex < sheet.tableStartColumnIndex) {
      errors.push("Configura un rango de columnas valido.");
    }
    const activeColumns = (sheet.columns || []).filter((column) => column.use);
    if (!activeColumns.length) {
      errors.push("Activa al menos una columna para construir el dataset.");
    }
    const aliases = activeColumns.map((column) =>
      sanitizeIdentifier(column.alias, `column_${column.index + 1}`)
    );
    if (aliases.some((alias) => !alias)) {
      errors.push("Todas las columnas activas deben tener un alias SQL.");
    }
    if (new Set(aliases).size !== aliases.length) {
      errors.push("Los alias SQL de las columnas activas deben ser unicos.");
    }
    return errors;
  }

  updateTableRange(key, value) {
    const sheet = this.selectedSheet;
    if (!sheet) {
      return;
    }
    sheet[key] = value;
    if (key === "tableStartColumnIndex" && sheet.tableEndColumnIndex < value) {
      sheet.tableEndColumnIndex = value;
    }
    if (key === "tableEndColumnIndex" && value < sheet.tableStartColumnIndex) {
      sheet.tableStartColumnIndex = value;
    }
    this.buildSheetStructure(sheet, { keepAliases: false });
    this.clearQueryResults();
    this.syncQueryStateWithSheet();
    this.render();
  }

  updateColumnSetting(index, key, value) {
    const sheet = this.selectedSheet;
    if (!sheet) {
      return;
    }
    const column = sheet.columns[index];
    if (!column) {
      return;
    }
    column[key] = value;
    sheet.errors = this.validateSheetStructure(sheet);
    sheet.structureDirty = true;
    sheet.structureApplied = false;
    this.state.datasetConfig.structureDirty = true;
    this.state.datasetConfig.structureReady = false;
    this.state.datasetConfig.statusLabel = sheet.errors.length ? "Requiere ajustes" : "Pendiente de aplicar";
    if (key !== "alias") {
      this.render();
    }
  }

  selectSheet(sheetId) {
    this.state.datasetConfig.selectedSheetId = sheetId;
    const sheet = this.selectedSheet;
    if (!sheet.columns.length) {
      this.buildSheetStructure(sheet, { keepAliases: false });
    }
    this.state.fileMeta.activeSheetName = sheet?.name || "";
    this.state.datasetConfig.structureReady = Boolean(
      sheet && sheet.structureApplied && !sheet.structureDirty && !sheet.errors.length
    );
    this.state.datasetConfig.structureDirty = Boolean(sheet?.structureDirty);
    this.state.datasetConfig.statusLabel = sheet?.errors.length
      ? "Requiere ajustes"
      : this.state.datasetConfig.structureReady
        ? "Dataset listo"
        : "Pendiente de aplicar";
    this.syncQueryStateWithSheet();
    this.clearQueryResults();
    this.render();
  }

  applyStructure(silent = false) {
    const sheet = this.selectedSheet;
    if (!sheet) {
      return;
    }
    try {
      sheet.errors = this.validateSheetStructure(sheet);
      if (sheet.errors.length) {
        this.state.datasetConfig.statusLabel = "Requiere ajustes";
        if (!silent) {
          this.render();
        }
        return;
      }
      this.registerSelectedSheet();
      sheet.structureApplied = true;
      sheet.structureDirty = false;
      this.state.datasetConfig.structureDirty = false;
      this.state.datasetConfig.structureReady = true;
      this.state.datasetConfig.statusLabel = "Dataset listo";
      this.state.queryState.tableName = sheet.tableName;
      if (!this.state.queryState.sql.trim()) {
        this.state.queryState.sql = this.buildSampleQuery(sheet.tableName);
      }
      if (!silent) {
        this.render();
      }
    } catch (error) {
      this.state.queryState.error = error.message || "No se pudo preparar el dataset temporal.";
      this.state.datasetConfig.statusLabel = "Requiere ajustes";
      if (!silent) {
        this.render();
      }
    }
  }

  buildDatasetRecords(sheet) {
    const activeColumns = sheet.columns.filter((column) => column.use);
    const selectedIndexes = sheet.columns.map((column) => column.index);
    return sheet.rawRows
      .slice(sheet.tableStartRowIndex + 1)
      .filter((row) =>
        selectedIndexes.some((columnIndex) => String(row[columnIndex] ?? "").trim() !== "")
      )
      .map((row) => {
        const record = {};
        activeColumns.forEach((column) => {
          const alias = sanitizeIdentifier(column.alias, `column_${column.index + 1}`);
          record[alias] = coerceValueByType(row[column.index], column.type);
        });
        return record;
      });
  }

  buildDatasetSignature(sheet) {
    return JSON.stringify({
      id: sheet.id,
      tableStartRowIndex: sheet.tableStartRowIndex,
      tableStartColumnIndex: sheet.tableStartColumnIndex,
      tableEndColumnIndex: sheet.tableEndColumnIndex,
      columns: sheet.columns.map((column) => ({
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

  registerSelectedSheet() {
    const sheet = this.selectedSheet;
    if (!sheet) {
      return;
    }
    if (!window.alasql) {
      throw new Error("La libreria SQL no esta disponible.");
    }
    const signature = this.buildDatasetSignature(sheet);
    if (this.registeredTableName === sheet.tableName && this.lastRegisteredSignature === signature) {
      return;
    }
    this.dropRegisteredTable();
    const records = this.buildDatasetRecords(sheet);
    window.alasql(`CREATE TABLE ${quoteSqlIdentifier(sheet.tableName)}`);
    window.alasql.tables[sheet.tableName].data = records;
    this.registeredTableName = sheet.tableName;
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

  loadSampleQuery() {
    this.state.queryState.sql = this.buildSampleQuery(this.activeTableName);
    this.render();
  }

  buildSampleQuery(tableName) {
    return `SELECT *\nFROM ${quoteSqlIdentifier(tableName)}\nLIMIT 20;`;
  }

  syncQueryStateWithSheet() {
    const sheet = this.selectedSheet;
    this.state.queryState.tableName = sheet?.tableName || "";
    if (!this.state.queryState.sql.trim() || this.state.queryState.sql.includes("FROM [")) {
      this.state.queryState.sql = sheet ? this.buildSampleQuery(sheet.tableName) : "";
    }
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

  runQuery() {
    const queryError = this.validateReadOnlyQuery(this.state.queryState.sql);
    if (queryError) {
      this.state.queryState.error = queryError;
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
      this.state.queryState.rows.some((row) => toChartNumber(row[column]) !== null)
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
      const option = this.buildChartOption(chartData);
      this.chartInstance.setOption(option, true);
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
      toolbox: {
        right: 0,
        feature: { saveAsImage: {} },
      },
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
      !window.confirm("Se eliminara el archivo temporal, la consulta y los resultados. Deseas continuar?")
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
    return `
      <div class="zrn_processing_landing">
        <section class="zrn_processing_panel">
          <div class="zrn_processing_panel_head">
            <strong>Carga de archivo</strong>
            <span>Un archivo temporal por sesion</span>
          </div>
          <div class="zrn_processing_panel_body">
            <label class="zrn_processing_dropzone zrn_processing_dropzone_main">
              <input type="file" data-action="file" accept=".csv,.json,.xml,.xls,.xlsx,.xlsm" />
              <span class="zrn_processing_dropzone_icon"><i class="fa fa-upload"></i></span>
              <strong>Cargar archivo para procesar</strong>
              <span>Al cargarlo se abrira el workspace de queries, resultados y graficas.</span>
            </label>
            <div class="zrn_processing_hint_strip">
              Formatos permitidos: csv, json, xml, xls, xlsx, xlsm.
            </div>
          </div>
        </section>
      </div>
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
    const activeColumns = sheet?.columns.filter((column) => column.use) || [];
    const tableName = sheet?.tableName || "dataset";
    const resultColumns = this.state.queryState.columns;
    const resultRows = this.state.queryState.rows;
    const numericResultColumns = resultColumns.filter((column) =>
      resultRows.some((row) => toChartNumber(row[column]) !== null)
    );
    const resultTabs = [
      ["table", "Tabla"],
      ["json", "JSON"],
      ["chart", "Grafica"],
    ];

    const overviewStatusClass = sheet?.errors.length
      ? "is-danger"
      : this.state.datasetConfig.structureReady
        ? "is-ready"
        : this.state.fileMeta.loaded
          ? "is-pending"
          : "";

    const maxSheetColumns = sheet
      ? Math.max(...sheet.rawRows.map((row) => row.length), 0)
      : 0;
    const startColumnOptions = sheet
      ? Array.from({ length: maxSheetColumns }, (_, index) => {
          const rowLabel = sheet.rawRows[sheet.tableStartRowIndex]?.[index];
          const optionLabel = rowLabel
            ? `${getColumnLabel(index)} / ${String(rowLabel).trim().slice(0, 36)}`
            : getColumnLabel(index);
          return `<option value="${index}" ${index === sheet.tableStartColumnIndex ? "selected" : ""}>${escapeHtml(
            optionLabel
          )}</option>`;
        }).join("")
      : "";
    const endColumnOptions = sheet
      ? Array.from({ length: maxSheetColumns }, (_, index) => {
          const rowLabel = sheet.rawRows[sheet.tableStartRowIndex]?.[index];
          const optionLabel = rowLabel
            ? `${getColumnLabel(index)} / ${String(rowLabel).trim().slice(0, 36)}`
            : getColumnLabel(index);
          return `<option value="${index}" ${index === sheet.tableEndColumnIndex ? "selected" : ""}>${escapeHtml(
            optionLabel
          )}</option>`;
        }).join("")
      : "";
    const rangeLabel = sheet
      ? `${getColumnLabel(sheet.tableStartColumnIndex)}:${getColumnLabel(sheet.tableEndColumnIndex)}`
      : "-";
    const previewStartLabel = sheet ? sheet.tableStartRowIndex + 1 : "-";
    const dataStartLabel = sheet ? sheet.tableStartRowIndex + 2 : "-";
    const isSpreadsheet = ["xls", "xlsx", "xlsm"].includes(this.state.fileMeta.extension);

    const columnRows = sheet
      ? sheet.columns
          .map(
            (column, index) => `
              <tr>
                <td><input type="checkbox" data-action="column-use" data-column-index="${index}" ${column.use ? "checked" : ""} /></td>
                <td>${escapeHtml(column.columnLabel)} / ${escapeHtml(column.originalLabel)}</td>
                <td>
                  <input
                    type="text"
                    class="form-control"
                    data-action="column-alias"
                    data-column-index="${index}"
                    value="${escapeHtml(column.alias)}"
                  />
                </td>
                <td>
                  <select class="form-select" data-action="column-type" data-column-index="${index}">
                    ${SQL_TYPES.map(
                      (type) => `<option value="${type}" ${column.type === type ? "selected" : ""}>${type}</option>`
                    ).join("")}
                  </select>
                </td>
              </tr>
            `
          )
          .join("")
      : "";

    const fileDetailRows = this.state.fileMeta.loaded
      ? `
          <tr><th>Archivo</th><td>${escapeHtml(this.state.fileMeta.name)}</td></tr>
          <tr><th>Formato</th><td>${escapeHtml(this.state.fileMeta.extension.toUpperCase())}</td></tr>
          <tr><th>Hoja activa</th><td>${escapeHtml(this.state.fileMeta.activeSheetName || "-")}</td></tr>
          <tr><th>Tabla SQL</th><td><code>${escapeHtml(tableName)}</code></td></tr>
          <tr><th>Fila de encabezado</th><td>${previewStartLabel}</td></tr>
          <tr><th>Columnas</th><td>${escapeHtml(rangeLabel)}</td></tr>
          <tr><th>Datos desde</th><td>Fila ${dataStartLabel}</td></tr>
          <tr><th>Filas detectadas</th><td>${sheet?.dataRowsCount || 0}</td></tr>
          <tr><th>Columnas activas</th><td>${activeColumns.length}</td></tr>
          <tr><th>Estado</th><td>${escapeHtml(this.state.datasetConfig.statusLabel)}</td></tr>
        `
      : "";

    const previewHead = activeColumns.map((column) => `<th>${escapeHtml(column.alias)}</th>`).join("");
    const previewRows = sheet
      ? sheet.previewRows
          .map((row) => {
            const cells = activeColumns
              .map((column) => `<td>${escapeHtml(row[column.index] ?? "")}</td>`)
              .join("");
            return `<tr>${cells}</tr>`;
          })
          .join("")
      : "";

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
        `
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
                      `<option value="${escapeHtml(column)}" ${this.state.chartState.categoryColumn === column ? "selected" : ""}>${escapeHtml(column)}</option>`
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
                      `<option value="${escapeHtml(column)}" ${this.state.chartState.valueColumn === column ? "selected" : ""}>${escapeHtml(column)}</option>`
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
                      `<option value="${aggregate}" ${this.state.chartState.aggregate === aggregate ? "selected" : ""}>${aggregate.toUpperCase()}</option>`
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
          ? `<div class="zrn_processing_result_json_wrap"><pre class="zrn_processing_result_json">${escapeHtml(
              this.state.queryState.json
            )}</pre></div>`
          : '<div class="zrn_processing_result_empty">Ejecuta una consulta para ver el JSON.</div>'
        : this.state.queryState.activeView === "chart"
          ? `
              ${chartConfig}
              ${
                chartPreview?.error
                  ? `<div class="zrn_processing_query_error">${escapeHtml(chartPreview.error)}</div>`
                  : ""
              }
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

    this.root.innerHTML = `
      <div class="zrn_processing_app">
        ${
          this.state.globalError
            ? `<div class="zrn_processing_global_error">${escapeHtml(this.state.globalError)}</div>`
            : ""
        }
        ${
          !this.state.fileMeta.loaded
            ? `
              <section class="zrn_processing_panel">
                <div class="zrn_processing_panel_head">
                  <strong>Carga pendiente</strong>
                  <span>Sin archivo activo</span>
                </div>
                <div class="zrn_processing_panel_body">
                  <div class="zrn_processing_empty_state">
                    <div class="zrn_processing_empty">No hay archivo temporal cargado en esta sesion.</div>
                  </div>
                </div>
              </section>
            `
            : `
              <section class="zrn_processing_panel zrn_processing_overview_panel">
                <div class="zrn_processing_panel_head">
                  <strong>Resumen del archivo</strong>
                  <span>Un archivo activo por sesion</span>
                </div>
                <div class="zrn_processing_panel_body">
                  <div class="zrn_processing_overview_top">
                    <div class="zrn_processing_file_overview">
                      <div class="zrn_processing_file_icon">
                        <i class="fa ${escapeHtml(this.state.fileMeta.iconClass)}"></i>
                      </div>
                      <div class="zrn_processing_file_copy">
                        <div class="zrn_processing_file_name">${escapeHtml(this.state.fileMeta.name)}</div>
                        <div class="zrn_processing_helper">
                          ${escapeHtml(this.state.fileMeta.extension.toUpperCase())} / ${escapeHtml(this.state.fileMeta.sizeLabel)} / ${this.state.fileMeta.totalSheets} origen(es)
                        </div>
                      </div>
                    </div>
                    <div class="zrn_processing_file_actions">
                      <label class="btn btn-secondary zrn_processing_replace_btn">
                        Reemplazar archivo
                        <input type="file" data-action="file" accept=".csv,.json,.xml,.xls,.xlsx,.xlsm" />
                      </label>
                      <button type="button" class="btn btn-secondary" data-action="reset-file">Limpiar sesion</button>
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
                            `
                          )
                          .join("")}
                      </select>
                    </div>
                    <div class="zrn_processing_field">
                      <label>Tabla SQL</label>
                      <input type="text" class="form-control" value="${escapeHtml(tableName)}" disabled="disabled" />
                    </div>
                  </div>
                  <div class="zrn_processing_file_details_wrap">
                    <table class="o_list_table table table-sm zrn_processing_file_details_table">
                      <tbody>${fileDetailRows}</tbody>
                    </table>
                  </div>
                </div>
              </section>

              <section class="zrn_processing_panel">
                <div class="zrn_processing_panel_head">
                  <strong>Dataset temporal</strong>
                  <span>${sheet ? `${sheet.dataRowsCount} filas detectadas` : "Sin estructura"}</span>
                </div>
                <div class="zrn_processing_panel_body">
                  ${
                    sheet
                      ? `
                        ${
                          sheet.errors.length
                            ? `<div class="zrn_processing_sheet_errors">${sheet.errors.map((error) => escapeHtml(error)).join("<br/>")}</div>`
                            : ""
                        }
                        <div class="zrn_processing_range_grid">
                          <div class="zrn_processing_field">
                            <label>Fila de encabezado</label>
                            <input
                              type="number"
                              min="1"
                              max="${sheet.rawRows.length || 1}"
                              class="form-control"
                              data-action="table-start-row"
                              value="${previewStartLabel}"
                            />
                            <div class="zrn_processing_field_hint">
                              ${
                                isSpreadsheet
                                  ? "Para Excel puedes indicar la fila real donde empiezan los encabezados, por ejemplo la 18."
                                  : "Configura la fila que contiene los encabezados del dataset temporal."
                              }
                            </div>
                          </div>
                          <div class="zrn_processing_field">
                            <label>Estado</label>
                            <div class="zrn_processing_status_inline ${overviewStatusClass}">${escapeHtml(this.state.datasetConfig.statusLabel)}</div>
                          </div>
                          <div class="zrn_processing_field">
                            <label>Columna inicial</label>
                            <select class="form-select" data-action="table-start-column">${startColumnOptions}</select>
                          </div>
                          <div class="zrn_processing_field">
                            <label>Columna final</label>
                            <select class="form-select" data-action="table-end-column">${endColumnOptions}</select>
                          </div>
                        </div>
                        <div class="zrn_processing_actions">
                          <button type="button" class="btn btn-primary" data-action="apply-structure">Aplicar estructura</button>
                          <button type="button" class="btn btn-secondary" data-action="sample-query">Cargar query base</button>
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
                      : '<div class="zrn_processing_empty">Carga un archivo para definir columnas y tipos.</div>'
                  }
                </div>
              </section>

              <section class="zrn_processing_panel">
                <div class="zrn_processing_panel_head">
                  <strong>Preview estructural</strong>
                  <span>Rango ${escapeHtml(rangeLabel)} desde fila ${previewStartLabel}</span>
                </div>
                <div class="zrn_processing_panel_body">
                  ${
                    sheet && activeColumns.length
                      ? `
                        <div class="zrn_processing_preview_wrap">
                          <table class="o_list_table table table-sm zrn_processing_preview_table">
                            <thead><tr>${previewHead}</tr></thead>
                            <tbody>${previewRows}</tbody>
                          </table>
                        </div>
                      `
                      : '<div class="zrn_processing_empty">Aplica estructura para revisar el preview del dataset.</div>'
                  }
                </div>
              </section>

              <section class="zrn_processing_panel">
                <div class="zrn_processing_panel_head">
                  <strong>Editor SQL</strong>
                  <span>Solo lectura: SELECT, WHERE, GROUP BY, ORDER BY y LIMIT</span>
                </div>
                <div class="zrn_processing_panel_body">
                  <div class="zrn_processing_query_hint">
                    Tabla disponible: <code>${escapeHtml(this.state.queryState.tableName || "dataset")}</code>. Se usan todas las filas hacia abajo dentro del rango ${escapeHtml(rangeLabel)}.
                  </div>
                  <textarea class="zrn_processing_query_area" data-action="sql-input" placeholder="SELECT * FROM [dataset] LIMIT 20;">${escapeHtml(
                    this.state.queryState.sql
                  )}</textarea>
                  <div class="zrn_processing_query_actions">
                    <button
                      type="button"
                      class="btn btn-primary"
                      data-action="run-query"
                      ${this.state.fileMeta.loaded ? "" : "disabled"}
                    >
                      ${this.state.queryState.running ? "Ejecutando..." : "Ejecutar"}
                    </button>
                    <div class="zrn_processing_helper">La estructura del dataset se aplica al ejecutar si aun esta pendiente.</div>
                  </div>
                  ${
                    this.state.queryState.error
                      ? `<div class="zrn_processing_query_error">${escapeHtml(this.state.queryState.error)}</div>`
                      : ""
                  }
                </div>
              </section>

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

              <section class="zrn_processing_panel">
                <div class="zrn_processing_panel_head">
                  <strong>Ayuda SQL</strong>
                  <span>Referencia rapida</span>
                </div>
                <div class="zrn_processing_panel_body">
                  <ul class="zrn_processing_table_list">
                    <li><strong>Tabla:</strong> <code>${escapeHtml(this.state.queryState.tableName || "dataset")}</code></li>
                    <li><strong>Permitido:</strong> SELECT, WHERE, GROUP BY, ORDER BY, LIMIT</li>
                    <li><strong>Agregados:</strong> COUNT, SUM, AVG, MIN, MAX</li>
                    <li><strong>No permitido:</strong> INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, ATTACH</li>
                  </ul>
                </div>
              </section>
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
