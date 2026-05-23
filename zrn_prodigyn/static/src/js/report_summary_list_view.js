/** @odoo-module **/

import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

class ZrnProdigynReportSummaryListController extends ListController {
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

  _getSummaryTab() {
    return (
      this.props?.context?.zrn_prodigyn_summary_tab ||
      this.model?.root?.context?.zrn_prodigyn_summary_tab ||
      "overview"
    );
  }

  _getWizardModel() {
    return (
      this.props?.context?.zrn_prodigyn_wizard_model ||
      this.model?.root?.context?.zrn_prodigyn_wizard_model ||
      "zrn_prodigyn.production.planning.wizard"
    );
  }

  async returnToReport() {
    const wizardId = this._getWizardId();
    if (!wizardId) {
      return;
    }
    const summaryTab = this._getSummaryTab();
    const wizardModel = this._getWizardModel();
    const action = await this.orm.call(
      wizardModel,
      "action_back_to_report_from_context",
      [wizardId, summaryTab],
    );
    if (action) {
      await this.actionService.doAction(action);
    }
  }

  async downloadExport(fields, import_compat, format) {
    let ids = false;
    if (!this.isDomainSelected) {
      const resIds = await this.getSelectedResIds();
      ids = resIds.length > 0 && resIds;
    }
    const exportedFields = fields
      .filter((field) => field.name !== "id" && field.id !== "id")
      .map((field) => ({
        name: field.name || field.id,
        label: field.label || field.string,
        store: field.store,
        type: field.field_type || field.type,
      }));

    await download({
      data: {
        data: JSON.stringify({
          import_compat: false,
          context: this.props.context,
          domain: this.model.root.domain,
          fields: exportedFields,
          groupby: this.model.root.groupBy,
          ids,
          model: this.model.root.resModel,
        }),
      },
      url: `/web/export/${format}`,
    });
  }

  async getExportedFields(model, import_compat, parentParams) {
    return await this.rpc("/web/export/get_fields", {
      ...parentParams,
      model,
      import_compat: false,
    });
  }
}

ZrnProdigynReportSummaryListController.template =
  "zrn_prodigyn.ReportSummaryListView";

export const zrnProdigynReportSummaryListView = {
  ...listView,
  Controller: ZrnProdigynReportSummaryListController,
  props: (genericProps, view) => {
    const props = listView.props(genericProps, view);
    props.archInfo.noOpen = true;
    return props;
  },
};

registry
  .category("views")
  .add("zrn_prodigyn_report_summary_list", zrnProdigynReportSummaryListView);
