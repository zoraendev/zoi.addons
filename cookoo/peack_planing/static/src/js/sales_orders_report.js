/** @odoo-module **/

/**
 * Advanced Metrics - Reporte de Ordenes de Venta
 *
 * Este modulo JavaScript controla la interaccion del dashboard de
 * planificacion semanal dentro de Odoo. Gestiona tres acciones:
 *
 * 1. Boton "Generar reporte": Llama al backend y pinta la tabla HTML.
 * 2. Boton "Descargar XLS": Genera y descarga un archivo Excel real.
 * 3. Selector de periodo: Auto-llena las fechas para semana o mes,
 *    y habilita edicion manual cuando el usuario elige personalizado.
 *
 * Autor: Equipo de Ingenieria - Zoraen
 * Ultima modificacion: 2026-04-20
 */

const REPORT_ROUTE = "/peack_planing/report/generate";
const PERIOD_DATES_ROUTE = "/peack_planing/report/period-dates";
const CACHE_KEY = "peack_planing_filters_cache";
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 horas
let listenersBound = false;
let currentRows = [];
let currentSort = { key: null, direction: "asc" };
let currentViewMode = "list"; // 'list' o 'cards'

const SORTABLE_COLUMN_MAP = {
  fecha_entrega: "fecha_entrega",
  dia_semana: "dia_semana",
  cliente_id: "cliente",
  numero_orden_venta: "numero_orden_venta",
  producto: "producto",
  cantidad_vendida: "cantidad_vendida",
  inventario_disponible: "inventario_disponible",
  inventario_libre_usar: "inventario_libre_usar",
  cantidad_sugerida_producir: "cantidad_sugerida_producir",
};

function getDownloadButton() {
  return document.querySelector(".zrn_am_download_btn");
}

function setDownloadButtonEnabled(enabled) {
  const downloadButton = getDownloadButton();
  if (!downloadButton) {
    return;
  }

  downloadButton.dataset.enabled = enabled ? "1" : "0";
  downloadButton.classList.toggle("disabled", !enabled);
  downloadButton.setAttribute("aria-disabled", enabled ? "false" : "true");
}

// ================================================================
// UTILIDADES: Acceso a campos del formulario
// ================================================================

/**
 * Busca el input HTML de un campo especifico dentro del formulario
 * de Advanced Metrics.
 *
 * @param {string} fieldName - Nombre tecnico del campo en Odoo.
 * @returns {HTMLInputElement|null} El elemento input o null.
 */
function getFieldInput(fieldName) {
  return document.querySelector(
    `.o_form_view.zrn_peack_planing_sales_orders_form .o_field_widget[name="${fieldName}"] input`,
  );
}

function getPeriodTypeValue() {
  const checkedRadio = document.querySelector(
    '.o_form_view.zrn_peack_planing_sales_orders_form .o_field_widget[name="period_type"] input:checked',
  );
  if (checkedRadio?.value) {
    return checkedRadio.value;
  }

  const selectInput = document.querySelector(
    '.o_form_view.zrn_peack_planing_sales_orders_form .o_field_widget[name="period_type"] select',
  );
  return selectInput?.value || "week";
}

function setFieldValue(inputEl, value) {
  if (!inputEl) {
    return;
  }

  const nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype,
    "value",
  )?.set;

  if (nativeSetter) {
    nativeSetter.call(inputEl, value || "");
  } else {
    inputEl.value = value || "";
  }

  inputEl.dispatchEvent(new Event("input", { bubbles: true }));
  inputEl.dispatchEvent(new Event("change", { bubbles: true }));
}

function getFormState() {
  return window.__advancedMetricsSalesOrdersGetState?.() || {};
}

function normalizeMany2manyIds(fieldValue) {
  if (!fieldValue) {
    return [];
  }

  if (Array.isArray(fieldValue)) {
    return fieldValue
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0);
  }

  const candidateIds = fieldValue.currentIds || fieldValue.resIds || [];
  return candidateIds
    .map((value) => Number(value))
    .filter((value) => Number.isInteger(value) && value > 0);
}

/**
 * Extrae los datos del filtro de clientes desde el estado vivo del formulario.
 *
 * @returns {Object} Objeto con todos_los_clientes y cliente_ids.
 */
function getCustomerFilterData() {
  const formState = getFormState();
  return {
    todos_los_clientes: Boolean(formState.todos_los_clientes),
    cliente_ids: normalizeMany2manyIds(formState.cliente_ids),
  };
}

/**
 * Construye el payload de filtros a enviar al backend.
 *
 * Lee los campos de fecha y cliente del formulario y los empaqueta
 * en un objeto JSON listo para enviar por POST.
 *
 * @returns {Object} Filtros para el backend.
 */
function getFiltersPayload() {
  const fechaDesde = (getFieldInput("fecha_entrega_desde")?.value || "").trim();
  const fechaHasta = (getFieldInput("fecha_entrega_hasta")?.value || "").trim();
  const customerData = getCustomerFilterData();

  const filters = {};
  if (fechaDesde) {
    filters.fecha_entrega_desde = fechaDesde;
  }
  if (fechaHasta) {
    filters.fecha_entrega_hasta = fechaHasta;
  }
  if (customerData.todos_los_clientes) {
    filters.todos_los_clientes = true;
  } else if (customerData.cliente_ids.length) {
    filters.cliente_ids = customerData.cliente_ids;
  }
  return filters;
}

function saveFiltersToCache() {
  try {
    const filters = getFiltersPayload();
    const cacheData = {
      timestamp: Date.now(),
      filters: filters,
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
  } catch (e) {
    console.error("Error saving filters to cache", e);
  }
}

function loadFiltersFromCache() {
  try {
    const cachedStr = localStorage.getItem(CACHE_KEY);
    if (!cachedStr) {
      return;
    }

    const cacheData = JSON.parse(cachedStr);
    const now = Date.now();

    if (now - cacheData.timestamp > CACHE_TTL) {
      localStorage.removeItem(CACHE_KEY);
      return;
    }

    const filters = cacheData.filters || {};
    if (filters.fecha_entrega_desde) {
      setFieldValue(getFieldInput("fecha_entrega_desde"), filters.fecha_entrega_desde);
    }
    if (filters.fecha_entrega_hasta) {
      setFieldValue(getFieldInput("fecha_entrega_hasta"), filters.fecha_entrega_hasta);
    }
    // Para clientes (m2m) es mas complejo ya que depende del widget de Odoo,
    // pero al menos recuperamos las fechas que es lo mas tedioso.
  } catch (e) {
    console.error("Error loading filters from cache", e);
  }
}

/**
 * Fabrica las opciones del fetch() para las peticiones POST.
 *
 * @param {Object} extraPayload - Datos adicionales para el body.
 * @returns {Object} Opciones para fetch().
 */
function buildRequestOptions(extraPayload = {}) {
  return {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
    credentials: "same-origin",
    body: JSON.stringify({
      filters: getFiltersPayload(),
      ...extraPayload,
    }),
  };
}

// ================================================================
// UTILIDADES: Formato de numeros
// ================================================================

/**
 * Formatea un numero para mostrar en la tabla HTML.
 * Usa formato mexicano (comas como separador de miles).
 *
 * @param {*} value - Valor a formatear.
 * @returns {string} Numero formateado o "0".
 */
function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "0";
  }
  return Number(value).toLocaleString("es-MX", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function getSortKeyFromHeader(headerCell) {
  if (!headerCell) {
    return null;
  }
  const fieldName = headerCell.dataset.name || "";
  return SORTABLE_COLUMN_MAP[fieldName] || null;
}

function compareValues(aValue, bValue, key) {
  const numericKeys = new Set([
    "cantidad_vendida",
    "inventario_disponible",
    "inventario_libre_usar",
    "cantidad_sugerida_producir",
  ]);

  if (numericKeys.has(key)) {
    const aNum = Number(aValue || 0);
    const bNum = Number(bValue || 0);
    return aNum - bNum;
  }

  if (key === "fecha_entrega") {
    const aDate = (aValue || "").toString();
    const bDate = (bValue || "").toString();
    return aDate.localeCompare(bDate);
  }

  return (aValue || "")
    .toString()
    .toLowerCase()
    .localeCompare((bValue || "").toString().toLowerCase());
}

function applyCurrentSort(rows) {
  const sortedRows = [...rows];
  if (!currentSort.key) {
    return sortedRows;
  }

  sortedRows.sort((a, b) => {
    const result = compareValues(
      a[currentSort.key],
      b[currentSort.key],
      currentSort.key,
    );
    return currentSort.direction === "asc" ? result : -result;
  });
  return sortedRows;
}

function updateHeaderSortIndicators() {
  const headerCells = document.querySelectorAll(
    ".zrn_am_table_shell .o_list_table thead th[data-name]",
  );

  headerCells.forEach((headerCell) => {
    const sortKey = getSortKeyFromHeader(headerCell);
    if (!sortKey) {
      headerCell.removeAttribute("aria-sort");
      return;
    }

    if (sortKey === currentSort.key) {
      headerCell.setAttribute(
        "aria-sort",
        currentSort.direction === "asc" ? "ascending" : "descending",
      );
    } else {
      headerCell.setAttribute("aria-sort", "none");
    }
  });
}

function toggleSortFromHeader(headerCell) {
  const sortKey = getSortKeyFromHeader(headerCell);
  if (!sortKey) {
    return;
  }

  if (currentSort.key === sortKey) {
    currentSort.direction = currentSort.direction === "asc" ? "desc" : "asc";
  } else {
    currentSort.key = sortKey;
    currentSort.direction = "asc";
  }

  renderRows(currentRows, { updateState: false });
}

// ================================================================
// RENDERIZADO DE TABLA HTML
// ================================================================

/**
 * Pinta las filas del reporte en la tabla HTML del dashboard.
 *
 * MEJORA 2: Se agrega la columna "Dia" al renderizado para que
 * la gerente vea "Lunes", "Martes", etc. directamente en Odoo.
 *
 * @param {Array} rows - Filas del reporte (desde el backend).
 */
function renderRows(rows, { updateState = true } = {}) {
  const container = document.querySelector(".zrn_am_table_shell");
  if (!container) {
    return;
  }

  if (updateState) {
    currentRows = Array.isArray(rows) ? [...rows] : [];
  }

  if (currentViewMode === "cards") {
    renderCards(currentRows);
  } else {
    renderTable(currentRows);
  }
}

function renderTable(rows) {
  const container = document.querySelector(".zrn_am_table_shell");
  container.innerHTML = `
    <table class="table o_list_table table-sm table-hover table-striped mb-0">
      <thead>
        <tr>
          <th data-name="fecha_entrega" class="o_column_sortable" title="Fecha comprometida de entrega">Fecha Entrega</th>
          <th data-name="dia_semana" class="o_column_sortable" title="Día de la semana">Día</th>
          <th data-name="cliente_id" class="o_column_sortable" title="Cliente comercial">Cliente</th>
          <th data-name="numero_orden_venta" class="o_column_sortable" title="Número de la Orden de Venta">Orden Venta</th>
          <th data-name="producto" class="o_column_sortable" title="Producto o Combo solicitado">Producto / Combo</th>
          <th data-name="cantidad_vendida" class="o_column_sortable text-end" title="Cantidad total vendida en la orden">Vendida</th>
          <th data-name="inventario_disponible" class="o_column_sortable text-end" title="Inventario físico actual en almacén">Disponible</th>
          <th data-name="inventario_libre_usar" class="o_column_sortable text-end" title="Inventario disponible menos lo ya reservado por otras órdenes">Libre</th>
          <th data-name="cantidad_sugerida_producir" class="o_column_sortable text-end" title="Cantidad calculada que falta por producir para cubrir esta demanda">Sugerido</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  `;

  const tableBody = container.querySelector("tbody");
  const rowsToRender = applyCurrentSort(rows);

  if (!rowsToRender.length) {
    setDownloadButtonEnabled(false);
    tableBody.innerHTML = `
      <tr class="o_data_row zrn_am_empty_row">
        <td colspan="9" class="o_data_cell text-muted text-center py-5">
          No hay datos para mostrar con los filtros seleccionados.
        </td>
      </tr>
    `;
    updateHeaderSortIndicators();
    return;
  }

  setDownloadButtonEnabled(true);

  rowsToRender.forEach((row) => {
    const tr = document.createElement("tr");
    tr.className = "o_data_row";
    tr.innerHTML = `
      <td class="o_data_cell">${row.fecha_entrega || ""}</td>
      <td class="o_data_cell">${row.dia_semana || ""}</td>
      <td class="o_data_cell">
        <a href="#" class="zrn_pp_record_link" data-model="res.partner" data-id="${row.cliente_id}">${row.cliente || ""}</a>
      </td>
      <td class="o_data_cell">
        <a href="#" class="zrn_pp_record_link" data-model="sale.order" data-id="${row.order_id}">${row.numero_orden_venta || ""}</a>
      </td>
      <td class="o_data_cell">
        <a href="#" class="zrn_pp_record_link" data-model="product.product" data-id="${row.product_id}">${row.producto || ""}</a>
      </td>
      <td class="o_data_cell text-end">${formatNumber(row.cantidad_vendida)}</td>
      <td class="o_data_cell text-end">${formatNumber(row.inventario_disponible)}</td>
      <td class="o_data_cell text-end">${formatNumber(row.inventario_libre_usar)}</td>
      <td class="o_data_cell text-end font-weight-bold text-primary">${formatNumber(row.cantidad_sugerida_producir)}</td>
    `;
    tableBody.appendChild(tr);
  });

  updateHeaderSortIndicators();
}

function renderCards(rows) {
  const container = document.querySelector(".zrn_am_table_shell");
  container.innerHTML = '<div class="zrn_pp_cards_grid p-3"></div>';
  const grid = container.querySelector(".zrn_pp_cards_grid");

  if (!rows.length) {
    setDownloadButtonEnabled(false);
    grid.innerHTML = '<div class="text-muted text-center py-5 w-100">No hay datos para mostrar.</div>';
    return;
  }

  setDownloadButtonEnabled(true);

  rows.forEach((row) => {
    const card = document.createElement("div");
    card.className = "zrn_pp_card";
    card.innerHTML = `
      <div class="zrn_pp_card_header">
        <span class="zrn_pp_card_date">${row.fecha_entrega} (${row.dia_semana})</span>
        <a href="#" class="badge rounded-pill bg-primary zrn_pp_record_link" data-model="sale.order" data-id="${row.order_id}">${row.numero_orden_venta}</a>
      </div>
      <div class="zrn_pp_card_body">
        <h5 class="zrn_pp_card_title">
            <a href="#" class="zrn_pp_record_link" data-model="product.product" data-id="${row.product_id}">${row.producto}</a>
        </h5>
        <div class="zrn_pp_card_client">
            <a href="#" class="zrn_pp_record_link text-muted" data-model="res.partner" data-id="${row.cliente_id}">${row.cliente}</a>
        </div>
        <div class="zrn_pp_card_stats">
          <div class="zrn_pp_stat">
            <label>Vendido</label>
            <span>${formatNumber(row.cantidad_vendida)}</span>
          </div>
          <div class="zrn_pp_stat">
            <label>Disponible</label>
            <span>${formatNumber(row.inventario_disponible)}</span>
          </div>
          <div class="zrn_pp_stat highlighting">
            <label>Sugerido</label>
            <span>${formatNumber(row.cantidad_sugerida_producir)}</span>
          </div>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}

// ================================================================
// COMUNICACION CON EL BACKEND
// ================================================================

/**
 * Llama al endpoint del backend y retorna los datos JSON.
 *
 * @returns {Object} Respuesta del servidor con las filas del reporte.
 * @throws {Error} Si la respuesta no es exitosa.
 */
async function fetchReportJson() {
  const response = await fetch(REPORT_ROUTE, buildRequestOptions());
  const data = await response.json();
  if (!response.ok || !data.success) {
    throw new Error(data.message || "No fue posible generar el reporte.");
  }
  return data;
}

async function fetchPeriodDates(periodType) {
  const response = await fetch(PERIOD_DATES_ROUTE, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
    credentials: "same-origin",
    body: JSON.stringify({
      params: {
        period_type: periodType,
      },
    }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error("No fue posible calcular el rango de fechas.");
  }
  return data.result || data;
}

/**
 * Extrae el nombre del archivo desde la cabecera Content-Disposition.
 *
 * @param {string|null} disposition - Valor de Content-Disposition.
 * @returns {string} Nombre del archivo para la descarga.
 */
function getFilenameFromDisposition(disposition) {
  if (!disposition) {
    return "planificacion_semanal.xlsx";
  }

  const utfMatch = disposition.match(/filename\*=UTF-8''([^;\n]+)/i);
  if (utfMatch?.[1]) {
    return decodeURIComponent(utfMatch[1]);
  }

  const asciiMatch = disposition.match(/filename="?([^";\n]+)"?/i);
  return asciiMatch?.[1] || "planificacion_semanal.xlsx";
}

// ================================================================
// ACCION: GENERAR REPORTE (tabla HTML)
// ================================================================

/**
 * Ejecuta la generacion del reporte y pinta los resultados.
 * Se conecta al boton "Generar reporte".
 *
 * @param {HTMLElement} buttonEl - Boton que disparo la accion.
 */
async function callGenerateReport(buttonEl) {
  if (buttonEl.dataset.loading === "1") {
    return;
  }

  const originalHtml = buttonEl.innerHTML;
  buttonEl.dataset.loading = "1";
  buttonEl.classList.add("disabled");
  buttonEl.innerHTML = "Generando...";

  try {
    saveFiltersToCache();
    const data = await fetchReportJson();
    const rows = Array.isArray(data.rows) ? data.rows : [];
    renderRows(rows);
  } catch (error) {
    console.error("Error generating report", error);
    renderRows([]);
  } finally {
    buttonEl.dataset.loading = "0";
    buttonEl.classList.remove("disabled");
    buttonEl.innerHTML = originalHtml;
  }
}

// ================================================================
// ACCION: DESCARGAR EXCEL (.xlsx)
// ================================================================

/**
 * Ejecuta la descarga del archivo Excel.
 * Se conecta al boton "Descargar XLS".
 *
 * El backend retorna un archivo binario .xlsx que el navegador
 * descarga directamente gracias a los headers MIME correctos.
 *
 * @param {HTMLElement} buttonEl - Boton que disparo la accion.
 */
async function callDownloadReport(buttonEl) {
  if (buttonEl.dataset.loading === "1" || buttonEl.dataset.enabled !== "1") {
    return;
  }

  const originalHtml = buttonEl.innerHTML;
  buttonEl.dataset.loading = "1";
  buttonEl.classList.add("disabled");
  buttonEl.innerHTML =
    '<span class="fa fa-spinner fa-spin" aria-hidden="true"></span><span>Descargando...</span>';

  try {
    const response = await fetch(
      REPORT_ROUTE,
      buildRequestOptions({ export_xls: true }),
    );

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data = await response.json();
      throw new Error(
        data.message || "No fue posible descargar el archivo XLS.",
      );
    }

    if (!response.ok) {
      throw new Error("No fue posible descargar el archivo XLS.");
    }

    // Crear un enlace temporal para forzar la descarga
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = getFilenameFromDisposition(
      response.headers.get("content-disposition"),
    );
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error("Error downloading XLS report", error);
  } finally {
    buttonEl.dataset.loading = "0";
    buttonEl.classList.remove("disabled");
    buttonEl.innerHTML = originalHtml;
  }
}

// ================================================================
// ACCION: SINCRONIZAR RANGO SEGUN TIPO DE PERIODO
// ================================================================

/**
 * Completa los campos de fecha con el rango de la semana o del mes
 * actual, calculado del lado del servidor con la zona horaria de Odoo.
 */
async function syncPeriodDates(periodType, { force = false } = {}) {
  const desdeInput = getFieldInput("fecha_entrega_desde");
  const hastaInput = getFieldInput("fecha_entrega_hasta");

  if (!desdeInput || !hastaInput || periodType === "custom") {
    return;
  }

  try {
    if (!force && desdeInput.value && hastaInput.value) {
      return;
    }

    const result = await fetchPeriodDates(periodType);
    if (result?.desde && result?.hasta) {
      setFieldValue(desdeInput, result.desde);
      setFieldValue(hastaInput, result.hasta);
    }
  } catch (err) {
    console.error("Error al obtener fechas del servidor", err);
  }
}

// ================================================================
// ENLACE DE EVENTOS (Event Binding)
// ================================================================

/**
 * Registra los listeners de click para los tres botones:
 * - Generar reporte (clase: zrn_am_generate_btn)
 * - Descargar XLS (clase: zrn_am_download_btn)
 * - Semana siguiente (clase: zrn_am_next_week_btn) [MEJORA 1]
 *
 * Usamos delegacion de eventos en document para funcionar incluso
 * cuando Odoo renderiza la vista de forma asincrona.
 */
function bindGenerateButtonListener() {
  if (listenersBound) {
    return;
  }

  document.addEventListener("click", (ev) => {
    const headerCell = ev.target.closest(
      ".zrn_am_table_shell .o_list_table thead th[data-name]",
    );
    if (headerCell) {
      ev.preventDefault();
      toggleSortFromHeader(headerCell);
      return;
    }

    // --- Boton: Generar reporte ---
    const generateButton = ev.target.closest(".zrn_am_generate_btn");
    if (generateButton) {
      ev.preventDefault();
      callGenerateReport(generateButton);
      return;
    }

    // --- Boton: Descargar XLS ---
    const downloadButton = ev.target.closest(".zrn_am_download_btn");
    if (downloadButton) {
      ev.preventDefault();
      callDownloadReport(downloadButton);
      return;
    }

    // --- Boton: Cambiar Vista (Cards/List) ---
    const viewModeButton = ev.target.closest(".zrn_pp_toggle_view_btn");
    if (viewModeButton) {
      ev.preventDefault();
      currentViewMode = currentViewMode === "list" ? "cards" : "list";
      const icon = viewModeButton.querySelector("i");
      if (icon) {
        icon.className = currentViewMode === "list" ? "fa fa-th" : "fa fa-list";
      }
      renderRows(currentRows, { updateState: false });
      return;
    }

    // --- Boton: Guardar Filtros Manual ---
    const saveFiltersButton = ev.target.closest(".zrn_am_save_filters_btn");
    if (saveFiltersButton) {
      ev.preventDefault();
      saveFiltersToCache();
      const originalText = saveFiltersButton.innerHTML;
      saveFiltersButton.innerHTML = '<i class="fa fa-check"></i> Guardado';
      saveFiltersButton.classList.replace("btn-secondary", "btn-success");
      window.setTimeout(() => {
        saveFiltersButton.innerHTML = originalText;
        saveFiltersButton.classList.replace("btn-success", "btn-secondary");
      }, 2000);
      return;
    }

    // --- Enlaces a registros de Odoo ---
    const recordLink = ev.target.closest(".zrn_pp_record_link");
    if (recordLink) {
      ev.preventDefault();
      const resModel = recordLink.dataset.model;
      const resId = parseInt(recordLink.dataset.id);
      if (resModel && resId) {
        // Usamos el servicio de acciones de Odoo si esta disponible via window
        if (window.__peackPlaningDoAction) {
          window.__peackPlaningDoAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            res_id: resId,
            views: [[false, "form"]],
            target: "current",
          });
        } else {
          // Fallback para entornos donde no se inyectó el helper
          console.warn("Odoo Action Service not linked to PeackPlaning");
        }
      }
      return;
    }
  });

  document.addEventListener("change", (ev) => {
    const periodField = ev.target.closest(
      '.o_form_view.zrn_peack_planing_sales_orders_form .o_field_widget[name="period_type"]',
    );
    if (!periodField) {
      return;
    }

    const periodType = getPeriodTypeValue();
    syncPeriodDates(periodType, { force: true });
  });

  listenersBound = true;
}

function syncInitialEmptyState(attempt = 0) {
  const table = document.querySelector(".zrn_am_table_shell .o_list_table");
  const tableBody = table?.querySelector("tbody");

  if (!tableBody) {
    if (attempt < 12) {
      window.setTimeout(() => syncInitialEmptyState(attempt + 1), 100);
    }
    return;
  }

  const hasMeaningfulData = Array.from(tableBody.querySelectorAll("tr")).some(
    (row) =>
      Array.from(row.querySelectorAll("td")).some(
        (cell) => (cell.textContent || "").trim() !== "",
      ),
  );

  if (!hasMeaningfulData) {
    renderRows([]);
    return;
  }

  setDownloadButtonEnabled(true);
}

function initPeackPlaningUi() {
  bindGenerateButtonListener();
  setDownloadButtonEnabled(false);
  loadFiltersFromCache();
  syncPeriodDates(getPeriodTypeValue(), { force: false });
  syncInitialEmptyState();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initPeackPlaningUi);
} else {
  initPeackPlaningUi();
}
