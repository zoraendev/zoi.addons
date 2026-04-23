# Documentación Técnica: Evolución del Módulo Sales Bot (Automatizations)
---

## 1. Objetivo de los Cambios
El objetivo principal de esta iteración fue transformar el módulo `automatizations` de una estructura de prueba abierta a un **sistema de producción seguro y funcional** para la integración con agentes externos (Bots). Se priorizó la seguridad mediante tokens, la consistencia de datos y la experiencia del administrador dentro de Odoo.

---

## 2. Cambios Arquitectónicos

### A. Estandarización de Seguridad (Capa de Controladores)
**Cambio:** Creación de `controllers/base_controller.py` y refactorización de los controladores de Clientes, Productos y Órdenes.
- **¿Por qué?:** Anteriormente, los endpoints estaban definidos con `auth='public'`, lo que exponía datos sensibles y permitía la creación de órdenes sin validación.
- **Razón del cambio:** Se implementó un patrón de herencia donde todos los controladores heredan de `AutomatizationsBaseController`. Este base controller valida que cada petición incluya un token válido en los headers (`Access-Token` o `Authorization`) o en la URL.
- **Beneficio:** Centraliza la lógica de seguridad. Si mañana cambia el método de autenticación, solo se modifica un archivo.

### B. Centralización de Credenciales (Token compartido)
**Cambio:** Se agregó `pbi_connections` como dependencia en el `__manifest__.py`.
- **¿Por qué?:** El sistema ya tenía un modelo robusto de gestión de tokens en el módulo de Power BI. Crear uno nuevo en Automatizaciones duplicaría el trabajo del administrador.
- **Razón del cambio:** Se reutilizó el modelo `pbi_connections.api.config`. Esto significa que **el mismo token** que se usa para Power BI puede usarse para el Bot de Ventas, simplificando la gestión de accesos.

---

## 3. Nuevas Funcionalidades Desarrolladas

### A. Servicio de Consulta de Órdenes (SalesOrderQueryService)
**Archivo:** `application/sales_orders/queries/sales_order_query_service.py`
- **¿Por qué?:** El bot no solo necesita crear órdenes, también necesita verificar si una orden existe, su estado (borrador, confirmado) o buscar pedidos por el teléfono del cliente.
- **Lo que se agregó:** Una implementación completa que permite filtrar órdenes por:
  - ID de la orden o Nombre (S00001).
  - ID del Cliente.
  - Teléfono o Móvil del Cliente (búsqueda inteligente).
  - Estado y rango de fechas.

### B. Interfaz de Configuración para el Bot
**Archivo:** `views/api_config_views.xml`
- **¿Por qué?:** Un programador o administrador necesita ver cuál es el token actual y qué endpoints están disponibles sin tener que leer el código.
- **Lo que se agregó:** Un nuevo menú en **Automatizaciones > Credenciales API Bot**. Esta vista permite:
  - Visualizar y copiar el Token de Acceso.
  - Regenerar el token en caso de brecha de seguridad.
  - Consultar una guía rápida de los 4 endpoints disponibles directamente en la pantalla.

---

## 4. Guía para Desarrolladores (Endpoints)

Todos los endpoints requieren el token y aceptan `POST` con un cuerpo JSON.

| Ruta | Uso |
|------|-----|
| `/api/automatizations/customers/query` | Identificar un cliente antes de vender. |
| `/api/automatizations/products/query` | Consultar catálogo y disponibilidad. |
| `/api/automatizations/sales-orders/query` | **(NUEVO)** Verificar historial o estado de pedidos. |
| `/api/automatizations/sales-orders/create` | Procesar la venta final. |

---

## 5. Notas para el Equipo de Despliegue
- Es necesario actualizar la lista de módulos en Odoo tras subir estos cambios debido a la nueva dependencia (`pbi_connections`) y la nueva vista XML.
- Los cambios están listos para ser "staged" y "committed" en la rama `dev-sales-sistem`.

---
