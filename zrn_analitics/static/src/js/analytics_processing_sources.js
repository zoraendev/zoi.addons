/** @odoo-module **/

import {
  buildFileIcon,
  extractJsonRows,
  extractXmlRows,
  formatBytes,
  parseCsvText,
} from "./analytics_processing_utils";

export async function parseLocalSource(file) {
  const extension = (file.name.split(".").pop() || "").toLowerCase();
  const parsedSheets = await parseSourceFile(file, extension);
  return {
    sourceType: "local_file",
    sourceLabel: file.name,
    sourceMeta: {
      name: file.name,
      extension,
      sizeLabel: formatBytes(file.size),
      iconClass: buildFileIcon(extension),
      totalSheets: parsedSheets.length,
      loaded: true,
      url: "",
    },
    sheets: parsedSheets,
  };
}

export async function parseGoogleSheetSource(url) {
  const normalized = normalizeGoogleSheetUrl(url);
  const response = await fetch("/zrn_analitics/google_sheet/metadata", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "same-origin",
    body: JSON.stringify({ url: normalized.cleanUrl }),
  });
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (!response.ok || !payload.success) {
    throw new Error(
      payload.error || "No se pudo leer el Google Sheet publico. Verifica la URL y los permisos.",
    );
  }
  const parsedSheets = payload.sheets || [];
  if (!parsedSheets.length) {
    throw new Error("El Google Sheet no devolvio hojas utilizables.");
  }
  return {
    sourceType: "google_sheet",
    sourceLabel: normalized.label,
    sourceMeta: {
      name: normalized.label,
      extension: "gsheet",
      sizeLabel: `${parsedSheets.length} hoja(s)`,
      iconClass: "fa-table",
      totalSheets: parsedSheets.length,
      loaded: true,
      url: normalized.cleanUrl,
    },
    sheets: parsedSheets,
  };
}

export async function fetchGoogleSheetSheet(url, sheetIndex) {
  const response = await fetch("/zrn_analitics/google_sheet/sheet", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "same-origin",
    body: JSON.stringify({ url, sheet_index: sheetIndex }),
  });
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (!response.ok || !payload.success || !payload.sheet) {
    throw new Error(payload.error || "No se pudo cargar la hoja seleccionada.");
  }
  return payload.sheet;
}

export async function parseSourceFile(file, extension) {
  if (["xls", "xlsx", "xlsm"].includes(extension)) {
    return parseWorkbook(await file.arrayBuffer());
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

export function parseWorkbook(arrayBuffer) {
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

export function normalizeGoogleSheetUrl(rawUrl) {
  const value = String(rawUrl || "").trim();
  if (!value) {
    throw new Error("Ingresa la URL publica del Google Sheet.");
  }
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error("La URL del Google Sheet no es valida.");
  }
  const match = url.pathname.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
  if (!match) {
    throw new Error("No se encontro el identificador del Google Sheet en la URL.");
  }
  const spreadsheetId = match[1];
  return {
    spreadsheetId,
    cleanUrl: value,
    label: `Google Sheet ${spreadsheetId.slice(0, 8)}`,
  };
}
