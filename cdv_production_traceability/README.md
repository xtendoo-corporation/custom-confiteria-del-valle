# Trazabilidad de Producción - Información adicional

## Descripción

Módulo completo de trazabilidad de producción para empresas del sector de confitería/panadería y parafarmacias, que incluye:

- Gestión de materias primas en uso
- Partes de producción con trazabilidad completa
- Lotes automáticos por fecha
- **UoM (Unidades de Medida) preferidas para Producción y Compra**

## Nueva funcionalidad: UoM Preferidas

### Problema que resuelve

En empresas multi-tienda (parafarmacias, confiterías) es común:
- Comprar productos en **cajas**
- Vender en **unidades**
- Fabricar/producir en **cajas**

Odoo estándar permite UoM de compra por proveedor, pero no una UoM preferida global para producción.

### Solución implementada

Este módulo añade dos campos nuevos en la ficha del producto:

1. **UdM preferida para Producción** (`uom_production_preferred_id`)
   - Se aplica automáticamente en:
     - Órdenes de fabricación (Manufacturing Orders)
     - Líneas de Lista de Materiales (BoM Lines)

2. **UdM preferida para Compra** (`uom_purchase_preferred_id`)
   - Para uso futuro (puede integrarse con módulos de compra)

### Características clave

✅ **Configuración simple**: Una sola vez en la ficha del producto
✅ **Aplicación automática**: Se aplica al crear MOs y BoMs
✅ **Validación estricta**: La UoM preferida debe estar en la misma categoría que la UoM base
✅ **No rompe estándar**: Si el campo está vacío, Odoo funciona como siempre
✅ **Respeta elección manual**: Si el usuario elige otra UoM compatible, se respeta

## Configuración

### 1. Configurar UoM preferida en el producto

1. Ir a **Inventario > Productos > Productos**
2. Abrir la ficha del producto
3. Ir a la pestaña **Inventario**
4. Buscar la sección **"Unidades de Medida Preferidas"**
5. Seleccionar:
   - **UdM preferida para Producción**: Por ejemplo, "Caja"
   - **UdM preferida para Compra**: Por ejemplo, "Caja" (opcional)

**Importante**: La UoM preferida debe pertenecer a la misma categoría que la UoM base del producto.

Ejemplo:
- UoM base: Unidad (Categoría: Unidades)
- UoM preferida válida: Caja, Docena, etc. (Categoría: Unidades)
- UoM preferida NO válida: Kilogramo (Categoría: Peso) ❌

### 2. Usar en Fabricación

#### Órdenes de Fabricación (MO)

Al crear una orden de fabricación:
1. Seleccionar el producto a fabricar
2. Si el producto tiene **UdM preferida para Producción**, se aplicará automáticamente
3. La cantidad se expresará en esa unidad

Ejemplo:
- Producto: Paracetamol 500mg
- UoM base: Unidad
- UoM preferida: Caja (12 unidades)
- Al crear MO → Se usará "Caja" automáticamente

#### Listas de Materiales (BoM)

Al añadir componentes a una BoM:
1. Seleccionar el producto componente
2. Si tiene **UdM preferida para Producción**, se aplicará automáticamente en la línea
3. Se puede cambiar manualmente si se necesita

## Validaciones

El módulo incluye validaciones estrictas para evitar errores:

### Constraint de categoría

```python
@api.constrains('uom_production_preferred_id', 'uom_id')
def _check_uom_production_preferred_category(self):
    """La UoM preferida debe estar en la misma categoría que la UoM base"""
```

**Mensaje de error si falla**:
```
La UdM preferida para Producción 'Kilogramo' debe pertenecer a la misma categoría
que la UdM base del producto 'Producto X'.

UdM base: Unidad (Categoría: Unidades)
UdM preferida: Kilogramo (Categoría: Peso)
```

### Warning en BoM Lines

Si el usuario selecciona manualmente una UoM de categoría incompatible en una línea de BoM, se muestra un warning:

```
⚠️ Categoría de UdM incompatible

La UdM seleccionada "Kilogramo" no pertenece a la misma categoría
que la UdM base del producto "Unidad".

Se recomienda usar una UdM de la categoría: Unidades
```

## Tests

El módulo incluye tests completos:

### Ejecutar todos los tests

```bash
# Desde la raíz de Odoo
./odoo-bin -c odoo.conf -d test_db -i cdv_production_traceability --test-enable --stop-after-init
```

### Ejecutar tests específicos

```bash
# Test de constraints
./odoo-bin -c odoo.conf -d test_db --test-tags=cdv_production_traceability.test_uom_production_preferred

# Test de BoM Lines
./odoo-bin -c odoo.conf -d test_db --test-tags=cdv_production_traceability.test_mrp_bom_line_uom

# Test de Manufacturing Orders
./odoo-bin -c odoo.conf -d test_db --test-tags=cdv_production_traceability.test_mrp_production_uom
```

### Tests incluidos

1. **test_uom_production_preferred.py**
   - Validación de categoría de UoM
   - UoM preferida vacía es válida
   - Error al usar categoría incorrecta

2. **test_mrp_bom_line_uom.py**
   - Aplicación automática en BoM Lines
   - Cambio de producto actualiza UoM
   - Producto sin UoM preferida usa base

3. **test_mrp_production_uom.py**
   - Aplicación en creación de MO
   - Onchange de producto
   - Respeto de UoM explícita
   - Write de producto actualiza UoM

## Instalación / Actualización

### Primera instalación

```bash
cd /ruta/a/odoo
./odoo-bin -c odoo.conf -d nombre_bd -i cdv_production_traceability
```

### Actualizar módulo existente

```bash
cd /ruta/a/odoo
./odoo-bin -c odoo.conf -d nombre_bd -u cdv_production_traceability
```

O desde Docker:

```bash
docker-compose run --rm odoo odoo -u cdv_production_traceability -d nombre_bd --stop-after-init
docker-compose restart odoo
```

## Casos de uso

### Caso 1: Parafarmacia multi-tienda

**Contexto**:
- Compran en cajas de 12 unidades
- Venden unidades individuales
- Producen en cajas

**Configuración**:
- Producto: Paracetamol 500mg
- UoM base: Unidad
- UoM preferida Producción: Caja (12 unidades)
- UoM preferida Compra: Caja (12 unidades)

**Resultado**:
- Órdenes de compra → Se sugiere "Caja"
- Órdenes de fabricación → Automáticamente en "Caja"
- Ventas → En "Unidades"

### Caso 2: Confitería/Panadería

**Contexto**:
- Producen en lotes de 100 unidades
- Venden en unidades o docenas

**Configuración**:
- Producto: Croissant
- UoM base: Unidad
- UoM preferida Producción: Lote (100 unidades)

**Resultado**:
- BoMs → Componentes en UoM preferida
- MOs → Producción en "Lotes"
- Ventas → Flexibilidad en unidades/docenas

## Arquitectura técnica

### Modelos extendidos

1. **product.template**
   - Campos: `uom_production_preferred_id`, `uom_purchase_preferred_id`
   - Constraints: Validación de categoría

2. **mrp.bom.line**
   - Onchange: `_onchange_product_id_uom_production_preferred`
   - Warning: `_onchange_product_uom_id_check_category`

3. **mrp.production**
   - Onchange: `_onchange_product_id_uom_production_preferred`
   - Override: `create()`, `write()`

### Flujo de datos

```
Producto configurado con UoM preferida
    ↓
Usuario crea BoM Line
    ↓
Onchange detecta producto
    ↓
Aplica UoM preferida automáticamente
    ↓
Usuario crea MO
    ↓
Create detecta producto
    ↓
Aplica UoM preferida automáticamente
    ↓
Conversiones automáticas en movimientos de stock
```

## Limitaciones conocidas

1. **Conversiones de UoM**: Las conversiones entre UoMs deben estar bien configuradas en Odoo
2. **Stock Moves**: Los movimientos de stock se convierten automáticamente, pero dependen de la configuración de Odoo
3. **Compras**: La integración con compras requiere módulos adicionales (no incluido en esta versión)

## Futuras mejoras

- [ ] Integración con módulo de compras (purchase)
- [ ] Sugerencia automática de UoM en órdenes de compra
- [ ] Dashboard de uso de UoM preferidas
- [ ] Reporte de productos sin UoM preferida configurada
- [ ] Validación de conversiones en movimientos de stock

## Soporte

Para soporte o consultas:
- Email: info@xtendoo.es
- Web: https://xtendoo.es

## Licencia

LGPL-3

## Créditos

Desarrollado por Xtendoo para el sector de confitería/panadería y parafarmacias.

