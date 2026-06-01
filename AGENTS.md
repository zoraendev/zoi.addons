# Reglas específicas para custom_addons

Todo cambio dentro de `custom_addons` debe respetar Odoo Community.

## Prioridades

- Mantener compatibilidad con Odoo.
- Evitar personalizaciones invasivas.
- No modificar comportamiento nativo si no es necesario.
- Usar XML, QWeb, Python, JS y SCSS siguiendo patrones de Odoo.
- Mantener nombres técnicos claros.
- Usar prefijo `zrn_` para clases CSS propias.

## UI

Las vistas deben verse como módulos internos de Odoo, no como landings.

Evitar:

- Degradados.
- Cards excesivas.
- Muchos bordes.
- Contenedores anidados.
- Textos decorativos.
- Espacios muertos.
- Estética de dashboard genérico de IA.

Preferir:

- Secciones compactas.
- Encabezados simples.
- Métricas claras.
- Tablas o bloques funcionales.
- Acciones visibles.
- Diseño sobrio.
- Acentos visuales de Zoraen solo donde aporten jerarquía.

## Código

No crear abstracciones innecesarias.

El código debe ser directo, mantenible y fácil de revisar.
