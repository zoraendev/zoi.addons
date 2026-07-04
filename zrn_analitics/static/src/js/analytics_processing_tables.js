/** @odoo-module **/

import {
  HEADER_SCAN_LIMIT,
  PREVIEW_ROW_LIMIT,
  buildRowSnippet,
  cloneRows,
  coerceValueByType,
  getColumnLabel,
  getFirstNonEmptyColumnIndex,
  getLastNonEmptyColumnIndex,
  inferColumnType,
  isRowEmpty,
  sanitizeIdentifier,
} from "./analytics_processing_utils";

export function createSheetState(sheet, index) {
  const rawRows = cloneRows(sheet.rawRows || []);
  const tables = detectTables(rawRows).map((tableDef, tableIndex) =>
    createTableState(rawRows, sheet.name, tableDef, tableIndex)
  );
  if (!tables.length && rawRows.length) {
    tables.push(createTableState(rawRows, sheet.name, buildFallbackTable(rawRows), 0));
  }
  return {
    id: `${Date.now()}_${index}`,
    name: sheet.name || `Hoja ${index + 1}`,
    rawRows,
    tables,
    selectedTableId: tables[0]?.id || "",
  };
}

export function detectHeaderRow(rawRows) {
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

export function detectTables(rawRows) {
  const blocks = [];
  let blockStart = -1;
  for (let index = 0; index < rawRows.length; index += 1) {
    const row = rawRows[index] || [];
    if (!isRowEmpty(row)) {
      if (blockStart === -1) {
        blockStart = index;
      }
      continue;
    }
    if (blockStart !== -1) {
      blocks.push([blockStart, index - 1]);
      blockStart = -1;
    }
  }
  if (blockStart !== -1) {
    blocks.push([blockStart, rawRows.length - 1]);
  }
  return blocks
    .filter(([start, end]) => end >= start)
    .map(([start, end], index) => {
      const blockRows = rawRows.slice(start, end + 1);
      const headerOffset = detectHeaderRow(blockRows);
      const headerIndex = start + headerOffset;
      const headerRow = rawRows[headerIndex] || [];
      const startColumnIndex = getFirstNonEmptyColumnIndex(headerRow);
      const endColumnIndex = Math.max(
        startColumnIndex,
        getLastNonEmptyColumnIndex(headerRow),
      );
      return {
        name: `tabla_${index + 1}`,
        tableStartRowIndex: headerIndex,
        tableEndRowIndex: end,
        tableStartColumnIndex: startColumnIndex,
        tableEndColumnIndex: endColumnIndex,
      };
    });
}

export function createTableState(rawRows, sheetName, tableDef, tableIndex) {
  const fallbackName = sanitizeIdentifier(
    `${sheetName || "hoja"}_${tableDef.name || `tabla_${tableIndex + 1}`}`,
    "dataset",
  );
  const table = {
    id: `${Date.now()}_${tableIndex}_${Math.random().toString(16).slice(2, 8)}`,
    name: tableDef.name || `Tabla ${tableIndex + 1}`,
    tableName: fallbackName,
    tableStartRowIndex: tableDef.tableStartRowIndex || 0,
    tableEndRowIndex:
      tableDef.tableEndRowIndex ?? Math.max(0, (rawRows || []).length - 1),
    tableStartColumnIndex: tableDef.tableStartColumnIndex || 0,
    tableEndColumnIndex: tableDef.tableEndColumnIndex || 0,
    columns: [],
    previewRows: [],
    dataRowsCount: 0,
    errors: [],
    structureApplied: false,
    structureDirty: true,
  };
  buildTableStructure(table, rawRows, { keepAliases: false });
  return table;
}

export function buildFallbackTable(rawRows) {
  const headerIndex = detectHeaderRow(rawRows);
  const headerRow = rawRows[headerIndex] || [];
  const startColumnIndex = getFirstNonEmptyColumnIndex(headerRow);
  const endColumnIndex = Math.max(
    startColumnIndex,
    getLastNonEmptyColumnIndex(headerRow),
  );
  return {
    name: "tabla_1",
    tableStartRowIndex: headerIndex,
    tableEndRowIndex: Math.max(0, rawRows.length - 1),
    tableStartColumnIndex: startColumnIndex,
    tableEndColumnIndex: endColumnIndex,
  };
}

export function buildTableStructure(table, rawRows, { keepAliases }) {
  const headerRow = rawRows[table.tableStartRowIndex] || [];
  const startColumnIndex = Math.max(0, Number(table.tableStartColumnIndex || 0));
  const endColumnIndex = Math.max(
    startColumnIndex,
    Number(table.tableEndColumnIndex || startColumnIndex),
  );
  const startRowIndex = Math.max(0, Number(table.tableStartRowIndex || 0));
  const endRowIndex = Math.max(startRowIndex, Number(table.tableEndRowIndex || startRowIndex));
  const selectedColumnIndexes = Array.from(
    { length: endColumnIndex - startColumnIndex + 1 },
    (_, index) => startColumnIndex + index,
  );
  const dataRows = rawRows
    .slice(startRowIndex + 1, endRowIndex + 1)
    .filter((row) =>
      selectedColumnIndexes.some((columnIndex) => String(row[columnIndex] ?? "").trim() !== ""),
    );
  const previousColumns = new Map((table.columns || []).map((column) => [column.index, column]));
  table.columns = selectedColumnIndexes.map((sourceIndex, index) => {
    const previous = previousColumns.get(sourceIndex);
    const originalLabel =
      String(headerRow[sourceIndex] ?? "").trim() || `Columna ${getColumnLabel(sourceIndex)}`;
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
  table.previewRows = dataRows.slice(0, PREVIEW_ROW_LIMIT);
  table.dataRowsCount = dataRows.length;
  table.errors = validateTableStructure(table, rawRows);
  table.structureDirty = true;
}

export function validateTableStructure(table, rawRows) {
  const errors = [];
  if (!rawRows.length) {
    errors.push("La hoja esta vacia.");
    return errors;
  }
  if (table.tableStartRowIndex < 0 || table.tableStartRowIndex >= rawRows.length) {
    errors.push("Configura una fila de encabezado valida.");
  }
  if (table.tableEndRowIndex < table.tableStartRowIndex + 1) {
    errors.push("La fila final debe estar debajo del encabezado.");
  }
  if (
    table.tableStartColumnIndex < 0 ||
    table.tableEndColumnIndex < table.tableStartColumnIndex
  ) {
    errors.push("Configura un rango de columnas valido.");
  }
  const activeColumns = (table.columns || []).filter((column) => column.use);
  if (!activeColumns.length) {
    errors.push("Activa al menos una columna para construir el dataset.");
  }
  const aliases = activeColumns.map((column) =>
    sanitizeIdentifier(column.alias, `column_${column.index + 1}`),
  );
  if (new Set(aliases).size !== aliases.length) {
    errors.push("Los alias SQL de las columnas activas deben ser unicos.");
  }
  if (!table.dataRowsCount) {
    errors.push("La tabla no contiene filas de datos en el rango actual.");
  }
  return errors;
}

export function buildDatasetRecords(table, rawRows) {
  const activeColumns = table.columns.filter((column) => column.use);
  return rawRows
    .slice(table.tableStartRowIndex + 1, table.tableEndRowIndex + 1)
    .filter((row) =>
      activeColumns.some((column) => String(row[column.index] ?? "").trim() !== ""),
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
