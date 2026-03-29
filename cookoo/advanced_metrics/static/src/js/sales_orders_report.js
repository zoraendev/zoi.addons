/** @odoo-module **/

const REPORT_ROUTE = "/advanced_metrics/report/generate";
let listenersBound = false;

function setEmptyStateMessage(message, isError = false) {
  const messageNode = document.querySelector(
    ".zrn_am_empty_state_content p:first-child",
  );
  if (!messageNode) {
    return;
  }

  messageNode.textContent = message;
  messageNode.classList.toggle("text-danger", isError);
}

async function callGenerateReport(buttonEl) {
  if (buttonEl.dataset.loading === "1") {
    return;
  }

  const originalText = buttonEl.textContent;
  buttonEl.dataset.loading = "1";
  buttonEl.disabled = true;
  buttonEl.textContent = "Generando...";
  setEmptyStateMessage("Generando reporte...");

  try {
    const response = await fetch(REPORT_ROUTE, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
      body: JSON.stringify({
        generated_at: new Date().toISOString(),
      }),
    });

    const data = await response.json();
    if (!response.ok || !data.success) {
      throw new Error(data.message || "No fue posible generar el reporte.");
    }

    setEmptyStateMessage(data.message || "Reporte generado.");
  } catch (error) {
    console.error("Error generating report", error);
    setEmptyStateMessage(
      error.message || "Ocurrio un error al generar el reporte.",
      true,
    );
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
