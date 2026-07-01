/** @odoo-module **/

const HEADER_SCAN_LIMIT = 25;
const PREVIEW_ROW_LIMIT = 8;
const QUERY_RESULT_LIMIT = 200;
const SQL_TYPES = ["text", "number", "date", "boolean"];

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

function buildRowSnippet(row) {
  return row
    .slice(0, 5)
    .map((cell) => String(cell ?? "").trim())
    .filter(Boolean)
    .join(" | ");
}

function isRowEmpty(row = []) {
  return !row.some((cell) => String(cell ?? "").trim() !== "");
}

function inferColumnType(values) {
  for (const rawValue of values) {
    const value = String(rawValue ?? "").trim();
    if (!value) {
      continue;
    }
    if (/^(true|false|si|no)$/i.test(value)) {
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
  const header = columns;
  const rows = records.map((record) =>
    columns.map((column) => normalizeCellValue(record?.[column]))
  );
  return [header, ...rows];
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
    const arrayEntry = Object.values(payload).find(
      (value) =>
        Array.isArray(value) &&
        value.every((item) => item && typeof item === "object" && !Array.isArray(item))
    );
    if (arrayEntry) {
      return buildRowsFromObjects(arrayEntry);
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
  const records = rowNodes.map((node) => {
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
  });
  return buildRowsFromObjects(records);
}

function coerceValueByType(value, type) {
  const normalized = String(value ?? "").trim();
  if (!normalized) {
    return null;
  }
  if (type === "number") {
    const parsed = Number(normalized.replace(/,/g, ""));
    return Number.isNaN(parsed) ? normalized : parsed;
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
  if (type === "date") {
    return normalized;
  }
  return normalized;
}

export class ZrnAnalyticsProcessingView {
  constructor() {
    this.root = null;
    this.state = this.getInitialState();
    this.boundHandleRootEvent = this.handleRootEvent.bind(this);
    this.boundBeforeUnload = this.handleBeforeUnload.bind(this);
    this.boundDocumentClick = this.handleDocumentClick.bind(this);
    this.listenersAttached = false;
    this.registeredTables = [];
  }

  getInitialState() {
    return {
      fileName: "",
      fileExtension: "",
      sheets: [],
      selectedSheetId: "",
      sqlQuery: "",
      queryColumns: [],
      queryRows: [],
      queryJson: "",
      queryError: "",
      globalError: "",
      resultCount: 0,
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
    this.root.innerHTML = "";
    this.root = null;
  }

  destroy() {
    this.unmount();
    this.dropRegisteredTables();
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
    return Boolean(this.state.fileName || this.state.sqlQuery.trim() || this.state.sheets.length);
  }

  async confirmDiscardIfNeeded() {
    if (!this.hasTransientData) {
      return true;
    }
    return window.confirm(
      "El archivo cargado y las consultas temporales se perderan al salir de esta pantalla. Deseas continuar?"
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
    if (!this.root || !this.hasTransientData) {
      return;
    }
    if (!(event.target instanceof Element)) {
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
      "El dataset temporal se perdera si sales o cambias de pantalla. Deseas continuar?"
    );
    if (!canLeave) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
    }
  }

  get selectedSheet() {
    return this.state.sheets.find((sheet) => sheet.id === this.state.selectedSheetId) || null;
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
    if (action === "sheet-select" && event.type === "change") {
      this.state.selectedSheetId = source.value;
      this.state.queryError = "";
      this.render();
      return;
    }
    if (action === "header-row" && event.type === "change") {
      const sheet = this.selectedSheet;
      if (!sheet) {
        return;
      }
      sheet.headerRowIndex = Number(source.value || 0);
      this.buildSheetStructure(sheet, { keepAliases: false });
      this.state.queryError = "";
      this.render();
      return;
    }
    if (action === "apply-structure" && event.type === "click") {
      event.preventDefault();
      this.rebuildSelectedSheet();
      return;
    }
    if (action === "reset-file" && event.type === "click") {
      event.preventDefault();
      this.resetAll();
      return;
    }
    if (action === "sql-input" && event.type === "input") {
      this.state.sqlQuery = source.value;
      return;
    }
    if (action === "sample-query" && event.type === "click") {
      event.preventDefault();
      const selectedSheet = this.selectedSheet;
      if (!selectedSheet) {
        return;
      }
      this.state.sqlQuery = `SELECT *\nFROM ${quoteSqlIdentifier(selectedSheet.tableName)}\nLIMIT 20;`;
      this.render();
      return;
    }
    if (action === "run-query" && event.type === "click") {
      event.preventDefault();
      this.runQuery();
      return;
    }
    if (action === "column-use" && event.type === "change") {
      const sheet = this.selectedSheet;
      if (!sheet) {
        return;
      }
      const column = sheet.columns[Number(source.dataset.columnIndex)];
      column.use = Boolean(source.checked);
      sheet.errors = this.validateSheetStructure(sheet);
      this.render();
      return;
    }
    if (action === "column-alias" && event.type === "input") {
      const sheet = this.selectedSheet;
      if (!sheet) {
        return;
      }
      const column = sheet.columns[Number(source.dataset.columnIndex)];
      column.alias = sanitizeIdentifier(source.value, `column_${column.index + 1}`);
      sheet.errors = this.validateSheetStructure(sheet);
      return;
    }
    if (action === "column-type" && event.type === "change") {
      const sheet = this.selectedSheet;
      if (!sheet) {
        return;
      }
      const column = sheet.columns[Number(source.dataset.columnIndex)];
      column.type = source.value;
      return;
    }
  }

  async handleFileSelection(input) {
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    try {
      this.dropRegisteredTables();
      const extension = (file.name.split(".").pop() || "").toLowerCase();
      const sheets = await this.parseFile(file, extension);
      if (!sheets.length) {
        throw new Error("El archivo no genero ninguna tabla utilizable.");
      }
      const usedNames = new Set();
      this.state.fileName = file.name;
      this.state.fileExtension = extension;
      this.state.sheets = sheets.map((sheet, index) => {
        const baseTableName = sanitizeIdentifier(sheet.name || `dataset_${index + 1}`, `dataset_${index + 1}`);
        let tableName = baseTableName;
        let suffix = 2;
        while (usedNames.has(tableName)) {
          tableName = `${baseTableName}_${suffix}`;
          suffix += 1;
        }
        usedNames.add(tableName);
        const enrichedSheet = {
          ...sheet,
          id: `${Date.now()}_${index}`,
          tableName,
          headerRowIndex: this.detectHeaderRow(sheet.rawRows),
          columns: [],
          errors: [],
          previewRows: [],
          dataRows: [],
        };
        this.buildSheetStructure(enrichedSheet, { keepAliases: false });
        return enrichedSheet;
      });
      this.state.selectedSheetId = this.state.sheets[0].id;
      this.state.sqlQuery = `SELECT *\nFROM ${quoteSqlIdentifier(this.state.sheets[0].tableName)}\nLIMIT 20;`;
      this.state.queryColumns = [];
      this.state.queryRows = [];
      this.state.queryJson = "";
      this.state.queryError = "";
      this.state.globalError = "";
      this.state.resultCount = 0;
      this.registerTables();
      this.render();
    } catch (error) {
      this.state = {
        ...this.getInitialState(),
        globalError: error.message || "No se pudo procesar el archivo.",
      };
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

  detectHeaderRow(rawRows) {
    let bestIndex = 0;
    let bestScore = -1;
    const scanRows = rawRows.slice(0, HEADER_SCAN_LIMIT);
    scanRows.forEach((row, index) => {
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
    const rawRows = sheet.rawRows || [];
    const headerRow = rawRows[sheet.headerRowIndex] || [];
    const trailingRows = rawRows.slice(sheet.headerRowIndex + 1).filter((row) => !isRowEmpty(row));
    const maxColumns = Math.max(
      headerRow.length,
      ...trailingRows.slice(0, PREVIEW_ROW_LIMIT).map((row) => row.length),
      0
    );
    const previousColumns = new Map(
      (sheet.columns || []).map((column) => [column.index, column])
    );
    sheet.columns = Array.from({ length: maxColumns }).map((_, index) => {
      const previous = previousColumns.get(index);
      const originalLabel = String(headerRow[index] ?? "").trim() || `Columna ${index + 1}`;
      const sampleValues = trailingRows.slice(0, 15).map((row) => row[index]);
      const aliasBase = sanitizeIdentifier(originalLabel, `column_${index + 1}`);
      return {
        index,
        originalLabel,
        use: previous ? previous.use : true,
        alias:
          keepAliases && previous
            ? sanitizeIdentifier(previous.alias, aliasBase)
            : aliasBase,
        type: previous?.type || inferColumnType(sampleValues),
      };
    });
    sheet.previewRows = trailingRows.slice(0, PREVIEW_ROW_LIMIT);
    sheet.dataRows = trailingRows;
    sheet.errors = this.validateSheetStructure(sheet);
  }

  validateSheetStructure(sheet) {
    const errors = [];
    if (!sheet.rawRows.length) {
      errors.push("La hoja esta vacia.");
      return errors;
    }
    if (sheet.headerRowIndex < 0 || sheet.headerRowIndex >= sheet.rawRows.length) {
      errors.push("Selecciona una fila de encabezado valida.");
    }
    const activeColumns = (sheet.columns || []).filter((column) => column.use);
    if (!activeColumns.length) {
      errors.push("Activa al menos una columna para construir el dataset.");
    }
    const aliases = activeColumns.map((column) => column.alias).filter(Boolean);
    if (aliases.length !== activeColumns.length) {
      errors.push("Todas las columnas activas deben tener un alias SQL.");
    }
    if (new Set(aliases).size !== aliases.length) {
      errors.push("Los alias de columnas activas deben ser unicos.");
    }
    return errors;
  }

  rebuildSelectedSheet() {
    const sheet = this.selectedSheet;
    if (!sheet) {
      return;
    }
    this.buildSheetStructure(sheet, { keepAliases: true });
    this.registerTables();
    this.state.queryError = "";
    this.render();
  }

  buildDatasetRows(sheet) {
    if (sheet.errors.length) {
      return [];
    }
    const activeColumns = sheet.columns.filter((column) => column.use);
    return sheet.dataRows.map((row) => {
      const record = {};
      activeColumns.forEach((column) => {
        record[column.alias] = coerceValueByType(row[column.index], column.type);
      });
      return record;
    });
  }

  dropRegisteredTables() {
    if (!window.alasql) {
      this.registeredTables = [];
      return;
    }
    for (const tableName of this.registeredTables) {
      try {
        window.alasql(`DROP TABLE IF EXISTS ${quoteSqlIdentifier(tableName)}`);
      } catch {
        // Ignore leftover temp tables from prior states.
      }
    }
    this.registeredTables = [];
  }

  registerTables() {
    if (!window.alasql) {
      this.state.globalError = "La libreria SQL no esta disponible.";
      return;
    }
    this.dropRegisteredTables();
    for (const sheet of this.state.sheets) {
      if (sheet.errors.length) {
        continue;
      }
      const rows = this.buildDatasetRows(sheet);
      window.alasql(`CREATE TABLE ${quoteSqlIdentifier(sheet.tableName)}`);
      window.alasql.tables[sheet.tableName].data = rows;
      this.registeredTables.push(sheet.tableName);
    }
  }

  runQuery() {
    if (!window.alasql) {
      this.state.queryError = "La libreria SQL no esta disponible.";
      this.render();
      return;
    }
    this.registerTables();
    if (!this.registeredTables.length) {
      this.state.queryError = "No hay tablas validas disponibles para consultar.";
      this.state.queryColumns = [];
      this.state.queryRows = [];
      this.state.queryJson = "";
      this.state.resultCount = 0;
      this.render();
      return;
    }
    try {
      const rawResult = window.alasql(this.state.sqlQuery);
      const resultRows = Array.isArray(rawResult)
        ? rawResult.slice(0, QUERY_RESULT_LIMIT)
        : [{ resultado: rawResult }];
      this.state.queryColumns = resultRows.length ? Object.keys(resultRows[0]) : [];
      this.state.queryRows = resultRows;
      this.state.queryJson = JSON.stringify(resultRows, null, 2);
      this.state.resultCount = Array.isArray(rawResult) ? rawResult.length : 1;
      this.state.queryError = "";
      this.render();
    } catch (error) {
      this.state.queryError = error.message || "La consulta no pudo ejecutarse.";
      this.state.queryColumns = [];
      this.state.queryRows = [];
      this.state.queryJson = "";
      this.state.resultCount = 0;
      this.render();
    }
  }

  resetAll() {
    if (
      this.hasTransientData &&
      !window.confirm("Se eliminara el archivo temporal y la consulta actual. Deseas continuar?")
    ) {
      return;
    }
    this.dropRegisteredTables();
    this.state = this.getInitialState();
    this.render();
  }

  render() {
    if (!this.root) {
      return;
    }
    const selectedSheet = this.selectedSheet;
    const tableList = this.state.sheets.length
      ? this.state.sheets
          .map(
            (sheet) => `
              <li>
                <span class="zrn_processing_table_name">${escapeHtml(sheet.tableName)}</span>
                <span class="zrn_processing_table_rows">${sheet.dataRows.length} filas base</span>
              </li>
            `
          )
          .join("")
      : '<div class="zrn_processing_empty">Carga un archivo para crear tablas temporales.</div>';

    const headerOptions = selectedSheet
      ? selectedSheet.rawRows
          .slice(0, HEADER_SCAN_LIMIT)
          .map(
            (row, index) => `
              <option value="${index}" ${selectedSheet.headerRowIndex === index ? "selected" : ""}>
                Fila ${index + 1}: ${escapeHtml(buildRowSnippet(row) || "(sin contenido)")}
              </option>
            `
          )
          .join("")
      : "";

    const columnRows = selectedSheet
      ? selectedSheet.columns
          .map(
            (column, index) => `
              <tr>
                <td><input type="checkbox" data-action="column-use" data-column-index="${index}" ${
                  column.use ? "checked" : ""
                } /></td>
                <td>${escapeHtml(column.originalLabel)}</td>
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

    const previewHead = selectedSheet?.columns
      .filter((column) => column.use)
      .map((column) => `<th>${escapeHtml(column.alias)}</th>`)
      .join("");
    const previewRows = selectedSheet
      ? selectedSheet.previewRows
          .map((row) => {
            const cells = selectedSheet.columns
              .filter((column) => column.use)
              .map((column) => `<td>${escapeHtml(row[column.index] ?? "")}</td>`)
              .join("");
            return `<tr>${cells}</tr>`;
          })
          .join("")
      : "";

    const resultHead = this.state.queryColumns
      .map((column) => `<th>${escapeHtml(column)}</th>`)
      .join("");
    const resultRows = this.state.queryRows
      .map((row) => {
        const cells = this.state.queryColumns
          .map((column) => `<td>${escapeHtml(row[column] ?? "")}</td>`)
          .join("");
        return `<tr>${cells}</tr>`;
      })
      .join("");
    const resultJson = this.state.queryJson
      ? escapeHtml(this.state.queryJson)
      : "";

    this.root.innerHTML = `
      <div class="zrn_processing_app">
        ${this.state.globalError ? `<div class="zrn_processing_global_error">${escapeHtml(this.state.globalError)}</div>` : ""}
        <div class="zrn_processing_grid">
          <div class="zrn_processing_main">
            <section class="zrn_processing_panel">
              <div class="zrn_processing_panel_head">
                <strong>Carga de archivo</strong>
                <span>Soporta csv, json, xml, xls, xlsx y xlsm</span>
              </div>
              <div class="zrn_processing_panel_body">
                <div class="zrn_processing_field_grid">
                  <div class="zrn_processing_field">
                    <label>Archivo local</label>
                    <input
                      type="file"
                      class="form-control"
                      data-action="file"
                      accept=".csv,.json,.xml,.xls,.xlsx,.xlsm"
                    />
                    <div class="zrn_processing_field_hint">
                      ${this.state.fileName ? `Cargado: ${escapeHtml(this.state.fileName)}` : "El archivo no se almacena en Odoo."}
                    </div>
                  </div>
                  <div class="zrn_processing_field">
                    <label>Hoja o tabla activa</label>
                    <select class="form-select" data-action="sheet-select" ${selectedSheet ? "" : "disabled"}>
                      ${(this.state.sheets || [])
                        .map(
                          (sheet) => `
                            <option value="${sheet.id}" ${this.state.selectedSheetId === sheet.id ? "selected" : ""}>
                              ${escapeHtml(sheet.name)}
                            </option>
                          `
                        )
                        .join("")}
                    </select>
                    <div class="zrn_processing_field_hint">
                      ${selectedSheet ? `Tabla SQL: ${escapeHtml(selectedSheet.tableName)}` : "Crea al menos una tabla temporal para consultar."}
                    </div>
                  </div>
                </div>
                <div class="zrn_processing_actions">
                  <button type="button" class="btn btn-primary" data-action="sample-query" ${selectedSheet ? "" : "disabled"}>
                    Cargar query base
                  </button>
                  <button type="button" class="btn btn-secondary" data-action="reset-file" ${this.hasTransientData ? "" : "disabled"}>
                    Limpiar sesion
                  </button>
                </div>
              </div>
            </section>

            <section class="zrn_processing_panel">
              <div class="zrn_processing_panel_head">
                <strong>Definicion de dataset</strong>
                <span>Selecciona encabezado, columnas y tipos antes de consultar</span>
              </div>
              <div class="zrn_processing_panel_body">
                ${
                  selectedSheet
                    ? `
                      <div class="zrn_processing_sheet_note">
                        Ajusta la fila de cabecera para archivos con lineas informativas antes del dataset, como el ejemplo de Retail Link.
                      </div>
                      ${
                        selectedSheet.errors.length
                          ? `<div class="zrn_processing_sheet_errors">${selectedSheet.errors
                              .map((error) => escapeHtml(error))
                              .join("<br/>")}</div>`
                          : ""
                      }
                      <div class="zrn_processing_field_grid">
                        <div class="zrn_processing_field">
                          <label>Fila de encabezado</label>
                          <select class="form-select" data-action="header-row">
                            ${headerOptions}
                          </select>
                        </div>
                        <div class="zrn_processing_field">
                          <label>Tabla SQL expuesta</label>
                          <input type="text" class="form-control" value="${escapeHtml(selectedSheet.tableName)}" disabled="disabled" />
                        </div>
                      </div>
                      <div class="zrn_processing_actions">
                        <button type="button" class="btn btn-primary" data-action="apply-structure">
                          Aplicar estructura
                        </button>
                      </div>
                      <div class="zrn_processing_columns_wrap">
                        <table class="zrn_processing_columns">
                          <thead>
                            <tr>
                              <th>Usar</th>
                              <th>Origen</th>
                              <th>Alias SQL</th>
                              <th>Tipo</th>
                            </tr>
                          </thead>
                          <tbody>
                            ${columnRows}
                          </tbody>
                        </table>
                      </div>
                    `
                    : '<div class="zrn_processing_empty">Carga un archivo para definir columnas y alias del dataset.</div>'
                }
              </div>
            </section>

            <section class="zrn_processing_panel">
              <div class="zrn_processing_panel_head">
                <strong>Editor SQL</strong>
                <span>Consulta en memoria las tablas temporales cargadas</span>
              </div>
              <div class="zrn_processing_panel_body">
                <textarea class="zrn_processing_query_area" data-action="sql-input" placeholder="SELECT * FROM [dataset] LIMIT 20;">${escapeHtml(
                  this.state.sqlQuery
                )}</textarea>
                <div class="zrn_processing_query_actions">
                  <button type="button" class="btn btn-primary" data-action="run-query" ${
                    this.registeredTables.length ? "" : "disabled"
                  }>
                    Ejecutar query
                  </button>
                  <div class="zrn_processing_helper">Usa los nombres SQL listados en la derecha o la tabla activa seleccionada.</div>
                </div>
                ${
                  this.state.queryError
                    ? `<div class="zrn_processing_query_error">${escapeHtml(this.state.queryError)}</div>`
                    : ""
                }
                <div class="zrn_processing_result_meta">
                  <span><strong>Resultados</strong> ${this.state.resultCount} fila(s)</span>
                  <span>Preview maximo: ${QUERY_RESULT_LIMIT}</span>
                </div>
                <div class="zrn_processing_result_views">
                  <div class="zrn_processing_result_panel">
                    <div class="zrn_processing_result_head">Vista tabla</div>
                    <div class="zrn_processing_result_wrap">
                      ${
                        this.state.queryColumns.length
                          ? `
                            <table class="zrn_processing_result_table">
                              <thead><tr>${resultHead}</tr></thead>
                              <tbody>${resultRows}</tbody>
                            </table>
                          `
                          : '<div class="zrn_processing_result_empty">Ejecuta una consulta para ver resultados.</div>'
                      }
                    </div>
                  </div>
                  <div class="zrn_processing_result_panel">
                    <div class="zrn_processing_result_head">Vista JSON</div>
                    <div class="zrn_processing_result_json_wrap">
                      ${
                        resultJson
                          ? `<pre class="zrn_processing_result_json">${resultJson}</pre>`
                          : '<div class="zrn_processing_result_empty">Ejecuta una consulta para ver el JSON.</div>'
                      }
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <aside class="zrn_processing_side">
            <section class="zrn_processing_panel">
              <div class="zrn_processing_panel_head">
                <strong>Estado temporal</strong>
                <span>Resumen de la sesion actual</span>
              </div>
              <div class="zrn_processing_panel_body">
                <div class="zrn_processing_status_grid">
                  <div class="zrn_processing_status_item">
                    <small>Archivo</small>
                    <strong>${escapeHtml(this.state.fileName || "Sin cargar")}</strong>
                  </div>
                  <div class="zrn_processing_status_item">
                    <small>Formato</small>
                    <strong>${escapeHtml((this.state.fileExtension || "-").toUpperCase())}</strong>
                  </div>
                  <div class="zrn_processing_status_item">
                    <small>Tablas SQL</small>
                    <strong>${this.registeredTables.length}</strong>
                  </div>
                  <div class="zrn_processing_status_item">
                    <small>Hoja activa</small>
                    <strong>${escapeHtml(selectedSheet?.name || "-")}</strong>
                  </div>
                </div>
              </div>
            </section>

            <section class="zrn_processing_panel">
              <div class="zrn_processing_panel_head">
                <strong>Tablas disponibles</strong>
                <span>Referencialas directo en SQL</span>
              </div>
              <div class="zrn_processing_panel_body">
                <ul class="zrn_processing_table_list">${tableList}</ul>
              </div>
            </section>

            <section class="zrn_processing_panel">
              <div class="zrn_processing_panel_head">
                <strong>Preview estructural</strong>
                <span>${selectedSheet ? `${selectedSheet.dataRows.length} filas detectadas` : "Sin preview"}</span>
              </div>
              <div class="zrn_processing_panel_body">
                ${
                  selectedSheet && selectedSheet.columns.filter((column) => column.use).length
                    ? `
                      <div class="zrn_processing_preview_head">
                        <div class="zrn_processing_helper">Se muestran las primeras ${PREVIEW_ROW_LIMIT} filas utiles despues del encabezado.</div>
                      </div>
                      <div class="zrn_processing_preview_wrap">
                        <table class="zrn_processing_preview_table">
                          <thead>
                            <tr>${previewHead}</tr>
                          </thead>
                          <tbody>
                            ${previewRows}
                          </tbody>
                        </table>
                      </div>
                    `
                    : '<div class="zrn_processing_empty">No hay preview disponible para la hoja actual.</div>'
                }
              </div>
            </section>
          </aside>
        </div>
      </div>
    `;
  }
}

let sharedProcessingView = null;

export function getSharedProcessingView() {
  if (!sharedProcessingView) {
    sharedProcessingView = new ZrnAnalyticsProcessingView();
  }
  return sharedProcessingView;
}

function syncSharedProcessingRoot() {
  if (typeof document === "undefined") {
    return;
  }
  const view = getSharedProcessingView();
  const root = document.querySelector("[data-zrn-processing-root='1']");
  if (root) {
    if (view.root !== root) {
      view.mount(root);
    }
    return;
  }
  if (view.root) {
    view.unmount();
  }
}

function bootstrapSharedProcessingView() {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return;
  }
  const runSync = () => syncSharedProcessingRoot();

  if (document.readyState === "complete" || document.readyState === "interactive") {
    runSync();
  } else {
    document.addEventListener("DOMContentLoaded", runSync, { once: true });
  }

  window.addEventListener("load", runSync);
  window.setInterval(runSync, 800);
}

bootstrapSharedProcessingView();
