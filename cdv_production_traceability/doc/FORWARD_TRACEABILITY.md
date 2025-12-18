# Informe de Trazabilidad hacia Adelante

## Descripción

El **Informe de Trazabilidad hacia Adelante** (Forward Traceability) permite rastrear en qué productos finales se ha utilizado un lote específico de materia prima.

Este informe es complementario al **Informe de Trazabilidad** estándar (hacia atrás), que permite ver qué materias primas se utilizaron para fabricar un producto final.

## Casos de uso

- **Retirada de productos**: Si se detecta un problema con un lote de materia prima, identificar rápidamente todos los productos finales que la contienen
- **Inspecciones sanitarias**: Demostrar qué productos se elaboraron con materias primas específicas
- **Control de calidad**: Rastrear el uso de lotes de materias primas a lo largo del tiempo
- **Gestión de stock**: Conocer el consumo de materias primas por producto final

## ¿Cómo funciona?

### 1. Datos necesarios

Para que el informe funcione correctamente, necesitas:

- **Materias primas en uso**: Registros de cuándo se puso en producción cada materia prima con su lote
- **Partes de producción**: Albaranes de entrada marcados como "Es entrada de producción"
- **Listas de materiales (BoM)**: Definir qué materias primas lleva cada producto final

### 2. Proceso de cálculo

El informe realiza los siguientes pasos:

1. Busca todos los períodos en los que la materia prima seleccionada estuvo en uso
2. Para cada período de uso, busca los partes de producción que se realizaron
3. Verifica si el producto final incluye esa materia prima en su BoM
4. Genera un listado de todos los productos finales fabricados con esa materia prima

## Acceso al informe

### Desde el menú

1. Ir a **Producción > Informes > Trazabilidad hacia adelante**
2. Seleccionar la materia prima
3. Seleccionar el lote de la materia prima
4. Definir el rango de fechas de búsqueda
5. Hacer clic en **Calcular trazabilidad**

### Desde la materia prima en uso

1. Ir a **Producción > Materias primas > Materias primas en uso**
2. Abrir un registro de materia prima en uso
3. Hacer clic en el botón inteligente **Trazabilidad hacia adelante**
4. El informe se abrirá con los datos precargados
5. Ajustar el rango de fechas si es necesario
6. Hacer clic en **Calcular trazabilidad**

## Resultados del informe

### Estadísticas

El informe muestra:

- **Total de productos finales diferentes**: Cuántos productos distintos se fabricaron
- **Total de producciones**: Número de veces que se produjeron productos con esta materia prima
- **Total de unidades producidas**: Suma de todas las unidades fabricadas

### Período de uso

Muestra cuándo se puso en uso la materia prima por primera vez y cuándo se finalizó su uso (si aplica).

### Detalle de productos finales

Para cada producción muestra:

- **Fecha de producción**
- **Producto final fabricado**
- **Lote del producto final**
- **Cantidad producida**
- **Cantidad de materia prima por unidad** (según BoM)
- **Cantidad total de materia prima utilizada** (calculada)
- **Período de uso de la materia prima** (cuándo estuvo en producción)

## Exportación

### PDF

Haz clic en **Imprimir PDF** para generar un informe PDF profesional con:

- Información de la materia prima y lote rastreado
- Estadísticas resumidas en tarjetas visuales
- Tabla detallada de todos los productos finales
- Totales calculados

El PDF es ideal para:
- Auditorías sanitarias
- Informes de calidad
- Documentación de trazabilidad
- Archivo histórico

## Ejemplo práctico

### Escenario: Retirada de un lote de harina

1. **Problema detectado**: El proveedor notifica que el lote 123456 de harina puede estar contaminado

2. **Acción**:
   - Ir a **Producción > Informes > Trazabilidad hacia adelante**
   - Seleccionar producto: "Harina de trigo"
   - Seleccionar lote: "123456"
   - Fechas: Desde que se recibió hasta hoy
   - Calcular trazabilidad

3. **Resultado**: El informe muestra que el lote se usó en:
   - 50 unidades de Pan blanco (lote 181224)
   - 30 unidades de Bizcocho (lote 181224)
   - 25 unidades de Galletas (lote 191224)

4. **Acción correctiva**: Con esta información se pueden retirar específicamente estos productos del mercado

## Diferencias con el informe de trazabilidad estándar

| Característica | Trazabilidad estándar (atrás) | Trazabilidad hacia adelante |
|----------------|-------------------------------|----------------------------|
| Punto de partida | Producto final | Materia prima |
| Pregunta que responde | ¿Qué materias primas tiene? | ¿En qué productos se usó? |
| Filtro principal | Producto terminado + lote | Materia prima + lote |
| Uso típico | Ver composición de un producto | Rastrear uso de una materia prima |

## Notas técnicas

- El informe solo considera producciones completadas (`state = 'done'`)
- Solo muestra producciones donde la materia prima está en la BoM del producto final
- Considera los períodos de uso de la materia prima (date_from - date_to)
- Si una materia prima no tiene fecha de fin (`date_to = False`), se considera aún en uso

## Requisitos

- Módulo: `cdv_production_traceability`
- Permisos: Usuario de producción o superior
- Datos necesarios:
  - Materias primas en uso registradas
  - BoM configuradas
  - Partes de producción completados

