# Guía de desarrollo del repositorio

Este repositorio debe mantenerse con el máximo nivel de calidad técnica posible.

## Principios generales

- Todo el código Python debe respetar PEP 8.
- El código debe ser claro, legible, mantenible y explícito.
- Se deben evitar soluciones rebuscadas, duplicación innecesaria y complejidad
  accidental.
- Antes de introducir un cambio, revisar el estilo y patrones ya existentes en el
  módulo.
- No inventar arquitecturas ajenas a Odoo. Respetar siempre la forma estándar de
  trabajar del framework.

## Calidad obligatoria

- Todo cambio funcional debe incluir pruebas.
- No se debe entregar código si falla el lint, el formato o los tests.
- No reducir nunca la cobertura existente.
- El objetivo por defecto es mantener una cobertura mínima del 90%.
- Siempre que sea viable, cubrir también ramas lógicas relevantes, no solo caminos
  felices.

## Estilo de código

- Usar nombres descriptivos y consistentes.
- Preferir funciones cortas y responsabilidades claras.
- Evitar comentarios innecesarios que repitan el código.
- Añadir docstrings solo cuando aporten contexto útil.
- Mantener imports ordenados y sin dependencias no usadas.
- Evitar variables de una sola letra salvo casos triviales.

## Reglas específicas para Odoo

- Respetar la arquitectura estándar de modelos, vistas, seguridad y datos.
- No introducir lógica de negocio en lugares incorrectos si puede residir en modelos o
  servicios adecuados.
- Mantener separación clara entre lógica de negocio, capa de presentación y datos.
- Las personalizaciones deben ser compatibles con upgrades razonables.
- Evitar hacks frágiles o dependencias ocultas.
- Si se modifica comportamiento estándar, dejarlo claramente justificado.

## Testing

- Priorizar tests unitarios y de integración de valor real.
- Cubrir casos normales, casos límite y errores esperables.
- Siempre explicar qué se ha probado.
- Si no es posible automatizar una parte, indicarlo expresamente junto con la validación
  manual necesaria.

## Entrega esperada

Cada entrega debe incluir:

1. Resumen de cambios realizados.
2. Riesgos o impactos potenciales.
3. Tests añadidos o modificados.
4. Comandos de validación ejecutados.
5. Limitaciones o puntos pendientes, si existen.

## Comportamiento esperado al generar código

- No devolver código apresurado o incompleto como solución final.
- No asumir dependencias no declaradas.
- No añadir librerías externas sin justificación.
- Si hay varias alternativas, priorizar la más mantenible y alineada con Odoo.
- Si una decisión técnica implica riesgos, explicarlos claramente.
