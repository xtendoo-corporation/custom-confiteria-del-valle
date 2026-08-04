# Guía de contribución

## Objetivo

Mantener este repositorio con un nivel alto de calidad, legibilidad, estabilidad y
cobertura de pruebas.

## Reglas generales

- Seguir PEP 8.
- Escribir código claro y mantenible.
- Evitar duplicidades y complejidad innecesaria.
- Respetar la arquitectura y convenciones de Odoo.

## Calidad obligatoria

Antes de dar un cambio por válido deben pasar:

- Formato
- Lint
- Tests
- Cobertura mínima

## Comandos recomendados

```bash
ruff check .
ruff format --check .
pytest
```
