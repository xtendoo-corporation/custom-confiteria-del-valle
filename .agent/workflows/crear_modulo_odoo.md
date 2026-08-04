---
description: Instrucciones y reglas constantes para crear un nuevo módulo en Odoo 19
---

1. **Nomenclatura**: Todos los nombres de tablas, modelos (`_name`), campos y lógica
   interna deben escribirse **siempre en inglés**.
2. **Traducciones**: Todo módulo debe generar y contener su traducción al **español**
   (archivo `es.po` en la carpeta `i18n`).
3. **Tests obligatorios**: Todos los módulos deben tener un archivo de test unitarios
   programado e integrado.
4. **Verificación**: Siempre, antes de dar el módulo por terminado, usa tu subagente de
   navegador para entrar en `http://localhost:19069`, instala el módulo y comprueba
   manualmente que la interfaz carga sin errores.
5. **Control de versiones**: Al terminar, haz siempre `git add`, `git commit` y
   `git push` a GitHub con el trabajo entregado.
