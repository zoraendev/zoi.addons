# Contexto del proyecto

Estoy trabajando en un addon de Odoo 17 llamado Zoraen Analytics.

El objetivo del addon NO es operar procesos de negocio como ventas, compras, fabricación, inventario, rutas o logística.

El objetivo es construir dashboards analíticos para toma de decisiones usando información existente en Odoo y, cuando aplique, fuentes externas o datos complementarios.

Actualmente estoy migrando una maqueta HTML entregada por el cliente hacia una vista integrada dentro de Odoo.

El alcance actual es únicamente la tab "Cobertura" dentro del Hub Comercial.

# Objetivo actual

Migrar/adaptar la tab "Cobertura" del HTML estático hacia el addon de Odoo, manteniendo la estructura conceptual de la maqueta, pero integrándola correctamente al backend de Odoo.

La vista debe funcionar como dashboard analítico de cobertura comercial, distribución, puntos de venta, clientes, canales, oportunidades y riesgo comercial.

No debe convertirse en un módulo operacional.

# Concepto funcional de Cobertura

La tab Cobertura debe responder preguntas como:

- Qué canales tienen mejor cobertura comercial.
- Cuántos PDVs o clientes están activos.
- Cuántos PDVs han facturado en el período.
- Qué canales tienen mayor revenue.
- Qué canales tienen bajo nivel de penetración.
- Qué productos o SKUs están llegando a más clientes.
- Qué clientes importantes tienen huecos de portafolio.
- Qué clientes A/B están en riesgo.
- Dónde hay oportunidad comercial no capturada.
- Qué datos vienen de Odoo y qué datos pueden venir de fuentes externas.

# Definiciones importantes

PDV significa Punto de Venta o cliente comercial analizado.

Canal representa una agrupación comercial como:

- Walmart/Paiz
- Mass
- PUMA Súper 7
- B3
- Food Service
- Distribuidor
- La Torre
- GTA / MSF
- Circle K

White space significa oportunidad comercial no capturada.

Ejemplo:

Un canal tiene muchos PDVs potenciales, pero pocos han facturado.

O un cliente importante debería comprar ciertos SKUs clave, pero no los está comprando.

Holes de portafolio significa productos clave ausentes en clientes importantes.

Ejemplo:

Cliente A compra algunos productos, pero no compra otros SKUs clave que debería tener en su portafolio.

Cliente A/B en riesgo significa cliente importante con señales de caída comercial.

Ejemplo:

- Reducción de revenue.
- Menor frecuencia de compra.
- Menos SKUs comprados.
- Meses sin compra.
- Pérdida de productos principales.

# Alcance de la tab

La tab Cobertura debe incluir como mínimo:

1. Cards superiores de resumen

- PDVs en universo
- PDVs facturados YTD
- White space ponderado
- Clientes A/B con holes
- Clientes A/B en riesgo

2. Tabla de cobertura por canal

Columnas sugeridas:

- Canal / operador
- Activos
- Red total
- % cobertura
- White space
- Revenue
- % mix
- Ticket / PDV
- Penetración

3. Bloque de universo PDV

Debe mostrar resumen de PDVs por cadena, operador, municipio o zona.

Por ahora puede ser visual y con datos mockeados.

No crear mapa real todavía salvo que ya exista estructura preparada.

4. Matriz canal x sub-marca

Debe cruzar canales contra sub-marcas o marcas comerciales.

Debe ayudar a visualizar qué marcas tienen presencia o revenue por canal.

5. Distribución por SKU

Debe mostrar productos/SKUs con:

- SKU
- Sub-marca
- Revenue
- Número de PDVs
- % PDVs
- Penetración
- Canales

6. Holes de portafolio

Debe mostrar clientes A/B que no compran ciertos SKUs clave.

Puede representarse con tabla de checks y equis.

Debe ser analítico, no operacional.

7. Clientes A/B en riesgo

Debe mostrar clientes importantes con señales de riesgo.

Columnas sugeridas:

- Cliente / PDV
- Canal
- ABC
- Segmento
- Revenue YTD
- Recencia
- Meses activo
- Producto principal
- Acción sugerida

8. Notas y fuentes

Debe mostrar trazabilidad del dato:

- Qué viene de Odoo.
- Qué viene de investigación externa.
- Qué está estimado.
- Qué está pendiente de validar.

# Datos que sí pueden venir de Odoo

Priorizar métricas calculables desde Odoo:

- Facturas
- Líneas de factura
- Clientes
- Productos
- Revenue por cliente
- Revenue por canal
- Revenue por SKU
- SKUs vendidos por cliente
- Última fecha de compra
- Clientes con compra en período
- Clientes sin compra reciente
- Productos vendidos por cliente
- Marcas o sub-marcas asociadas a productos
- Clasificación comercial de clientes

Modelos Odoo relevantes:

- account.move
- account.move.line
- res.partner
- product.template
- product.product
- sale.order
- sale.order.line

# Datos que NO deben asumirse como nativos de Odoo

No asumir que Odoo ya tiene:

- Universo total GPS real
- Todos los PDVs del mercado
- Datos de competencia
- Sell-out real del retailer
- Presencia física en góndola
- Investigación externa validada
- Potencial exacto de mercado
- Ubicación GPS limpia de todos los clientes

Esos datos pueden quedar como placeholders o estructura preparada para fase futura.

# Reglas importantes

No crear rutas comerciales.
No crear gestión de vendedores.
No crear operaciones de entrega.
No crear flujos de visita a clientes.
No crear procesos de venta.
No crear procesos de inventario.
No crear procesos de fabricación.
No modificar flujos nativos de Odoo si no es necesario.
No inventar lógica operacional.
No mezclar esta tab con la tab Portafolio.
No implementar otras tabs.
No hacer cambios grandes fuera de Cobertura.
No convertir la maqueta en una landing page.
No usar degradados excesivos.
No usar muchos contenedores anidados.
No usar bordes demasiado redondeados.
No agregar textos largos que ocupen espacio sin aportar análisis.
No romper la estética base de Odoo.

# Enfoque visual

La vista debe sentirse integrada a Odoo, pero con identidad visual de Zoraen.

Debe verse como herramienta interna ejecutiva de BI.

Estilo esperado:

- Limpio
- Compacto
- Gerencial
- Tablas claras
- Cards funcionales
- Métricas visibles
- Colores usados solo para alertas, riesgo, cobertura y énfasis
- Espaciado controlado
- Bordes sutiles
- Sin decoración innecesaria

# Arquitectura esperada

Usar la estructura normal de un addon Odoo 17.

La parte visual debe estar en OWL / JS / XML / SCSS cuando aplique.

La data debe estar separada de la estructura visual.

Por ahora se permite usar datos mockeados, pero deben quedar organizados para reemplazarse luego por una llamada RPC a métodos Python.

La vista debe quedar preparada para consumir un método Python del addon, por ejemplo:

get_coverage_dashboard_data

Ese método debe devolver una estructura organizada como:

- summary_cards
- coverage_by_channel
- pdv_universe
- channel_brand_matrix
- sku_distribution
- portfolio_holes
- clients_at_risk
- notes_sources

# Forma de trabajo

Antes de hacer cambios grandes:

1. Revisar la estructura actual del addon.
2. Identificar dónde está el Hub Comercial.
3. Identificar dónde se renderizan las tabs.
4. Trabajar únicamente la tab Cobertura.
5. Mantener el patrón actual del proyecto.
6. Migrar primero la estructura visual.
7. Separar estilos en SCSS.
8. Separar data mockeada en una función o archivo aparte.
9. Evitar meter todo en un solo archivo gigante.
10. Hacer cambios incrementales y fáciles de revisar.

# Resultado esperado

La tab Cobertura debe verse como una versión integrada a Odoo de la maqueta HTML del cliente.

Debe enfocarse únicamente en análisis de cobertura comercial, distribución, clientes, canales, oportunidades y riesgo.

Debe quedar preparada para conectarse a datos reales de Odoo, pero sin crear procesos operacionales nuevos.
