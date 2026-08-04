# Instrucciones del repositorio para asistencia de código

## Calidad mínima exigida

- Todo código Python debe seguir PEP 8.
- Mantener alta legibilidad, bajo acoplamiento y responsabilidad clara por función o
  clase.
- No reducir la cobertura de test existente.
- La cobertura mínima objetivo es del 90%.

## Antes de proponer cambios

- Revisar la estructura y convenciones ya existentes en el módulo.
- Respetar siempre el patrón estándar de Odoo.
- No inventar arquitecturas paralelas innecesarias.

## Tests

- Todo cambio funcional debe incluir tests.
- Cubrir casos normales, casos límite y errores esperables.
- Explicar siempre qué se valida y cómo.

## Estilo

- Usar nombres descriptivos.
- Evitar comentarios redundantes.
- Evitar complejidad accidental.
- Mantener imports ordenados y sin elementos no usados.

## Restricciones

- No añadir nuevas dependencias sin necesidad clara.
- No dar por bueno código que no pase lint, formato y tests.
- No introducir hacks frágiles ni atajos que dificulten mantenimiento futuro.

## Contexto Odoo

- Respetar modelos, vistas, seguridad, datos y flujos estándar del framework.
- Mantener una separación adecuada entre lógica de negocio, interfaz y configuración.
- Favorecer soluciones robustas, upgrade-friendly y fáciles de mantener.
