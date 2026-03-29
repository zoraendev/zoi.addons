/** @odoo-module **/

const REPORT_ROUTE = "/advanced_metrics/report/generate";
let listenersBound = false;

function getFieldInput(fieldName) {
  return document.querySelector(
    `.o_form_view.zrn_advanced_metrics_sales_orders_form .o_field_widget[name="${fieldName}"] input`,
  );
}

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

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "0";
  }
  return Number(value).toLocaleString("es-MX", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

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
    emptyCell.colSpan = 7;
    emptyCell.textContent =
      "No hay datos para mostrar con los filtros seleccionados.";

    emptyRow.appendChild(emptyCell);
    tableBody.appendChild(emptyRow);
    return;
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.className = "o_data_row";

    const cells = [
      row.fecha_entrega || "",
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

async function callGenerateReport(buttonEl) {
  if (buttonEl.dataset.loading === "1") {
    return;
  }

  const originalText = buttonEl.textContent;
  buttonEl.dataset.loading = "1";
  buttonEl.disabled = true;
  buttonEl.textContent = "Generando...";

  try {
    const response = await fetch(REPORT_ROUTE, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
      body: JSON.stringify({
        filters: getFiltersPayload(),
      }),
    });

    const data = await response.json();
    if (!response.ok || !data.success) {
      throw new Error(data.message || "No fue posible generar el reporte.");
    }

    renderRows(Array.isArray(data.rows) ? data.rows : []);
  } catch (error) {
    console.error("Error generating report", error);
    renderRows([]);
  } finally {
    buttonEl.dataset.loading = "0";
    buttonEl.disabled = false;
    buttonEl.textContent = originalText;
  }
}

function bindGenerateButtonListener() {
  if (listenersBound) {
    return;
  }

  document.addEventListener("click", (ev) => {
    const buttonEl = ev.target.closest(".zrn_am_generate_btn");
    if (!buttonEl) {
      return;
    }

    ev.preventDefault();
    callGenerateReport(buttonEl);
  });

  listenersBound = true;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bindGenerateButtonListener);
} else {
  bindGenerateButtonListener();
}
