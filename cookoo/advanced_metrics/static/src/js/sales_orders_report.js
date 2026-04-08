/** @odoo-module **/

/**
 * Advanced Metrics - Reporte de Ordenes de Venta
 *
 * Este modulo JavaScript controla la interaccion del dashboard de
 * planificacion semanal dentro de Odoo. Gestiona tres acciones:
 *
 * 1. Boton "Generar reporte": Llama al backend y pinta la tabla HTML.
 * 2. Boton "Descargar XLS": Genera y descarga un archivo Excel real.
 * 3. Boton "Semana Siguiente" (MEJORA 1): Auto-llena las fechas con
 *    el proximo lunes y domingo para facilitar la planificacion.
 *
 * Autor: Equipo de Ingenieria - Zoraen
 * Ultima modificacion: 2026-04-06
 */

const REPORT_ROUTE = "/advanced_metrics/report/generate";
let listenersBound = false;

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
    `.o_form_view.zrn_advanced_metrics_sales_orders_form .o_field_widget[name="${fieldName}"] input`,
  );
}

/**
 * Extrae los datos del filtro de cliente (ID y nombre).
 *
 * @returns {Object} Objeto con cliente_id y cliente_nombre.
 */
function getCustomerFilterData() {
  const customerInput = getFieldInput("cliente_id");
  if (!customerInput) {
    return { cliente_id: null, cliente_nombre: "" };
  }

  const customerId =
    customerInput.dataset.resId ||
    customerInput.dataset.id ||
    customerInput.getAttribute("data-res-id") ||
    null;

  return {
    cliente_id: customerId,
    cliente_nombre: (customerInput.value || "").trim(),
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
  if (customerData.cliente_id) {
    filters.cliente_id = customerData.cliente_id;
  }
  if (customerData.cliente_nombre) {
    filters.cliente_nombre = customerData.cliente_nombre;
  }
  return filters;
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
function renderRows(rows) {
  const table = document.querySelector(".zrn_am_table_shell .o_list_table");
  const tableBody = table?.querySelector("tbody");
  if (!tableBody) {
    return;
  }

  tableBody.innerHTML = "";
  if (!rows.length) {
    const emptyRow = document.createElement("tr");
    emptyRow.className = "o_data_row";

    const emptyCell = document.createElement("td");
    emptyCell.className = "o_data_cell text-muted";
    // MEJORA 2: La tabla ahora tiene 8 columnas (se agrego "Dia")
    emptyCell.colSpan = 8;
    emptyCell.textContent =
      "No hay datos para mostrar con los filtros seleccionados.";

    emptyRow.appendChild(emptyCell);
    tableBody.appendChild(emptyRow);
    return;
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.className = "o_data_row";

    // MEJORA 2: Se agrega row.dia_semana como segunda columna
    const cells = [
      row.fecha_entrega || "",
      row.dia_semana || "",
      row.cliente || "",
      row.numero_orden_venta || "",
      row.producto || "",
      formatNumber(row.cantidad_vendida),
      formatNumber(row.inventario_disponible),
      formatNumber(row.cantidad_sugerida_producir),
    ];

    cells.forEach((value) => {
      const td = document.createElement("td");
      td.className = "o_data_cell";
      td.textContent = value;
      tr.appendChild(td);
    });

    tableBody.appendChild(tr);
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
    const data = await fetchReportJson();
    renderRows(Array.isArray(data.rows) ? data.rows : []);
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
  if (buttonEl.dataset.loading === "1") {
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
// MEJORA 1: BOTON "SEMANA SIGUIENTE"
// ================================================================

/**
 * Calcula el proximo lunes y domingo, y los inyecta en los campos
 * de fecha del formulario.
 *
 * Logica:
 * - Si hoy es domingo, "semana siguiente" empieza manana (lunes).
 * - Si hoy es lunes, "semana siguiente" empieza el proximo lunes.
 * - Para cualquier otro dia, avanzamos al proximo lunes.
 *
 * Esto evita que la gerente tenga que calcular manualmente que
 * dia cae el proximo lunes y el proximo domingo.
 */
/**
 * MEJORA 1: BOTON "SEMANA SIGUIENTE" (Seguro)
 * Llama al servidor para obtener las fechas oficiales (GT).
 */
async function fillNextWeekDates() {
  const desdeInput = getFieldInput("fecha_entrega_desde");
  const hastaInput = getFieldInput("fecha_entrega_hasta");

  if (!desdeInput || !hastaInput) return;

  try {
    const response = await fetch("/advanced_metrics/report/next-week-dates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ params: {} }),
    });
    const { result } = await response.json();

    if (result && result.desde && result.hasta) {
      const nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value",
      ).set;

      nativeSetter.call(desdeInput, result.desde);
      desdeInput.dispatchEvent(new Event("input", { bubbles: true }));
      desdeInput.dispatchEvent(new Event("change", { bubbles: true }));

      nativeSetter.call(hastaInput, result.hasta);
      hastaInput.dispatchEvent(new Event("input", { bubbles: true }));
      hastaInput.dispatchEvent(new Event("change", { bubbles: true }));
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

    // --- MEJORA 1: Boton: Semana Siguiente ---
    const nextWeekButton = ev.target.closest(".zrn_am_next_week_btn");
    if (nextWeekButton) {
      ev.preventDefault();
      fillNextWeekDates();
      return;
    }
  });

  listenersBound = true;
}

function initAdvancedMetricsUi() {
  bindGenerateButtonListener();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAdvancedMetricsUi);
} else {
  initAdvancedMetricsUi();
}
