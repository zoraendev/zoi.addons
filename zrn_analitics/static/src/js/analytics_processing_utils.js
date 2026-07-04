/** @odoo-module **/

export const HEADER_SCAN_LIMIT = 25;
export const PREVIEW_ROW_LIMIT = 8;
export const QUERY_RESULT_LIMIT = 200;
export const SQL_TYPES = ["text", "number", "date", "boolean"];
export const READ_ONLY_SQL_PATTERN = /^\s*select\b/i;
export const FORBIDDEN_SQL_PATTERN =
  /\b(insert|update|delete|drop|create|alter|attach|truncate|replace|merge|grant|revoke)\b/i;

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function sanitizeIdentifier(value, fallback = "column") {
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

export function quoteSqlIdentifier(value) {
  return `[${String(value ?? "").replace(/]/g, "]]")}]`;
}

export function buildRowSnippet(row = []) {
  return row
    .slice(0, 5)
    .map((cell) => String(cell ?? "").trim())
    .filter(Boolean)
    .join(" | ");
}

export function isRowEmpty(row = []) {
  return !row.some((cell) => String(cell ?? "").trim() !== "");
}

export function formatBytes(size) {
  const units = ["B", "KB", "MB", "GB"];
  let value = Number(size || 0);
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value >= 100 || unitIndex === 0 ? Math.round(value) : value.toFixed(1)} ${units[unitIndex]}`;
}

export function getColumnLabel(index) {
  let value = index + 1;
  let label = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    value = Math.floor((value - 1) / 26);
  }
  return label;
}

export function getLastNonEmptyColumnIndex(row = []) {
  for (let index = row.length - 1; index >= 0; index -= 1) {
    if (String(row[index] ?? "").trim()) {
      return index;
    }
  }
  return -1;
}

export function getFirstNonEmptyColumnIndex(row = []) {
  for (let index = 0; index < row.length; index += 1) {
    if (String(row[index] ?? "").trim()) {
      return index;
    }
  }
  return 0;
}

export function inferColumnType(values) {
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
    if (
      /^\d{4}[-/]\d{1,2}[-/]\d{1,2}$/.test(value) ||
      /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/.test(value)
    ) {
      return "date";
    }
    return "text";
  }
  return "text";
}

export function normalizeCellValue(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function parseCsvLine(line) {
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

export function parseCsvText(text) {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .filter((line) => line.length || text.includes("\n"))
    .map((line) => parseCsvLine(line));
}

export function buildRowsFromObjects(records) {
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

export function extractJsonRows(text) {
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

export function extractXmlRows(text) {
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

export function coerceValueByType(value, type) {
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
  }
  return normalized;
}

export function cloneRows(rows) {
  return rows.map((row) => [...row]);
}

export function buildFileIcon(extension) {
  if (["xls", "xlsx", "xlsm"].includes(extension)) {
    return "fa-file-excel-o";
  }
  if (["json", "xml"].includes(extension)) {
    return "fa-file-code-o";
  }
  if (extension === "csv") {
    return "fa-file-text-o";
  }
  return "fa-file-o";
}

export function toChartNumber(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const numeric = Number(String(value).replace(/,/g, ""));
  return Number.isFinite(numeric) ? numeric : null;
}

export function aggregateValues(values, aggregate) {
  const cleanValues = values.filter((value) => value !== null && value !== undefined);
  if (!cleanValues.length) {
    return 0;
  }
  if (aggregate === "count") {
    return cleanValues.length;
  }
  const numericValues = cleanValues.map((value) => Number(value)).filter(Number.isFinite);
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
