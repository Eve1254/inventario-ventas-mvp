# Gráficos en azul, negro y blanco

La cuarta pestaña de la aplicación presenta dos gráficos de barras a partir de los datos reales de SQLite. No se añadieron dependencias ni se cambió el esquema de la base.

## 1. Abrir y probar

Desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe main.py
```

Entra en Gráficos. Si no hay productos, se indica que el catálogo está vacío; si no hay ventas, aparecen las siete fechas con importe 0,00. Para un ejercicio manual, crea un producto con stock seis y precio 10,50. Vende tres unidades. Al volver a Gráficos, su stock debe ser tres y el total vendido de hoy habrá aumentado 31,50. Los ejemplos que registres manualmente sí quedan en tu base; las pruebas automatizadas utilizan bases temporales.

## 2. Interpretar existencias

Se muestran hasta diez productos, ordenados de menor a mayor stock; los empates se resuelven por ID. El gráfico incluye productos agotados. Una barra más larga representa más unidades; el valor exacto se muestra a la derecha. El título indica que es una selección del catálogo, mientras que los indicadores superiores cuentan todos los productos y todos los de stock menor a cinco.

Los códigos/nombres largos se acortan visualmente con puntos suspensivos para no invadir las barras. Los datos completos permanecen en Inventario. Las barras parten de cero; un producto sin existencias no recibe una barra de tamaño ficticio.

## 3. Interpretar ventas

El período son siete días de calendario local, desde hace seis días hasta hoy; no es una ventana móvil de 168 horas. Las fechas de SQLite tienen zona UTC explícita. Primero se convierten a hora local y luego se agrupan por fecha. Una venta a las 02:00 UTC puede corresponder al día anterior en Colombia.

Se suma `ventas.total`, una vez por cabecera. No se unen sus detalles para calcular el total, porque una venta con tres productos no debe contarse tres veces. Tampoco se incluyen carritos pendientes. Los siete días se inicializan con cero para que los días sin movimiento no desaparezcan.

## 4. Recorrer el código

1. `app/charts.py`: abre una transacción de lectura y obtiene productos y ventas desde la misma instantánea. Construye `ChartData`, con series y resúmenes. Las sumas usan enteros de Python.
2. `app/charts_ui.py`: presenta indicadores y dibuja barras con Canvas. La anchura se calcula respecto al máximo del gráfico, desde cero. Las etiquetas monetarias permanecen exactas.
3. `app/theme.py`: concentra azul, negro, blanco y tintes de azul para que los controles compartan la paleta.
4. `app/ui.py`: integra la pestaña y dispara su actualización después de guardar/eliminar productos, confirmar ventas y cambiar a Gráficos. F5 o Actualizar gráficos también releen la base.

Si falla la lectura, no se reemplaza la vista con ceros: se conservan los datos anteriores y se avisa que pueden estar desactualizados. Si eso sucede después de confirmar una venta, la venta sigue guardada; no se vuelve a procesar.

## 5. Colores y accesibilidad

Blanco para superficies, negro para texto y cabecera, azul para acciones, selección y barras. Stock Bajo usa azul claro; Agotado, negro con texto blanco. La columna Estado sigue indicando las condiciones por escrito. Las selecciones conservan contraste y los campos muestran foco de teclado. Los diálogos del sistema pueden tener colores propios de Windows.

## 6. Cómo responder en la entrevista

**Pregunta:** ¿Por qué esos dos gráficos?

**Respuesta orientativa:** «Las existencias ayudan a localizar productos próximos a agotarse; las ventas por día permiten ver el movimiento reciente. Elegí siete fechas y diez productos para mantener una lectura sencilla. El alcance está escrito en la pantalla.»

**Pregunta:** ¿Cómo sabes que no duplicas lo vendido?

**Respuesta orientativa:** «Sumo las cabeceras de ventas confirmadas, no un JOIN que repita la cabecera por cada detalle. Una prueba registra una venta de varios productos y verifica el total exacto. Otra comprueba los límites de fecha local.»

**Pregunta:** ¿Por qué Canvas?

**Respuesta orientativa:** «Tkinter ya lo incluye y dos gráficos de barras no requieren una librería adicional. Separé la consulta de datos del dibujo para probar los cálculos sin depender de la interfaz.»

Para practicar, responde primero con tus propias palabras y luego comprueba si mencionaste la decisión, el motivo y una prueba concreta.

## 7. Verificación

La suite ampliada tiene 80 pruebas aprobadas. Las diez nuevas cubren datos vacíos, diez menores existencias, límites de fecha local, venta con varios detalles, dinero fuera del rango del agregado SQLite, proporción de barras, refresco y errores posteriores al commit. Se comprobó la geometría de los gráficos en 1120×760 y 1020×680 con etiquetas largas e importes grandes. La revisión independiente también ejecutó las 80 pruebas.

El servicio de capturas no pudo iniciar; queda pendiente la inspección visual humana de apariencia. Las comprobaciones de geometría no equivalen a esa inspección.
