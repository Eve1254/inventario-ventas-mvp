# Día 3: ventas transaccionales, alertas y exportación

Hoy cerramos el flujo completo: preparar una compra, confirmarla, descontar existencias, consultar su historial y exportar resultados. Los productos de los días anteriores se conservan.

## 1. Abrir la versión final y actualizar la base

Cierra la ventana anterior y, desde la carpeta del proyecto, ejecuta:

```powershell
.\.venv\Scripts\python.exe main.py
```

La versión actual abre cinco pestañas: Inventario, Punto de venta, Ventas, Gráficos e Importar CSV. Las dos últimas se incorporaron después del Día 3 a petición de la usuaria. Al iniciar, `initialize_database()` crea dos tablas adicionales si no existen:

| Tabla | Qué representa |
| --- | --- |
| `ventas` | Una operación confirmada: ID, fecha y total. |
| `detalle_venta` | Cada producto vendido: venta, producto, código, nombre, cantidad, precio y subtotal. |

Una venta puede tener muchas líneas; cada línea pertenece a una sola venta. `venta_id` y `producto_id` son claves foráneas. SQLite comprueba que apunten a registros existentes y evita eliminar productos referenciados por el historial.

El detalle contiene una copia de nombre, código y precio. Si mañana cambias el producto del catálogo, la venta de ayer conserva lo que realmente se vendió. Los importes siguen guardándose en centavos enteros.

La actualización es aditiva: no elimina ni reconstruye `productos` o `usuarios`. Las tablas y el marcador `user_version=1` se crean dentro de una transacción. Una base marcada con una versión futura se rechaza para evitar degradarla accidentalmente.

## 2. Preparar una venta de prueba

Para practicar manualmente crea un producto con un código libre, por ejemplo `TECNICA03`, nombre `Cuaderno de práctica`, precio `10,50` y stock `6`.

En Punto de venta, agrega tres unidades. Verás un total de **31,50**. Hasta aquí el stock continúa en seis; el carrito aún es temporal.

Pulsa **Procesar venta**. La aplicación muestra el total y las unidades que se descontarán. Cancelar conserva el carrito y no escribe una venta. Confirmar llama a `process_sale()` de `app/sales.py`.

Tras una confirmación correcta se muestra el número de venta, se vacía el carrito y el stock queda en tres. Puedes comprobar el resultado en Inventario y Ventas.

## 3. Comprender una transacción

Una transacción agrupa modificaciones que deben confirmarse juntas. Para nuestro sistema, guardar una venta sin descontar stock —o descontar stock sin guardar la venta— produciría datos inconsistentes.

El recorrido de `process_sale()` es:

```text
Validar carrito no vacío e importes dentro de rango
        ↓
BEGIN IMMEDIATE
        ↓
Releer todos los productos y comprobar código, precio y stock
        ↓
INSERT ventas
        ↓
Por cada producto: UPDATE stock + INSERT detalle_venta
        ↓
COMMIT si todo termina bien / ROLLBACK si falla
        ↓
Vaciar carrito únicamente después del commit
```

`BEGIN IMMEDIATE` reserva la escritura antes de consultar existencias. SQLite admite un escritor a la vez: si dos conexiones intentan vender, la segunda debe esperar y después lee el stock actualizado. Si no logra obtener acceso dentro del tiempo configurado, se informa el bloqueo y se conserva el carrito.

Usamos una sola conexión dentro de toda la transacción. No llamamos al auxiliar `get_product()` allí, porque ese auxiliar abriría otra conexión y separaría la lectura de la transacción de venta.

## 4. Descontar stock sin permitir valores negativos

Cada descuento utiliza parámetros y una condición adicional:

```sql
UPDATE productos
SET stock = stock - ?
WHERE id = ? AND stock >= ?
```

Después se comprueba `rowcount == 1`, es decir, que se haya actualizado exactamente el producto esperado. Además, la tabla productos conserva su restricción `CHECK(stock >= 0)`.

Son defensas complementarias: validamos la compra, condicionamos la actualización y mantenemos la regla en la base. Los precios y cantidades se vuelven a comprobar al confirmar, aunque se hayan validado al agregarlos al carrito.

Si un precio o código cambió, no cobramos silenciosamente otro importe: se cancela la operación y se pide quitar y volver a agregar ese producto para revisar el total.

También protegemos el formulario de edición: imagina que lo abres cuando hay cinco unidades y otra ventana vende cuatro. Si guardaras el formulario antiguo sin comprobar nada, podrías volver a escribir cinco unidades. Para evitarlo, el `UPDATE` de edición exige que código, nombre, precio y stock todavía coincidan con los valores que tenía el producto al abrir el formulario. Comparar y escribir se hace en una sola sentencia SQL. Si los datos cambiaron, se rechaza el guardado y se pide cancelar y reabrir. Esto es **control de concurrencia optimista**: permite trabajar, pero detecta un conflicto al guardar.

## 5. Explicar COMMIT y ROLLBACK con un ejemplo

Imagina que la compra contiene café y pan. Se crea la cabecera, se descuenta café y se guarda su detalle; después falla la inserción del detalle del pan.

Con rollback se deshacen **todos** los cambios de esa transacción: vuelve el stock del café, también el del pan si ya se había descontado y desaparecen cabecera y detalles parciales. El carrito sigue disponible para corregir o reintentar.

`connect_db()` utiliza el administrador de contexto de SQLite: al salir correctamente confirma, y ante una excepción revierte. La instrucción `cart.clear()` está después del bloque `with`, porque salir del bloque también puede fallar al hacer commit.

Las pruebas provocan tanto un fallo en el segundo detalle como un fallo diferido en el commit. Por eso podemos demostrar que el comportamiento no depende de que siempre funcione la base de datos.

El botón se deshabilita y se marca una operación en curso antes de abrir la confirmación. Esto evita que dos activaciones del botón registren dos ventas. Un fallo al refrescar una vista después del commit se trata como un problema de visualización de una venta ya guardada, no como una invitación a vender otra vez.

Los métodos que recargan tablas devuelven `True` si leyeron correctamente y `False` si fallaron. El POS combina esos resultados: si alguna vista falló, mantiene el aviso de actualizar y muestra el identificador de la venta confirmada. El carrito permanece vacío. Así diferenciamos el estado de los datos del estado de la pantalla.

## 6. Revisar el historial

En Ventas se muestra el ID, fecha local y total de cada operación, además del número de ventas y la suma vendida. Selecciona una fila para consultar sus productos.

La fecha se almacena como texto ISO 8601 con UTC explícito, por ejemplo terminando en `+00:00`; la interfaz la convierte a la hora del equipo. No depende de que todos los equipos interpreten una fecha sin zona de la misma manera.

El total del historial se suma con enteros de Python. El CSV de ventas se basa en el detalle histórico, no en los nombres o precios actuales del catálogo.

## 7. Entender las alertas

| Stock | Estado mostrado | Color |
| --- | --- | --- |
| 0 | Agotado | Fondo negro, texto blanco |
| 1 a 4 | Bajo | Azul claro |
| 5 o más | Disponible | Normal |

En nuestro ejemplo, después de vender tres de seis unidades el producto queda con estado Bajo. El límite es **menor que cinco**, no menor o igual: cinco todavía se muestra Disponible.

La función `stock_status()` calcula el texto. Los tags de `Treeview` aplican el color a las filas. El texto evita depender únicamente del color y sigue siendo visible cuando la fila está seleccionada.

La paleta actual azul, negro y blanco sustituye los colores iniciales del Día 3. La [guía de gráficos](guia_graficos.md) explica la ampliación y las pruebas adicionales.

## 8. Exportar a CSV

Pulsa **Exportar CSV** en Inventario o en Ventas, elige una ruta y guarda. El diálogo permite cancelar y pide confirmación al sobrescribir un archivo existente.

- Inventario exporta todo el catálogo actual, aun si en pantalla hay una búsqueda.
- Ventas exporta una fila por producto vendido: ID de venta, fecha, código, nombre, cantidad, precio unitario y subtotal.
- No repetimos el total de cabecera en cada detalle: eso podría duplicar el resultado al sumar un archivo con varias líneas por venta.

Formato: **UTF-8 con BOM**, separador **punto y coma**, coma decimal sin separadores de miles. El módulo `csv` escapa comillas, separadores y saltos de línea. Si Excel no distribuye las columnas al abrir, importa el archivo indicando esos parámetros; para conservar ceros iniciales en códigos, elige tipo texto para esa columna.

Los textos con un inicio interpretable como fórmula, como `=`, reciben un apóstrofo. Ese carácter forma parte del CSV; es una transformación intencional para que una hoja de cálculo trate el contenido como texto.

`exports.py` escribe primero en un archivo temporal del mismo directorio y solo al terminar reemplaza el destino. Un fallo de escritura o un archivo bloqueado no debe truncar el archivo anterior. También se impide elegir la base de datos o sus archivos auxiliares como destino de una exportación.

## 9. Ejecutar las pruebas finales

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Todas las ventas y modificaciones automatizadas usan bases temporales. Puedes repetir las pruebas sin alterar tu inventario. El detalle de resultados está en [Pruebas finales](pruebas_finales.md).

En el entorno de entrega se ejecutaron **70 pruebas, todas aprobadas y ninguna omitida**. Incluyen los dos conflictos anteriores: formulario antiguo y error real de lectura al refrescar una venta ya confirmada. Las pruebas funcionales y de geometría usan Tkinter real; la inspección visual humana de colores y legibilidad sigue pendiente porque el servicio de capturas del equipo no pudo iniciar.

Para demostrar el rollback de manera específica:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sales.SaleTests.test_failure_on_second_detail_rolls_back_stock_header_and_first_detail -v
```

Para demostrar competencia por stock:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sales.SaleTests.test_concurrent_carts_cannot_oversell -v
```

## 10. Recorrido final para practicar

1. Crea el producto del ejercicio con stock seis y precio 10,50.
2. Vende tres unidades: total 31,50, stock tres, alerta Bajo.
3. Consulta la venta y su detalle; exporta ambos CSV y revisa sus columnas.
4. Cierra y abre la aplicación: stock e historial deben conservarse.
5. Intenta vender cuatro unidades del mismo producto: debe rechazarse por falta de stock.
6. Intenta eliminar ese producto: debe rechazarse porque tiene historial de ventas.
7. Ejecuta las pruebas de rollback y concurrencia y explica qué demuestran.

Esta es una aplicación local para un MVP. No incluye pagos reales, facturación fiscal, devoluciones, sincronización en red, autenticación ni instalador. La tabla usuarios se conserva conforme al enunciado; no hay contraseñas predeterminadas ni una implementación de login que presentar.
