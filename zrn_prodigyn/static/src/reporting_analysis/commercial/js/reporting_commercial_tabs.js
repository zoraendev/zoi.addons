/** @odoo-module **/

const ROOT_SELECTOR = ".zrn_prodigyn_reporting_commercial_view";

function mountCommercialTabs(root) {
  if (root.dataset.commercialTabsMounted === "1") {
    return;
  }

  const tabButtons = Array.from(
    root.querySelectorAll("[data-commercial-chart-tabs='1'] [data-chart-tab]")
  );
  const tabPanels = Array.from(root.querySelectorAll("[data-chart-panel]"));

  if (!tabButtons.length || !tabPanels.length) {
    return;
  }

  const activateTab = (tabName) => {
    tabButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.chartTab === tabName);
    });
    tabPanels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.chartPanel === tabName);
    });
  };

  tabButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      activateTab(button.dataset.chartTab);
    });
  });

  activateTab(tabButtons[0].dataset.chartTab);
  root.dataset.commercialTabsMounted = "1";
}

function scan(target = document) {
  target.querySelectorAll(ROOT_SELECTOR).forEach(mountCommercialTabs);
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
          mountCommercialTabs(node);
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
