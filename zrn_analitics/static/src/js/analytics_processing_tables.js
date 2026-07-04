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
    loaded: true,
  };
}

export function createDeferredSheetState(sheet, index) {
  return {
    id: `${Date.now()}_${index}`,
    name: sheet.name || `Hoja ${index + 1}`,
    rawRows: [],
    tables: [],
    selectedTableId: "",
    remoteIndex: Number.isFinite(sheet.index) ? sheet.index : index,
    loaded: false,
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
  const occupied = new Set();
  const maxColumns = Math.max(...rawRows.map((row) => row.length), 0);
  rawRows.forEach((row, rowIndex) => {
    for (let columnIndex = 0; columnIndex < maxColumns; columnIndex += 1) {
      if (String(row[columnIndex] ?? "").trim() !== "") {
        occupied.add(`${rowIndex}:${columnIndex}`);
      }
    }
  });

  const components = [];
  const visited = new Set();
  occupied.forEach((key) => {
    if (visited.has(key)) {
      return;
    }
    const queue = [key];
    visited.add(key);
    const cells = [];
    while (queue.length) {
      const current = queue.shift();
      const [rowIndex, columnIndex] = current.split(":").map(Number);
      cells.push([rowIndex, columnIndex]);
      [
        [rowIndex - 1, columnIndex],
        [rowIndex + 1, columnIndex],
        [rowIndex, columnIndex - 1],
        [rowIndex, columnIndex + 1],
      ].forEach(([nextRow, nextColumn]) => {
        const nextKey = `${nextRow}:${nextColumn}`;
        if (occupied.has(nextKey) && !visited.has(nextKey)) {
          visited.add(nextKey);
          queue.push(nextKey);
        }
      });
    }
    components.push(cells);
  });

  return components
    .map((cells, index) => {
      const rowIndexes = cells.map(([rowIndex]) => rowIndex);
      const columnIndexes = cells.map(([, columnIndex]) => columnIndex);
      const minRow = Math.min(...rowIndexes);
      const maxRow = Math.max(...rowIndexes);
      const minColumn = Math.min(...columnIndexes);
      const maxColumn = Math.max(...columnIndexes);
      const height = maxRow - minRow + 1;
      const width = maxColumn - minColumn + 1;
      if (height < 3 || width < 2 || cells.length < 5) {
        return null;
      }
      const rowCounts = Array.from({ length: height }, (_, offset) =>
        cells.filter(([rowIndex]) => rowIndex === minRow + offset).length,
      );
      const firstRow = rawRows[minRow] || [];
      const componentTitle = firstRow
        .slice(minColumn, maxColumn + 1)
        .map((cell) => String(cell ?? "").trim())
        .filter(Boolean)
        .join(" ")
        .trim();
      const hasTitleRow = rowCounts[0] === 1 && rowCounts[1] >= 2;
      const headerIndex = hasTitleRow ? minRow + 1 : minRow;
      const headerRow = rawRows[headerIndex] || [];
      const startColumnIndex = Math.max(
        minColumn,
        getFirstNonEmptyColumnIndex(headerRow.slice(minColumn, maxColumn + 1)) + minColumn,
      );
      const endColumnIndex = Math.max(
        startColumnIndex,
        Math.min(
          maxColumn,
          getLastNonEmptyColumnIndex(headerRow.slice(minColumn, maxColumn + 1)) + minColumn,
        ),
      );
      return {
        name: componentTitle || `tabla_${index + 1}`,
        tableStartRowIndex: headerIndex,
        tableEndRowIndex: maxRow,
        tableStartColumnIndex: startColumnIndex,
        tableEndColumnIndex: endColumnIndex,
        hasEndRow: true,
        headerAxis: "row",
      };
    })
    .filter(Boolean)
    .sort((left, right) =>
      left.tableStartRowIndex - right.tableStartRowIndex ||
      left.tableStartColumnIndex - right.tableStartColumnIndex,
    );
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
    hasEndRow: tableDef.hasEndRow ?? true,
    headerAxis: tableDef.headerAxis || "row",
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
    hasEndRow: true,
    headerAxis: "row",
  };
}

export function buildTableStructure(table, rawRows, { keepAliases }) {
  const startColumnIndex = Math.max(0, Number(table.tableStartColumnIndex || 0));
  const endColumnIndex = Math.max(
    startColumnIndex,
    Number(table.tableEndColumnIndex || startColumnIndex),
  );
  const startRowIndex = Math.max(0, Number(table.tableStartRowIndex || 0));
  const endRowIndex = getEffectiveEndRowIndex(table, rawRows);
  const previousColumns = new Map((table.columns || []).map((column) => [column.index, column]));

  if (table.headerAxis === "column") {
    const selectedRowIndexes = Array.from(
      { length: endRowIndex - startRowIndex + 1 },
      (_, index) => startRowIndex + index,
    );
    const dataColumnIndexes = Array.from(
      { length: Math.max(0, endColumnIndex - startColumnIndex) },
      (_, index) => startColumnIndex + index + 1,
    ).filter((columnIndex) =>
      selectedRowIndexes.some((rowIndex) => String(rawRows[rowIndex]?.[columnIndex] ?? "").trim() !== ""),
    );
    table.columns = selectedRowIndexes.map((sourceIndex, index) => {
      const previous = previousColumns.get(sourceIndex);
      const originalLabel =
        String(rawRows[sourceIndex]?.[startColumnIndex] ?? "").trim() || `Fila ${sourceIndex + 1}`;
      const sampleValues = dataColumnIndexes.slice(0, 20).map(
        (columnIndex) => rawRows[sourceIndex]?.[columnIndex],
      );
      return {
        index: sourceIndex,
        tablePosition: index,
        columnLabel: `F${sourceIndex + 1}`,
        originalLabel,
        use: previous ? previous.use : true,
        alias:
          keepAliases && previous
            ? previous.alias
            : sanitizeIdentifier(originalLabel, `column_${index + 1}`),
        type: previous?.type || inferColumnType(sampleValues),
      };
    });
    table.dataRowsCount = dataColumnIndexes.length;
    table.previewRows = buildDatasetRecords(table, rawRows).slice(0, PREVIEW_ROW_LIMIT);
  } else {
    const headerRow = rawRows[startRowIndex] || [];
    const selectedColumnIndexes = Array.from(
      { length: endColumnIndex - startColumnIndex + 1 },
      (_, index) => startColumnIndex + index,
    );
    const dataRows = rawRows
      .slice(startRowIndex + 1, endRowIndex + 1)
      .filter((row) =>
        selectedColumnIndexes.some((columnIndex) => String(row[columnIndex] ?? "").trim() !== ""),
      );
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
  }
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
    errors.push(
      table.headerAxis === "column"
        ? "Configura una fila inicial valida."
        : "Configura una fila de encabezado valida.",
    );
  }
  if (table.hasEndRow && table.tableEndRowIndex < table.tableStartRowIndex + 1) {
    errors.push("La fila final debe estar debajo del encabezado.");
  }
  if (
    table.tableStartColumnIndex < 0 ||
    table.tableEndColumnIndex < table.tableStartColumnIndex
  ) {
    errors.push("Configura un rango de columnas valido.");
  }
  if (table.headerAxis === "column" && table.tableEndColumnIndex <= table.tableStartColumnIndex) {
    errors.push("Cuando el encabezado es por columna, deja al menos una columna de datos a la derecha.");
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
  if (table.headerAxis === "column") {
    const endRowIndex = getEffectiveEndRowIndex(table, rawRows);
    const dataColumnIndexes = Array.from(
      { length: Math.max(0, table.tableEndColumnIndex - table.tableStartColumnIndex) },
      (_, index) => table.tableStartColumnIndex + index + 1,
    );
    return dataColumnIndexes
      .filter((columnIndex) =>
        Array.from({ length: endRowIndex - table.tableStartRowIndex + 1 }, (_, offset) =>
          table.tableStartRowIndex + offset,
        ).some((rowIndex) => String(rawRows[rowIndex]?.[columnIndex] ?? "").trim() !== ""),
      )
      .map((columnIndex) => {
        const record = {};
        activeColumns.forEach((column) => {
          const alias = sanitizeIdentifier(column.alias, `column_${column.index + 1}`);
          record[alias] = coerceValueByType(rawRows[column.index]?.[columnIndex], column.type);
        });
        return record;
      });
  }
  const endRowIndex = getEffectiveEndRowIndex(table, rawRows);
  return rawRows
    .slice(table.tableStartRowIndex + 1, endRowIndex + 1)
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

export function getEffectiveEndRowIndex(table, rawRows) {
  const lastRowIndex = Math.max(0, rawRows.length - 1);
  if (table.hasEndRow) {
    return Math.max(
      table.tableStartRowIndex,
      Math.min(lastRowIndex, Number(table.tableEndRowIndex || table.tableStartRowIndex)),
    );
  }
  for (let rowIndex = lastRowIndex; rowIndex > table.tableStartRowIndex; rowIndex -= 1) {
    const row = rawRows[rowIndex] || [];
    const hasValue = row
      .slice(table.tableStartColumnIndex, table.tableEndColumnIndex + 1)
      .some((cell) => String(cell ?? "").trim() !== "");
    if (hasValue) {
      return rowIndex;
    }
  }
  return table.tableStartRowIndex;
}
