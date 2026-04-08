/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class AdvancedMetricsSalesOrdersFormController extends FormController {
  displayName() {
    return "Ordenes de Venta";
  }
}

export const advancedMetricsSalesOrdersFormView = {
  ...formView,
  Controller: AdvancedMetricsSalesOrdersFormController,
};

registry.category("views").add(
  "advanced_metrics_sales_orders_form",
  advancedMetricsSalesOrdersFormView,
);
