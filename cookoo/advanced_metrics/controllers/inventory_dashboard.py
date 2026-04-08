# -*- coding: utf-8 -*-

from odoo import http

from .base_dashboard import BaseDashboardController


class InventoryDashboardController(BaseDashboardController):
    _service_model = 'advanced_metrics.inventory.dashboard'
    _request_filter_keys = (
        'dateFrom',
        'dateTo',
        'warehouseId',
        'categoryId',
        'limit',
        'groupBy',
        'daysWithoutMovement',
    )

    @http.route('/api/bi/inventory-intelligent/top-products', type='http', auth='public', methods=['POST'], csrf=False)
    def get_top_products(self, **kwargs):
        return self._handle_service_request(
            'get_top_products_report_data',
            'Top productos obtenido correctamente.',
            'No fue posible obtener el top de productos.',
        )

    @http.route('/api/bi/inventory-intelligent/products-sales', type='http', auth='public', methods=['POST'], csrf=False)
    def get_products_sales(self, **kwargs):
        return self._handle_service_request(
            'get_products_sales_report_data',
            'Ventas por producto obtenidas correctamente.',
            'No fue posible obtener las ventas por producto.',
        )

    @http.route('/api/bi/inventory-intelligent/sales-trend', type='http', auth='public', methods=['POST'], csrf=False)
    def get_sales_trend(self, **kwargs):
        return self._handle_service_request(
            'get_sales_trend_report_data',
            'Tendencia de ventas obtenida correctamente.',
            'No fue posible obtener la tendencia de ventas.',
            extra_keys=['periodSummary'],
            extra_payload={'periodSummary': {}},
        )

    @http.route('/api/bi/inventory-intelligent/dead-products', type='http', auth='public', methods=['POST'], csrf=False)
    def get_dead_products(self, **kwargs):
        return self._handle_service_request(
            'get_dead_products_report_data',
            'Productos sin movimiento obtenidos correctamente.',
            'No fue posible obtener los productos sin movimiento.',
        )

    @http.route('/api/bi/inventory-intelligent/high-rotation-products', type='http', auth='public', methods=['POST'], csrf=False)
    def get_high_rotation_products(self, **kwargs):
        return self._handle_service_request(
            'get_high_rotation_products_report_data',
            'Productos con alta rotación obtenidos correctamente.',
            'No fue posible obtener los productos con alta rotación.',
        )

    @http.route('/api/bi/production/weekly-plan', type='http', auth='public', methods=['POST'], csrf=False)
    def get_weekly_production_plan(self, **kwargs):
        return self._handle_service_request(
            'get_weekly_production_plan_report_data',
            'Plan de produccion obtenido correctamente.',
            'No fue posible obtener el plan de produccion.',
        )
