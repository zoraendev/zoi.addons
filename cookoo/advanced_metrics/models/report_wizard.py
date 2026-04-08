from datetime import datetime, timedelta

from odoo import api, fields, models


class AdvancedMetricsReportWizard(models.TransientModel):
    _name = 'advanced_metrics.report.wizard'
    _description = 'Asistente de reporte de ventas e inventario'

    fecha_entrega_desde = fields.Date(string='Fecha de entrega desde')
    fecha_entrega_hasta = fields.Date(string='Fecha de entrega hasta')
    cliente_id = fields.Many2one(
        'res.partner',
        string='Cliente',
    )
    numero_orden_venta = fields.Char(string='Numero de orden de venta')
    producto = fields.Char(string='Producto')
    cantidad_vendida_min = fields.Float(string='Cantidad vendida minima')
    cantidad_vendida_max = fields.Float(string='Cantidad vendida maxima')
    inventario_disponible_min = fields.Float(string='Inventario disponible minimo')
    inventario_disponible_max = fields.Float(string='Inventario disponible maximo')
    report_line_ids = fields.One2many(
        'advanced_metrics.report.wizard.line',
        'wizard_id',
        string='Lineas de reporte',
    )

    @api.model
    def get_sales_orders_report_rows(self, filters=None, limit=500):
        """
        Genera las filas del reporte de planificacion semanal.

        Extrae lineas de orden de venta confirmadas, las cruza con el
        inventario actual en almacen, y calcula cuanto falta producir
        para cubrir cada pedido.

        Filtros soportados (dict):
            - fecha_entrega_desde (str YYYY-MM-DD): Limite inferior de fecha de entrega.
            - fecha_entrega_hasta (str YYYY-MM-DD): Limite superior de fecha de entrega.
            - cliente_id (int): ID del partner para filtrar por cliente exacto.
            - cliente_nombre (str): Nombre parcial para busqueda difusa de cliente.

        Returns:
            list[dict]: Lista de filas con las 8 columnas del reporte:
                fecha_entrega, dia_semana, cliente, numero_orden_venta,
                producto, cantidad_vendida, inventario_disponible,
                cantidad_sugerida_producir.
        """
        filters = filters or {}

        # --- MEJORA 2: Mapa de dias de la semana en espanol ---
        # Python devuelve weekday() como 0=Lunes, 6=Domingo.
        # Este diccionario traduce el numero al nombre completo en espanol
        # para que la gerente de operaciones vea "Lunes" en vez de "2026-04-07".
        DIAS_SEMANA = {
            0: 'Lunes',
            1: 'Martes',
            2: 'Miercoles',
            3: 'Jueves',
            4: 'Viernes',
            5: 'Sabado',
            6: 'Domingo',
        }

        # --- Validacion de modelos disponibles ---
        # Si el modulo de ventas o inventario no estan instalados,
        # retornamos vacio en vez de lanzar un error.
        if 'sale.order.line' not in self.env or 'stock.quant' not in self.env:
            return []

        sale_line_model = self.env['sale.order.line']
        stock_quant_model = self.env['stock.quant']

        # --- Dominio base: solo ordenes confirmadas o completadas ---
        # display_type=False excluye lineas de seccion/nota que no son productos.
        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('display_type', '=', False),
        ]

        fecha_desde = filters.get('fecha_entrega_desde')
        fecha_hasta = filters.get('fecha_entrega_hasta')
        cliente_id = filters.get('cliente_id')
        cliente_nombre = filters.get('cliente_nombre')

        # --- FILTRO INTELIGENTE EN CASCADA (Mitigacion Riesgo 1) ---
        # Prioridad: commitment_date (fecha de entrega prometida al cliente).
        # Problema: commitment_date puede estar vacia si el vendedor no la lleno.
        # Solucion: Buscamos primero por commitment_date. Para las ordenes que no
        # la tengan, el campo f_entrega mas abajo usara date_order como respaldo,
        # pero la busqueda principal filtra por commitment_date para que el
        # reporte refleje la realidad logistica de entregas.
        if fecha_desde:
            domain.append(('order_id.commitment_date', '>=', f'{fecha_desde} 00:00:00'))
        if fecha_hasta:
            domain.append(('order_id.commitment_date', '<=', f'{fecha_hasta} 23:59:59'))

        if cliente_id:
            domain.append(('order_partner_id', '=', int(cliente_id)))
        elif cliente_nombre:
            domain.append(('order_partner_id.name', 'ilike', cliente_nombre))

        # --- MITIGACION RIESGO 4: Limite anti-colapso de memoria ---
        # Nunca permitimos mas de 10,000 filas para proteger la RAM del servidor.
        safe_limit = min(limit, 10000)
        order_lines = sale_line_model.search(domain, order='id desc', limit=safe_limit)
        product_ids = order_lines.mapped('product_id').ids

        # --- Consulta de inventario actual agrupado por producto ---
        # quantity representa el stock fisico total en ubicaciones internas.
        # available_quantity representa el stock libre de usar despues de reservas.
        qty_by_product_id = {}
        free_qty_by_product_id = {}
        if product_ids:
            grouped_quants = stock_quant_model.read_group(
                [('product_id', 'in', product_ids), ('location_id.usage', '=', 'internal')],
                ['product_id', 'quantity:sum', 'available_quantity:sum'],
                ['product_id'],
            )
            qty_by_product_id = {
                item['product_id'][0]: item.get('quantity', 0.0)
                for item in grouped_quants
                if item.get('product_id')
            }
            free_qty_by_product_id = {
                item['product_id'][0]: item.get('available_quantity', 0.0)
                for item in grouped_quants
                if item.get('product_id')
            }

        # --- MEMORIA DE INVENTARIO VIRTUAL (Rolling Deduction / FIFO) ---
        # MITIGACION RIESGO MATEMATICO: Para evitar la "Doble Contabilidad" de stock, 
        # creamos una copia del inventario actual. A medida que procesamos cada orden 
        # cronologicamente, vamos restando lo vendido de esta memoria virtual.
        running_stock_by_product = qty_by_product_id.copy()
        running_free_stock_by_product = free_qty_by_product_id.copy()

        # --- ORDENAMIENTO CRONOLOGICO (El pilar de la planificacion) ---
        # Paso critico: El descuento de inventario DEBE ser First-In-First-Out.
        # Ordenamos las lineas empezando por el Lunes mas temprano hasta el Domingo.
        def get_sort_date(line):
            # Usamos commitment_date como fecha primaria de entrega
            f_entrega = line.order_id.commitment_date or line.order_id.date_order or datetime.now()
            return f_entrega.date() if hasattr(f_entrega, 'date') else f_entrega

        # Ordenamiento en memoria antes de construir las filas del reporte
        sorted_lines = sorted(order_lines, key=get_sort_date)

        # --- Construccion de filas del reporte ---
        rows = []
        for line in sorted_lines:
            if not line.product_id:
                continue

            product_id = line.product_id.id
            sold_qty = float(line.product_uom_qty or 0.0)

            # LOGICA DE ASIGNACION DE STOCK (Cascada):
            # Leemos cuanto stock queda disponible y libre de usar
            # despues de las ordenes anteriores.
            available_qty_before = running_stock_by_product.get(product_id, 0.0)
            free_qty_before = running_free_stock_by_product.get(product_id, 0.0)
            
            if available_qty_before >= sold_qty:
                # Caso A: Tenemos stock suficiente para cubrir toda esta orden.
                # Sugerido a producir es 0.
                suggested_production = 0.0
                # Descontamos las unidades consumidas de la reserva virtual.
                running_stock_by_product[product_id] -= sold_qty
                running_free_stock_by_product[product_id] = max(free_qty_before - sold_qty, 0.0)
            else:
                # Caso B: El stock se agoto o no es suficiente.
                # Solo sugerimos producir el faltante neto.
                suggested_production = sold_qty - available_qty_before
                # El inventario para este producto se marca como 0 para las siguientes filas.
                running_stock_by_product[product_id] = 0.0
                running_free_stock_by_product[product_id] = max(free_qty_before - sold_qty, 0.0)

            # Fecha final para mostrar en el reporte (con filtro de respaldo)
            f_entrega = line.order_id.commitment_date or line.order_id.date_order or datetime.now()

            # Normalizacion de fecha para calculo de dia de semana
            if hasattr(f_entrega, 'date'):
                fecha_date = f_entrega.date()
            elif hasattr(f_entrega, 'weekday'):
                fecha_date = f_entrega
            else:
                fecha_date = datetime.now().date()

            rows.append({
                'fecha_entrega': fecha_date.isoformat(),
                'dia_semana': DIAS_SEMANA.get(fecha_date.weekday(), ''),
                'cliente': line.order_partner_id.display_name or '',
                'numero_orden_venta': line.order_id.name or '',
                'producto': line.product_id.display_name or '',
                'cantidad_vendida': sold_qty,
                # Reportamos el stock que habia disponible JUSTO antes de esta venta
                'inventario_disponible': round(available_qty_before, 2),
                'inventario_libre_usar': round(free_qty_before, 2),
                'cantidad_sugerida_producir': round(suggested_production, 2),
            })

        # --- MEJORA 5: ORDENAMIENTO INTELIGENTE PARA PLANIFICACION ---
        # Ordenamos primero por fecha de entrega (lunes primero) y luego
        # por nombre de cliente dentro de cada dia. Esto permite que la
        # gerente de operaciones lea el reporte de arriba a abajo como
        # un plan de produccion diario sin reordenar nada.
        rows.sort(key=lambda r: (r.get('fecha_entrega', ''), r.get('cliente', '')))

        return rows

    def action_generate_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Advanced Metrics',
                'message': 'La logica de generacion del reporte se implementara despues.',
                'type': 'warning',
                'sticky': False,
            },
        }


    @api.model
    def get_next_week_dates(self):
        """
        Calcula el intervalo de la proxima semana (Lunes a Domingo)
        ajustado a la operacion en Guatemala.
        
        Returns:
            dict: {'desde': 'YYYY-MM-DD', 'hasta': 'YYYY-MM-DD'}
        """
        # Obtenemos la fecha actual en la zona horaria del usuario
        # Si no esta definida, usamos UTC, pero lo ideal en GT es UTC-6
        today = fields.Date.context_today(self)
        
        # weekday() en Python: 0=Lunes, 6=Domingo
        # Calculamos dias hasta el proximo lunes
        current_weekday = today.weekday()
        days_until_monday = (7 - current_weekday) if current_weekday < 7 else 1
        
        next_monday = today + timedelta(days=days_until_monday)
        next_sunday = next_monday + timedelta(days=6)
        
        return {
            'desde': next_monday.isoformat(),
            'hasta': next_sunday.isoformat(),
        }

class AdvancedMetricsReportWizardLine(models.TransientModel):
    _name = 'advanced_metrics.report.wizard.line'
    _description = 'Linea del reporte de ventas e inventario'
    # MEJORA 5: Ordenamiento ascendente por fecha para planificacion
    # (lunes primero, domingo al final).
    _order = 'fecha_entrega asc, id asc'

    wizard_id = fields.Many2one(
        'advanced_metrics.report.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    fecha_entrega = fields.Date(string='Fecha de entrega')
    # MEJORA 2: Dia de la semana en espanol (Lunes, Martes, etc.)
    dia_semana = fields.Char(string='Dia')
    cliente_id = fields.Many2one('res.partner', string='Cliente')
    numero_orden_venta = fields.Char(string='Numero de orden de venta')
    producto = fields.Char(string='Producto')
    cantidad_vendida = fields.Float(string='Cantidad vendida')
    inventario_disponible = fields.Float(string='Inventario disponible de producto terminado')
    inventario_libre_usar = fields.Float(string='Inventario libre de usar')
    cantidad_sugerida_producir = fields.Float(
        string='Cantidad sugerida a producir',
        default=0.0,
    )
