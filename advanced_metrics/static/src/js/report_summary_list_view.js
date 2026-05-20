/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

class AdvancedMetricsReportSummaryListController extends ListController {
  setup() {
    super.setup();
    this.orm = useService("orm");
  }

  _getWizardId() {
    const contextWizardId =
      this.props?.context?.active_id ||
      this.props?.context?.default_wizard_id ||
      this.model?.root?.context?.active_id ||
      this.model?.root?.context?.default_wizard_id;
    if (contextWizardId) {
      return Number(contextWizardId);
    }

    const rawHash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : window.location.hash;
    const params = new URLSearchParams(rawHash);
    return Number(params.get("active_id") || 0);
  }

  _getOriginView() {
    return (
      this.props?.context?.advanced_metrics_origin_view ||
      this.model?.root?.context?.advanced_metrics_origin_view ||
      "report"
    );
  }

  async returnToReport() {
    const wizardId = this._getWizardId();
    if (!wizardId) {
      return;
    }
    const originView = this._getOriginView();
    const action = await this.orm.call(
      "advanced_metrics.report.wizard",
      "action_back_to_origin_from_context",
      [wizardId, originView],
    );
    await this.actionService.doAction(action);
  }
}

AdvancedMetricsReportSummaryListController.template =
  "advanced_metrics.ReportSummaryListView";

const advancedMetricsReportSummaryListView = {
  ...listView,
  Controller: AdvancedMetricsReportSummaryListController,
};

registry
  .category("views")
  .add(
    "advanced_metrics_report_summary_list",
    advancedMetricsReportSummaryListView,
  );
