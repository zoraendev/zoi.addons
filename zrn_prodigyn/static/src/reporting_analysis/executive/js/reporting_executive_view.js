/** @odoo-module **/

const ROOT_SELECTOR = ".zrn_prodigyn_reporting_executive_view[data-executive-dashboard='1']";

const EXECUTIVE_BLUEPRINT = {
  kpis: [
    {
      label: "Facturacion consolidada",
      value: "Q 601K",
      note: "Lugar para revenue, delta y ritmo del periodo.",
    },
    {
      label: "Margen real",
      value: "21.5%",
      note: "Aqui ira el margen ponderado y su lectura ejecutiva.",
    },
    {
      label: "Cobertura comercial",
      value: "56.9%",
      note: "Base para cobertura total, gap y focos por canal.",
    },
    {
      label: "Clientes activos",
      value: "118",
      note: "Espacio para clientes, tickets y profundidad del portafolio.",
    },
  ],
  centers: [
    {
      name: "Centro Comercial",
      status: "estable",
      metric: "Sell-through y revenue",
      meta: "Canales, marcas y traccion por cliente.",
      signals: [
        "Traer KPIs de facturacion, sell-out y mezcla.",
        "Cruzar alertas por canal, marca y lineas clave.",
      ],
    },
    {
      name: "Centro Financiero",
      status: "atencion",
      metric: "Cartera y margen",
      meta: "Cobranzas, aging y desviaciones de rentabilidad.",
      signals: [
        "Preparar cartera vencida, riesgo y recuperacion.",
        "Anclar variaciones de margen a decisiones concretas.",
      ],
    },
    {
      name: "Centro Operaciones",
      status: "seguimiento",
      metric: "Servicio y capacidad",
      meta: "Alertas operativas, fill rate y lotes sensibles.",
      signals: [
        "Conectar inventario, abastecimiento y fabricacion.",
        "Mostrar cuellos de botella y backlog transversal.",
      ],
    },
    {
      name: "Centro Cobertura",
      status: "exploracion",
      metric: "PDV y expansion",
      meta: "Presencia, huecos y potencial por red comercial.",
      signals: [
        "Montar mapa de PDVs activos y brechas por cadena.",
        "Agregar lectura de velocity y alertas de stockout.",
      ],
    },
  ],
  alerts: [
    {
      title: "Bloque ejecutivo de alertas",
      meta: "Prioridad alta",
      note: "Aqui ira la narrativa transversal de los hallazgos mas urgentes del hub.",
    },
    {
      title: "Desviaciones de margen o cobertura",
      meta: "Prioridad media",
      note: "Reservado para resumir impactos, causa probable y siguiente accion.",
    },
  ],
  timeline: [
    {
      date: "Semana 1",
      title: "Conectar KPIs base",
      note: "Revenue, margen, cobertura y clientes desde las fuentes definitivas.",
    },
    {
      date: "Semana 2",
      title: "Mapear centros del hub",
      note: "Llevar Comercial, Finanzas, Operaciones y Cobertura a componentes separables.",
    },
    {
      date: "Semana 3",
      title: "Abrir alertas narrativas",
      note: "Agregar backlog ejecutivo y agenda de hitos priorizados.",
    },
  ],
};

function renderKpis(items) {
  return items
    .map(
      (item) => `
        <article class="zrn_prodigyn_reporting_executive_kpi">
          <div class="zrn_prodigyn_reporting_executive_kpi_label">${item.label}</div>
          <div class="zrn_prodigyn_reporting_executive_kpi_value">${item.value}</div>
          <div class="zrn_prodigyn_reporting_executive_kpi_note">${item.note}</div>
        </article>
      `
    )
    .join("");
}

function renderCenters(items) {
  return items
    .map(
      (item) => `
        <article class="zrn_prodigyn_reporting_executive_center">
          <div class="zrn_prodigyn_reporting_executive_center_top">
            <div>
              <div class="zrn_prodigyn_reporting_executive_center_name">${item.name}</div>
              <div class="zrn_prodigyn_reporting_executive_center_meta">${item.meta}</div>
            </div>
            <div class="zrn_prodigyn_reporting_executive_center_status">${item.status}</div>
          </div>
          <div class="zrn_prodigyn_reporting_executive_center_metric">${item.metric}</div>
          <ul class="zrn_prodigyn_reporting_executive_center_signals">
            ${item.signals.map((signal) => `<li>${signal}</li>`).join("")}
          </ul>
        </article>
      `
    )
    .join("");
}

function renderAlerts(items) {
  return items
    .map(
      (item) => `
        <article class="zrn_prodigyn_reporting_executive_alert">
          <div class="zrn_prodigyn_reporting_executive_alert_title">${item.title}</div>
          <div class="zrn_prodigyn_reporting_executive_alert_meta">${item.meta}</div>
          <div class="zrn_prodigyn_reporting_executive_alert_note">${item.note}</div>
        </article>
      `
    )
    .join("");
}

function renderTimeline(items) {
  return items
    .map(
      (item) => `
        <article class="zrn_prodigyn_reporting_executive_timeline_item">
          <div class="zrn_prodigyn_reporting_executive_timeline_date">${item.date}</div>
          <div class="zrn_prodigyn_reporting_executive_timeline_title">${item.title}</div>
          <div class="zrn_prodigyn_reporting_executive_timeline_note">${item.note}</div>
        </article>
      `
    )
    .join("");
}

function mountExecutiveView(root) {
  if (root.dataset.executiveMounted === "1") {
    return;
  }

  const kpiNode = root.querySelector("[data-executive-kpis='1']");
  const centerNode = root.querySelector("[data-executive-centers='1']");
  const alertNode = root.querySelector("[data-executive-alerts='1']");
  const timelineNode = root.querySelector("[data-executive-timeline='1']");

  if (kpiNode) {
    kpiNode.innerHTML = renderKpis(EXECUTIVE_BLUEPRINT.kpis);
  }
  if (centerNode) {
    centerNode.innerHTML = renderCenters(EXECUTIVE_BLUEPRINT.centers);
  }
  if (alertNode) {
    alertNode.innerHTML = renderAlerts(EXECUTIVE_BLUEPRINT.alerts);
  }
  if (timelineNode) {
    timelineNode.innerHTML = renderTimeline(EXECUTIVE_BLUEPRINT.timeline);
  }

  root.dataset.executiveMounted = "1";
}

function scan(target = document) {
  target.querySelectorAll(ROOT_SELECTOR).forEach(mountExecutiveView);
}

function startObserver() {
  scan();
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType !== 1) {
          continue;
        }
        if (node.matches?.(ROOT_SELECTOR)) {
          mountExecutiveView(node);
          continue;
        }
        scan(node);
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startObserver, { once: true });
} else {
  startObserver();
}
