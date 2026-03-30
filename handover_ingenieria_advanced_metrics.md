# 🛠️ Handover Técnico: Refactorización y API Segura para `advanced_metrics`

**Fecha:** 2026-03-29
**Dirigido a:** Equipo de Ingeniería de Software / DevOps
**Módulo afectadó:** `advanced_metrics` (ubicado en `zoraen_cookokitchen/cookoo`)

---

## 1. Contexto General
El módulo original presentaba dos necesidades principales:
1. **Bugfix (Error Crítico de Instalación):** Odoo lanzaba un `ValueError: External ID not found` durante la instalación inicial debido a referencias cruzadas (dependencia circular) entre los archivos XML.
2. **Feature (API Segura para BI):** Se requería exponer la data procesada del reporte de inventario (`get_sales_orders_report_rows`) hacia Power BI de forma segura, sin exponer bases de datos internas ni requerir uso de cookies de sesión (`auth='user'`).

---

## 2. Detalle de Cambios por Archivo (El "Qué" y el "Por Qué")

### 🐛 Fase 1: Resolución del Bug de Instalación (Dependencia Circular)

**1. `__manifest__.py`**
*   **Cambio:** Se alteró el orden del array `'data'`, colocando `'views/views.xml'` antes de `'views/sales_orders.xml'`.
*   **Por Qué:** Odoo lee las vistas secuencialmente. `sales_orders.xml` usaba `<field name="inherit_id" ref="...inicio_form"/>`, la cual estaba declarada en `views.xml`. Al estar `sales_orders` primero, Odoo intentaba heredar de una vista que aún no existía en memoria.

**2. `views/views.xml`**
*   **Cambio:** Se trasladó la declaración del `ir.actions.act_window` (`action_advanced_metrics_report_wizard`) desde `sales_orders.xml` hacia este archivo.
*   **Por Qué:** El botón del dashboard principal en `views.xml` intentaba disparar esta acción. Como la acción vivía en el archivo secundario, el parser XML fallaba al compilar el botón. Al mover la acción "hacia arriba", resolvimos la dependencia.

**3. `views/sales_orders.xml`**
*   **Cambio:** Se agregó el prefijo de módulo explícito en la herencia: `<field name="inherit_id" ref="advanced_metrics.view_advanced_metrics_inicio_form"/>` y se eliminó la declaración de la acción redundante.
*   **Por Qué:** Buena práctica de namespace en Odoo 17. Esto previene colisiones si otro módulo llegase a tener una vista con el mismo sufijo.

---

### 🚀 Fase 2: Implementación de la API Zero-Trust para BI

Para no consumir la API oData nativa de Odoo (que obligaría a Power BI a calcular la resta de inventario por su cuenta), creamos un Endpoint personalizado que entrega la data ya "masticada".

**4. `models/api_config.py` (NUEVO)**
*   **Cambio:** Creación del modelo `advanced_metrics.api.config`.
*   **Arquitectura:**
    *   `access_token`: Generado vía `uuid.uuid4()`. Evitamos contraseñas y JWT complejos innecesarios para lecturas de sistema cerrado.
    *   `record_limit`: Límite duro (default 5000) por petición.
*   **Por Qué (Seguridad):** Diseño estricto de *Security by Design*. PowerBI requiere una URL estática, pero si la URL se filtra, la empresa está expuesta. Este modelo almacena la llave maestra y permite al Key User hacer un "rotate" (revocar token) al instante cambiando el string del UUID mediante un botón.

**5. `models/report_wizard.py`**
*   **Cambio:** Modificación de la firma del método `get_sales_orders_report_rows(self, filters=None, limit=500)` para aceptar un límite variable, e inyección de este límite en el `search()` del ORM.
*   **Por Qué:** Anteriormente `limit` estaba quemado (hardcoded) a 500 líneas, insuficiente para un modelo de minería de datos de BI de toda la empresa pero peligroso dejarlo `limit=False` (DoS attack vector). Se volvió paramétrico y seguro de inyectar por controlador.

**6. `controllers/controllers.py`**
*   **Cambio:** Creación de la ruta `@http.route('/api/advanced_metrics/sales_inventory', type='http', auth='public', methods=['GET'], csrf=False)`.
*   **Lógica de Rechazo:**
    1.  Verifica la existencia del query parameter `?token=...`. Si es nulo -> Retorna `HTTP 401`.
    2.  Busca en el ORM (con `.sudo()`) el token exacto en la tabla `api.config`. Si no hace match -> Retorna `HTTP 401`.
*   **Por Qué:** Al usar `auth='public'`, el endpoint no exige cookies de sesión activa. Sin embargo, en caso de fallo, la API no expone el por qué exacto ni throwea errores de stack de Python, simplemente rechaza la solicitud para despistar ataques automatizados.

**7. Vistas del Backend y Seguridad (`views/api_config_views.xml` & `ir.model.access.csv`)**
*   **Cambio:** Inclusión del formulario de administración de credenciales con botones `btn-danger` para revocar permisos.
*   **Seguridad:** Accesibilidad de nivel maestro `base.group_system` (`1,1,1,1`). 
*   **Por Qué:** No queremos que un representante de ventas común y corriente pueda alterar el límite de tráfico (generando latencia al servidor) o revocar la llave que rompa los tableros del cuerpo directivo en medio del mes.

---

### 💻 3. Entorno de Servidor (Notas para DevOps)
1.  **IP Desplegada:** `192.168.0.42`
2.  **Sistema de Archivos:** Todo ha sido sobreescrito mediante `chown odoo:odoo` y posteriormente se refrescó el sistema usando `odoo-bin -u advanced_metrics --stop-after-init`.
3.  **Logs de Odoo:** Se comprobó mediante `curl` de servidor que los intentos fallidos marcan efectivamente un retorno **401 Unauthorized**.

---
*Documento estructurado técnicamente para procesos de Code Review y Handover de ingeniería.*
