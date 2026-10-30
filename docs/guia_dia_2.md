# Día 2: formularios de productos y carrito de ventas

Este capítulo describe el hito del Día 2. La versión actual también implementa el [Día 3](guia_dia_3.md), que añade confirmación de venta y descuento de stock.

El objetivo de esta etapa es administrar productos y preparar una venta. Ya puedes crear, editar y eliminar productos en SQLite, buscar el catálogo y manejar cantidades y totales del carrito. Procesar una venta y descontar existencias corresponde al Día 3.

## 1. Abrir la versión nueva

Cierra la ventana anterior si sigue abierta. Desde PowerShell, en la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe main.py
```

Ahora hay dos pestañas: **Inventario** y **Punto de venta**. No necesitas reinstalar nada. Los productos guardados en el Día 1 se conservan: no se borraron tablas ni se sustituyó la base.

## 2. Entender la organización

| Archivo | Responsabilidad |
| --- | --- |
| `app/validation.py` | Convertir texto a precios/cantidades válidos y comunicar errores. |
| `app/inventory.py` | Crear, consultar, actualizar y eliminar productos usando SQL. |
| `app/product_dialog.py` | Un formulario que se usa tanto para crear como para editar. |
| `app/sales.py` | Mantener las líneas del carrito y aplicar sus reglas. |
| `app/pos_ui.py` | Mostrar resultados de búsqueda, cantidades y totales. |
| `app/ui.py` | Coordinar las pestañas, acciones del inventario y cierre. |

El flujo de guardar un producto es:

```text
Formulario → texto de los campos → validación/conversión
           → función de inventario → SQL parametrizado → SQLite
           → cierre del formulario → actualización de listados
```

El formulario muestra errores; la lógica de inventario decide si los datos son válidos. Así las reglas también se aplican si mañana llamas al CRUD desde otro script.

## 3. Crear un producto

En **Inventario**, pulsa **Nuevo producto**. Para practicar, utiliza un código que no exista, por ejemplo:

| Campo | Valor |
| --- | --- |
| Código | `TECNICA02` |
| Nombre | `Cuaderno` |
| Precio | `10,50` |
| Stock | `5` |

Pulsa **Guardar producto**. La ventana se cierra si se guardó bien y el inventario vuelve a leer SQLite. Cancelar o cerrar el formulario no guarda nada.

En `ProductDialog`, cada entrada está conectada a una `StringVar`. El método `save()` obtiene sus textos, llama a `create_product()` o `update_product()` según el caso y mantiene el diálogo abierto si hay un error. El mensaje aparece al pie y, cuando corresponde, se enfoca el campo inválido.

La creación usa esta consulta:

```sql
INSERT INTO productos (codigo, nombre, precio, stock)
VALUES (?, ?, ?, ?)
```

Los signos `?` son marcadores para parámetros. Los valores se envían separados de la instrucción SQL. Un nombre con una comilla sigue siendo texto, no una parte de la consulta.

La función devuelve el identificador que SQLite asignó a la nueva fila. La conexión se confirma al terminar el bloque sin errores y luego se cierra.

## 4. Validar antes de guardar

Normalizar significa llevar una entrada a una forma consistente. Para el código hacemos `strip().upper()`: ` tecnica02 ` se convierte en `TECNICA02`. El nombre usa `strip()` para quitar espacios de los extremos.

Reglas del formulario:

- Código y nombre obligatorios.
- Código único. Intentar crear `tecnica02` después de `TECNICA02` se rechaza.
- Precio estrictamente positivo, con hasta dos decimales; admite coma o punto decimal y no admite separadores de miles.
- Stock entero no negativo; cero representa un producto agotado.
- Valores persistidos dentro del rango de enteros de SQLite.

Ejemplos válidos de precio: `10`, `10,5`, `10.50`. Ejemplos inválidos: `0`, `-1`, `10,555`, `1.000,50`, `NaN` y `1e3`.

`parse_price()` primero comprueba el formato, después usa `Decimal` y finalmente convierte a centavos enteros. `10,50` se guarda como `1050`. No se usa `float` para la entrada ni para los cálculos del carrito.

El texto para editar es distinto del texto para mostrar: `price_to_input(850050)` produce `8500,50`, mientras que `format_price(850050)` produce `8.500,50`. Precargar el segundo en el formulario sería un error, porque el formulario no acepta separadores de miles.

La base conserva sus propias restricciones `UNIQUE`, `NOT NULL` y `CHECK`. Las validaciones de Python mejoran el mensaje para el usuario; las restricciones de SQLite protegen el almacenamiento.

## 5. Editar un producto

Selecciona la fila de `TECNICA02` y pulsa **Editar**, o haz doble clic. El mismo formulario se abre precargado. Cambia el nombre a `Cuaderno universitario` y el stock a `6`; conserva el precio `10,50`.

La edición utiliza el ID interno, no el código editable:

```sql
UPDATE productos
SET codigo = ?, nombre = ?, precio = ?, stock = ?
WHERE id = ?
```

**La condición `WHERE id = ?` es fundamental:** limita la modificación al producto seleccionado. Cambiar el código no crea una nueva fila ni modifica el ID.

Si intentas usar el código de otro producto, se conserva la información anterior y aparece un error. Si otro proceso eliminó el producto, se informa que ya no existe. Cancelar conserva los datos previos.

## 6. Buscar productos

En Inventario, escribe parte del código o nombre y pulsa **Buscar** o Enter. Dejar el campo vacío muestra todo. Los conteos corresponden al listado mostrado.

Para el tamaño de este MVP se lee el catálogo y se filtra con `casefold()` de Python, que compara texto sin distinguir mayúsculas y también funciona con caracteres como la É. `CAFÉ` encuentra `Café`. Los acentos sí importan: `cafe` no es igual a `café`.

La búsqueda es literal: un `%` no es un comodín. Con un catálogo grande moveríamos búsqueda y paginación a la base de datos; esa optimización no es necesaria para esta primera versión.

## 7. Agregar productos al carrito

Abre **Punto de venta**. Puedes:

1. Escribir el código exacto `TECNICA02` y pulsar Enter. Se agrega una unidad y el campo queda listo para otro código.
2. Buscar `Cuaderno`, seleccionar el resultado y pulsar **Agregar al carrito**, hacer doble clic o usar Enter en la tabla de resultados.

Un lector de códigos que funcione como teclado y envíe Enter puede utilizar el primer flujo; no se ha probado hardware específico.

Al agregar el mismo producto dos veces, aparece una sola línea con cantidad dos. Con el ejemplo anterior, el subtotal es **21,00**. El stock de SQLite sigue siendo seis.

El carrito se guarda en un diccionario de Python indexado por ID de producto. Así es fácil localizar una línea existente y acumular su cantidad. Cada línea es un `CartItem` inmutable con ID, código, nombre, precio unitario y cantidad. Para cambiarla, la clase crea una nueva línea después de validar.

El carrito se conserva al cambiar de pestaña porque ambas vistas pertenecen a la misma aplicación y comparten la misma instancia de `Cart`.

## 8. Cambiar cantidades y calcular el total

Selecciona la línea del carrito, escribe `3` en **Cantidad** y pulsa **Aplicar**. El subtotal será **31,50**. Si hay varias líneas, el total es la suma de sus subtotales:

```python
subtotal = unit_price * quantity
total = sum(item.subtotal for item in items)
```

Los cálculos se hacen con enteros. Por ejemplo, tres unidades a 0,10 son `10 * 3 = 30` centavos, que se muestran como `0,30`.

Antes de agregar o cambiar una cantidad, la clase vuelve a consultar el producto en SQLite. Comprueba:

- Que el producto todavía exista.
- Que la cantidad sea un entero positivo.
- Que la cantidad acumulada no supere el stock actual.
- Que el código y precio de una línea existente sigan siendo los mismos.

Con stock seis, intenta poner cantidad siete. Aparece un error y el carrito conserva cantidad tres y total 31,50. Si el precio o código cambió, hay que quitar y volver a agregar la línea para revisar el nuevo total; no cambiamos silenciosamente el importe.

Un carrito puede quedar desactualizado si se cambia el inventario después de armarlo. Esta etapa valida al operar sus cantidades, pero no reserva stock. En el Día 3 la venta tendrá una nueva validación completa dentro de la transacción.

## 9. Quitar, vaciar y eliminar

**Quitar** elimina únicamente la línea seleccionada del carrito. **Vaciar carrito** elimina sus líneas tras confirmar. Ninguna de esas acciones borra productos de SQLite ni cambia existencias.

**Eliminar**, en la pestaña Inventario, sí elimina el producto persistido:

```sql
DELETE FROM productos WHERE id = ?
```

Se pide confirmación con código y nombre. Si el producto está en el carrito, primero debes quitarlo de allí para evitar dejar una línea pendiente que ya no tiene producto.

La conexión tiene claves foráneas activadas. Cuando añadamos los detalles de ventas, un producto asociado al historial no podrá borrarse. La lógica ya convierte ese rechazo de SQLite en un mensaje comprensible; la prueba correspondiente usa una tabla de referencia temporal, no un historial de ventas que aún no existe.

Al cerrar la aplicación con un carrito pendiente, se pregunta si quieres descartarlo. El inventario sí es persistente; el carrito es temporal y no se recupera al volver a abrir.

## 10. Ejecutar las pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas cubren la base del Día 1, el CRUD, los formatos numéricos y límites, duplicados, referencias, dinero exacto, stock acumulado, cambios de precio y recorridos de interfaz. Todas las escrituras de prueba usan SQLite temporal; no modifican tus datos.

Resultado final: **39 pruebas aprobadas, ninguna omitida**. La revisión independiente detectó que Enter sobre Cancelar podía guardar; primero se reprodujo el problema con un evento real de Tkinter y una base temporal, después se corrigió la selección de la acción según el control enfocado. Las pruebas comprueban que cancelar por teclado no crea ni edita productos y que Enter desde un campo sigue guardando una sola vez.

También se comprobaron los límites geométricos de tablas y botones a 1120 × 760 y 1020 × 680 y los eventos Enter para código y cantidad. La captura de Windows sigue fallando al iniciar su runtime (`failed to write kernel assets`): estos controles no sustituyen una revisión visual de apariencia y legibilidad, que queda pendiente al abrir la ventana.

Prueba manual recomendada: crear el producto de práctica, editarlo, buscarlo, agregarlo dos veces, cambiar a cantidad tres, intentar exceder stock, verificar que el stock no bajó, quitarlo del carrito y eliminarlo desde inventario. También prueba cancelar una edición y una eliminación.

## Qué sigue en el Día 3

Crear las tablas de ventas, registrar cabecera/detalle y descontar existencias en una transacción; después agregar alertas, exportación CSV y pruebas de cierre de venta. El carrito construido hoy será la entrada de esa operación.
