# Informe de Entrega - Capa de Decision

## 1. Objetivo de la entrega

Esta entrega consolida una arquitectura de addons orientada a separar tres capas del negocio dentro de Odoo:

- `zrn_commercial`: capa comercial operativa.
- `zrn_planning`: capa de planeacion operativa.
- `zrn_analitics`: capa de decision, analisis y lectura ejecutiva.

La intencion de esta separacion es que la empresa no tome decisiones a partir de datos dispersos, reportes manuales o pantallas operativas mezcladas con analitica, sino a partir de una estructura donde cada addon cumple una funcion concreta dentro del flujo de gestion.

## 2. Criterio funcional de la capa de decision

La capa de decision no se limita a mostrar indicadores. Su funcion es convertir datos operativos en contexto accionable para direccion, gerencias y responsables de area.

Las necesidades que esta capa busca satisfacer son:

- centralizar informacion clave en un solo punto de consulta;
- reducir tiempo de lectura entre ventas, compras, inventario y reclutamiento;
- detectar riesgos, desviaciones y oportunidades mas rapido;
- facilitar comparaciones por marca, canal, cliente, producto y PDV;
- apoyar decisiones tacticas y estrategicas sin depender de hojas externas;
- conectar la operacion diaria con una lectura ejecutiva clara.

## 3. Segmentacion de addons y funcion de cada uno

### 3.1 `zrn_commercial`

`zrn_commercial` resuelve la capa comercial operativa. Su papel no es ser el centro analitico, sino estructurar la base comercial que luego alimenta los hubs y reportes.

Funciones principales:

- administracion de marcas comerciales propias;
- administracion de canales comerciales;
- clasificacion comercial de clientes, PDVs, prospectos y oportunidades;
- consistencia de portafolio por marca;
- preparacion de la base de datos para lectura por marca, canal y cobertura.

Valor que aporta:

- ordena la operacion comercial con una taxonomia propia de Zoraen;
- evita analizar ventas con clasificaciones ambiguas o incompletas;
- hace posible que analytics lea el negocio con el mismo criterio con el que comercial lo opera.

Funcion que agiliza:

- organizacion de cartera, pipeline, canales y portafolio sin depender de clasificaciones nativas insuficientes.

Decisiones que ayuda a tomar:

- en que marcas concentrar esfuerzo comercial;
- que canales tienen mejor adopcion por marca;
- donde hay cuentas o PDVs mal clasificados o sin cobertura clara;
- como separar crecimiento real de crecimiento por mezcla de cartera.

### 3.2 `zrn_planning`

`zrn_planning` cubre la planeacion operativa. Aqui entra la generacion de planes y la lectura de ejecucion futura.

Funciones principales:

- planeacion de produccion;
- planeacion de abastecimiento;
- planeacion logistica;
- capas de plan desacopladas de la ejecucion real;
- construccion de planes sobre demanda, insumos y trazabilidad.

Dentro de esta capa entra la generacion de escenarios de planeacion. Esto significa que los escenarios no se reportan como una funcionalidad aislada de analytics, sino como parte del trabajo de planning sobre fechas, demanda, abastecimiento y capacidad.

Valor que aporta:

- permite proyectar antes de comprometer inventario, compras o fabricacion;
- mejora la trazabilidad entre necesidad, suministro y liberacion;
- reduce el riesgo de tomar decisiones operativas directamente sobre la ejecucion real.

Funcion que agiliza:

- evaluacion de planes antes de liberar ordenes reales;
- lectura de necesidades de insumos;
- coordinacion entre compras, produccion y logistica.

Decisiones que ayuda a tomar:

- cuando producir;
- que abastecer primero;
- que pedidos cubrir con stock y cuales requieren compra o fabricacion;
- que cambios de demanda obligan a revisar el plan.

### 3.3 `zrn_analitics`

`zrn_analitics` es la capa de decision. Aqui viven los hubs, la reporteria, el procesamiento analitico y las metricas avanzadas.

Funciones principales:

- hubs por dominio de negocio;
- reporteria dinamica;
- visualizacion de metricas avanzadas;
- consolidacion de ventas, compras, inventario, clientes, productos y RRHH;
- procesamiento de datos para exploracion y comparacion;
- lectura ejecutiva sobre la base construida por comercial y la operacion capturada por Odoo.

En esta capa tambien entra lo que internamente se ha referido como ZAM. En la entrega actual, esa necesidad no se maneja como un modulo separado, sino como parte del ecosistema de hubs de `zrn_analitics`, donde la reporteria avanzada y los dashboards dinamicos se expresan a traves de vistas filtrables y comparativos de negocio.

Valor que aporta:

- transforma datos sueltos en una vista de negocio entendible;
- reduce friccion entre revision operativa y lectura gerencial;
- permite priorizar acciones con base en evidencia y no solo en percepcion.

Funcion que agiliza:

- lectura consolidada del negocio;
- deteccion de tendencias;
- revision de desviaciones;
- identificacion de cuentas, productos, PDVs o procesos que requieren accion.

Decisiones que ayuda a tomar:

- donde crecer;
- donde corregir;
- donde hay riesgo de caida, sobrestock, baja cobertura o baja rotacion;
- donde conviene profundizar una revision comercial, financiera, operativa o de RRHH.

## 4. Como la entrega satisface cada necesidad de la capa de decision

### 4.1 Centralizacion de informacion clave

Necesidad:

- consultar ventas, compras, inventario, productos, clientes, PDVs y RRHH sin saltar entre multiples menus operativos.

Como se satisface:

- `zrn_analitics` concentra hubs por dominio;
- cada hub lee informacion desde fuentes operativas ya existentes;
- la lectura se presenta en forma de KPIs, distribuciones, rankings, alertas y tablas accionables.

Valor:

- reduce tiempos de revision;
- permite a direccion entender situacion actual sin reconstruir datos manualmente.

### 4.2 Planeacion con base en datos reales

Necesidad:

- decidir produccion, compras y abastecimiento usando demanda y consumo reales.

Como se satisface:

- `zrn_planning` trabaja como capa de planeacion desacoplada de la ejecucion;
- los escenarios de planeacion se entienden dentro de esta misma capa;
- `zrn_analitics` complementa con lectura de tendencias y contexto para priorizar.

Valor:

- evita decisiones apresuradas sobre documentos operativos;
- mejora la coordinacion entre demanda, capacidad y suministro.

### 4.3 Reporterias avanzadas y dashboards dinamicos

Necesidad:

- contar con vistas comparativas configurables y no solo con reportes estaticos.

Como se satisface:

- la reporteria avanzada tipo ZAM queda absorbida dentro de los hubs de `zrn_analitics`;
- los hubs permiten filtros por periodo, marca, categoria, canal y otras dimensiones del negocio;
- el procesamiento analitico abre espacio para consultas temporales, comparaciones y simulaciones de lectura.

Valor:

- habilita analisis mas flexible;
- permite responder preguntas de negocio sin depender de desarrollos nuevos para cada consulta.

### 4.4 Metricas avanzadas por dominio

Necesidad:

- ver metricas que no viven naturalmente en una sola pantalla operativa.

Como se satisface:

- las metricas avanzadas se concentran dentro de los hubs de `zrn_analitics`;
- el analisis se organiza por dominio: comercial, financiero, operaciones, PDV/cobertura y RRHH.

Valor:

- cada gerencia puede leer su area sin perder coherencia con el resto del negocio;
- se reducen interpretaciones cruzadas o calculos paralelos fuera de Odoo.

### 4.5 Sustitucion de rendimiento por empleado por contenido RRHH

Necesidad:

- la presentacion original contemplaba una metrica de rendimiento por empleado, pero en la evaluacion del negocio se determino que no era conveniente por el tamano del equipo y por la division funcional entre areas.

Como se satisface:

- ese punto se sustituyo por el contenido del Hub RRHH en `zrn_analitics`;
- en lugar de forzar una metrica debil o poco representativa, se incorporo una lectura mas util para la toma de decisiones de reclutamiento;
- el hub RRHH trabaja con solicitudes, predictor, checklist de entrevista y patrones validados.

Valor:

- la lectura pasa de una metrica de baja relevancia estadistica a una herramienta de evaluacion de riesgo de candidatos;
- se mejora la calidad de la decision donde hoy si existe una necesidad directa de filtro y validacion.

Funcion que agiliza:

- revision de solicitudes activas;
- evaluacion previa a entrevistas o poligrafo;
- seguimiento de alertas de reclutamiento.

Decisiones que ayuda a tomar:

- que candidatos requieren validacion profunda;
- en que casos conviene profundizar entrevista;
- que solicitudes tienen combinacion de senales de mayor riesgo;
- donde RRHH debe enfocar tiempo antes de avanzar en costo de pruebas o contratacion.

## 5. Valor concreto de los hubs de `zrn_analitics`

## 5.1 Hub Comercial

Necesidad que cubre:

- entender desempeno de ventas, mezcla de marcas, comportamiento de clientes, PDVs y portafolio.

Valor:

- muestra donde se vende, que tan concentrada esta la venta y que productos sostienen el negocio.

Funcion que agiliza:

- lectura de revenue, pedidos, ticket, mix de marcas, top clientes, cobertura y tendencias.

Decisiones que apoya:

- priorizacion de marcas;
- expansion o correccion de cobertura;
- foco comercial por cliente, canal o categoria;
- revision de surtido y portafolio.

## 5.2 Hub Financiero

Necesidad que cubre:

- leer impacto economico de ventas, compras, inventario y margen teorico desde una vista agregada.

Valor:

- acerca la lectura financiera a la operacion comercial y de inventario.

Funcion que agiliza:

- revision de revenue, costo estandar, backlog, exposicion y comparativos.

Decisiones que apoya:

- priorizar categorias o marcas con mejor aporte;
- revisar riesgo de margen;
- identificar presion de compras o inventario sobre caja.

## 5.3 Hub Operaciones

Necesidad que cubre:

- traducir movimiento comercial e inventario en lectura operativa de demanda, rotacion y abastecimiento.

Valor:

- conecta venta con capacidad de respuesta.

Funcion que agiliza:

- lectura de cobertura, ritmo de salida, rotacion y alertas operativas.

Decisiones que apoya:

- reabastecimiento;
- control de productos lentos o criticos;
- priorizacion operativa por marca o canal.

## 5.4 Hub PDV / Cobertura

Necesidad que cubre:

- entender presencia real en puntos de venta, dispersion de cartera y senales de caida o dormancia.

Valor:

- baja el analisis del nivel cuenta al nivel punto de ejecucion.

Funcion que agiliza:

- deteccion de PDVs dormantes, caidas de venta, altas recientes y bajo sell-through.

Decisiones que apoya:

- reactivacion comercial;
- visitas y seguimiento;
- redefinicion de cobertura;
- ajustes de surtido por PDV.

## 5.5 Hub RRHH

Necesidad que cubre:

- evaluar solicitudes activas con una mirada de riesgo y seguimiento.

Valor:

- da estructura a una evaluacion que antes podia quedar dispersa entre criterio humano, notas sueltas y pasos manuales.

Funcion que agiliza:

- consolidacion de predictor;
- checklist de entrevista;
- patrones validados;
- historico de solicitudes con alertas.

Decisiones que apoya:

- avanzar o no a etapas de validacion;
- justificar entrevistas ampliadas;
- detectar solicitudes que requieren mayor revision antes de contratar.

## 6. Como se segmenta con `zrn_commercial`

La segmentacion entre `zrn_commercial` y `zrn_analitics` es clave para la calidad del dato.

`zrn_commercial` define:

- la marca comercial;
- el canal comercial;
- la relacion entre cartera, PDVs y estructura comercial;
- el portafolio que da contexto al negocio.

`zrn_analitics` consume esa estructura para:

- agrupar ventas por marca;
- leer cobertura por canal;
- comparar clientes y PDVs con criterio comercial consistente;
- construir hubs que hablen el mismo lenguaje que usa el equipo comercial.

En otras palabras:

- `zrn_commercial` ordena la operacion;
- `zrn_analitics` convierte ese orden en lectura ejecutiva.

Sin `zrn_commercial`, analytics perderia consistencia en cortes por marca, canal y cobertura. Sin `zrn_analitics`, comercial seguiria teniendo estructura, pero no una capa de decision consolidada para direccion.

## 7. Como se articula con planning

La capa de decision no reemplaza planning. Ambas se complementan.

`zrn_planning` se usa para construir y evaluar planes operativos.

`zrn_analitics` se usa para entender el contexto que justifica esos planes:

- tendencia de ventas;
- concentracion de demanda;
- cobertura de inventario;
- comportamiento por cliente, canal y PDV;
- alertas operativas que ayudan a decidir que priorizar.

Asi, los escenarios de plan viven en planning, mientras que las metricas avanzadas y la lectura transversal del negocio viven en analytics.

## 8. Conclusiones de valor de negocio

La entrega no consiste solo en nuevos menus o dashboards. Consiste en una estructura funcional donde:

- la operacion comercial queda ordenada en `zrn_commercial`;
- la planeacion operativa queda controlada en `zrn_planning`;
- la capa de decision queda centralizada en `zrn_analitics`.

Esto aporta valor porque:

- reduce incertidumbre;
- mejora la trazabilidad entre dato operativo y decision;
- facilita comparaciones reales entre marcas, canales, clientes, productos y PDVs;
- reemplaza metricas poco utiles por analisis mas pertinentes, como el hub RRHH;
- permite a la empresa pasar de revisar datos a decidir con contexto.

## 9. Resumen ejecutivo

La necesidad de la capa de decision queda satisfecha mediante una arquitectura segmentada:

1. `zrn_commercial` prepara la estructura operativa del negocio.
2. `zrn_planning` resuelve la planeacion y los escenarios de plan.
3. `zrn_analitics` concentra hubs, reporteria avanzada, metricas avanzadas y lectura para toma de decisiones.

Dentro de esta logica:

- ZAM queda absorbido por los hubs de `zrn_analitics`;
- las metricas avanzadas quedan dentro de los hubs;
- la generacion de escenarios se reporta como parte de planning;
- el punto de rendimiento por empleado se sustituye por el Hub RRHH por ser mas util y representativo para la realidad actual de Zoraen.
