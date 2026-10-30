# Sustentación del MVP completo

## Presentación de un minuto

«Desarrollé una aplicación de escritorio en Python con Tkinter y SQLite. Permite administrar productos, preparar un carrito y confirmar ventas. Separé la interfaz y la lógica para probarlas de forma independiente; los precios se almacenan en centavos enteros. La venta y el descuento de stock se confirman en una transacción: si falla un paso, se revierte todo. Incluí alertas, historial, CSV y gráficos. Como valor agregado implementé un ETL para importar catálogos: extrae un CSV, normaliza y valida sus filas, muestra errores y carga solo productos nuevos de forma transaccional. Repetir un archivo no duplica productos ni restaura stock vendido. Las pruebas cubren rollback, concurrencia y calidad de datos.»

Adáptalo a tus palabras. Puedes mostrar cada afirmación en los archivos y pruebas del proyecto.

## Demostración de cinco minutos

1. **Inventario:** crear un producto, editarlo y explicar el ID frente al código único.
2. **POS:** agregar el producto dos veces y mostrar una sola línea con cantidad acumulada.
3. **Venta:** confirmar, mostrar número de venta, stock menor y alerta si corresponde.
4. **Historial:** seleccionar la operación y explicar cabecera frente a detalle.
5. **Exportación:** guardar CSV de inventario y ventas y mostrar columnas y tildes.
6. **Gráficos:** observar las existencias y la venta confirmada en el día local correspondiente.
7. **Calidad:** ejecutar la suite; explicar una prueba de rollback y otra de concurrencia.

Para destacar el valor agregado, reserva dos minutos adicionales: abre el CSV con errores, muestra una fila duplicada, exporta el informe, carga el archivo válido y vuelve a abrirlo para demostrar que sus códigos se omiten. El recorrido detallado está en `guia_etl.md`.

## Preguntas técnicas y respuestas

**¿Qué protege la transacción?**

La coherencia entre venta y existencias. O se guarda la cabecera, todos los detalles y todos los descuentos, o no se confirma ninguno de esos cambios.

**¿Por qué BEGIN IMMEDIATE?**

Obtiene la reserva de escritura antes de leer stock. Otro escritor espera y después comprueba las existencias actualizadas. Si la base sigue ocupada, la operación termina con un mensaje de reintento y sin borrar el carrito.

**¿Por qué consultar stock otra vez si ya se validó al agregar al carrito?**

El carrito puede llevar abierto un tiempo y otro proceso puede vender o editar productos. La validación definitiva se hace dentro de la misma transacción que descuenta las unidades.

**¿Qué hacen COMMIT y ROLLBACK?**

COMMIT confirma los cambios; ROLLBACK revierte los de la transacción actual. El rollback no deshace operaciones anteriores que ya estaban confirmadas.

**¿Cómo comprobaste que el rollback funciona después de modificar datos?**

Una prueba instala un trigger en una base temporal que falla al insertar el segundo detalle. Después comprueba que no hay cabecera ni detalles y que ambos productos mantienen sus existencias iniciales. Otra prueba provoca un fallo diferido en el commit.

**¿Puede ocurrir sobreventa con dos ventanas?**

Las conexiones independientes se serializan al escribir y vuelven a revisar stock. La prueba concurrente prepara dos carritos de cuatro unidades con solo cinco disponibles: confirma uno y rechaza el otro; queda una unidad.

**¿Y si dejo abierto Editar producto mientras otra ventana vende?**

El formulario conserva los valores originales. Al guardar, una sola sentencia UPDATE compara esos valores con los actuales antes de escribir. Si cambió alguno, pide reabrir el formulario. Este control optimista evita que un stock antiguo sobrescriba el resultado de una venta.

**¿Cómo evitas que un doble clic registre dos ventas?**

Marco el procesamiento en curso y deshabilito el botón antes de la confirmación. Una segunda activación retorna sin procesar. Tras el commit se vacía el carrito, por lo que tampoco se vuelve a vender con el mismo carrito vacío.

**¿Qué pasa si falla la actualización de la pantalla después de guardar?**

La venta ya está confirmada. Se debe informar el problema de lectura/refresco sin presentar la venta como fallida ni repetirla. El carrito ya está vacío y el historial puede consultarse nuevamente.

**¿Qué evidencia tienes de que funciona?**

La suite actual ejecutó 102 pruebas, todas aprobadas, en Windows con Python 3.14.3, Tk 8.6.15 y SQLite 3.50.4. Utiliza bases temporales y comprueba rollback, fallos al confirmar, competencia por stock, formularios desactualizados, refrescos posteriores al commit, gráficos y ETL. También se comprobó el flujo con eventos de Tkinter y la geometría en dos tamaños. No presento esto como inspección visual humana: el servicio de capturas falló y esa comprobación sigue pendiente.

**¿Por qué guardar nombre, código y precio en detalle_venta?**

Porque el catálogo puede cambiar. El historial debe representar la operación original, no recalcularse con un precio o nombre posterior.

**¿Por qué no borrar productos vendidos?**

Las claves foráneas mantienen la relación con el historial. La aplicación explica el rechazo. Un sistema mayor podría agregar desactivación lógica en lugar de borrado; no la implementé en este MVP.

**¿Cómo manejas dinero?**

Convierto el texto usando Decimal y almaceno centavos enteros. Sumo y multiplico enteros, y solo formateo a dos decimales al mostrar o exportar. También controlo que una venta quepa en el rango INTEGER de SQLite.

**¿Qué limita SQLite?**

Es adecuado para esta aplicación local, no requiere servidor y admite transacciones. Solo hay un escritor simultáneo. Para operación distribuida o múltiples tiendas consideraría otra arquitectura y una base centralizada.

**¿Qué pruebas hay sobre CSV?**

Encabezados aun sin datos, tildes, comillas y delimitadores, importes exactos, historial conservado, neutralización de fórmulas, cancelación del diálogo, protección de la base como destino y conservación del archivo anterior cuando falla el reemplazo.

**¿Por qué no repetir el total de la venta en cada fila del CSV?**

Porque cada fila representa un detalle. Si una venta tiene tres productos y se repite su total tres veces, alguien podría triplicar lo vendido al sumar esa columna. Se exportan subtotales por línea.

**¿Qué está fuera de alcance?**

Autenticación, roles, impuestos, descuentos, devoluciones, facturación fiscal, pagos reales, sincronización entre equipos e instalador. El enunciado pidió un MVP local; la tabla usuarios está creada, pero no se debe presentar como un login terminado.

**¿Cuál es el valor agregado del ETL?**

Permite cargar un catálogo inicial por lotes. Extrae filas de CSV, transforma códigos e importes, valida con las reglas del formulario y ofrece una vista previa antes de cargar. El informe de calidad ayuda a corregir el archivo. La transacción impide cargas parciales y el código normalizado evita duplicados al repetir la importación.

**¿Por qué omitir existentes en lugar de actualizar stock?**

Un CSV puede contener existencias antiguas. Actualizarlas automáticamente podría restablecer unidades ya vendidas. El alcance elegido es insertar códigos nuevos; los existentes se identifican y conservan sus datos. No lo presento como sincronización ni actualización masiva.

**¿Cómo calculas los gráficos?**

Para existencias ordeno el catálogo por stock y muestro los diez productos con menos unidades. Para ventas leo las cabeceras confirmadas, convierto cada fecha UTC a hora local y sumo sus centavos por día en una ventana de siete fechas que incluye hoy. Los días sin venta tienen cero. No sumo los carritos pendientes ni duplico el total al unirlo con los detalles.

**¿Por qué usaste Canvas y cómo evitas perder precisión?**

Son dos gráficos de barras simples; Canvas ya forma parte de Tkinter y evita instalar otra librería. Los importes se suman y formatean con enteros exactos. Solo la proporción visual de una barra se convierte a coordenadas; el cálculo monetario no usa float.

**¿Por qué esos colores y cómo se reconocen las alertas?**

La paleta azul, negro y blanco fue un requisito de la usuaria. Azul identifica acciones y barras, blanco las superficies y negro el texto y la cabecera. Stock bajo tiene fondo azul claro y agotado fondo negro con texto blanco; ambos conservan su estado escrito. Así la información no depende únicamente del color.

## Archivos para mostrar durante la explicación

| Tema | Archivo |
| --- | --- |
| Tablas y restricciones | `app/database.py` |
| CRUD parametrizado | `app/inventory.py` |
| Dinero y validaciones | `app/validation.py` |
| BEGIN IMMEDIATE, stock y venta | `app/sales.py` |
| CSV y escritura temporal | `app/exports.py` |
| Fallo parcial, commit y concurrencia | `tests/test_sales.py` |
| Venta, alertas y diálogos en Tkinter | `tests/test_day3_ui.py` |
| Fechas locales y sumas de gráficos | `app/charts.py` y `tests/test_charts.py` |
| Barras y paleta | `app/charts_ui.py` y `app/theme.py` |
| ETL, duplicados y carga por lotes | `app/imports.py` y `tests/test_imports.py` |
| Vista previa y errores del archivo | `app/import_ui.py` y `tests/test_import_ui.py` |

## Ideas para explicar sin memorizar

- Dibuja una venta con dos productos y señala qué debe deshacerse si falla el segundo.
- Distingue claramente carrito temporal, inventario persistente y venta confirmada.
- Explica qué ocurre con una operación previa si otra venta posterior hace rollback.
- Muestra por qué stock cuatro tiene alerta y stock cinco no.
- Explica qué mejoraría al ampliar el alcance y qué ya está probado en este MVP.
