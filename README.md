# Inventario y Ventas — MVP de escritorio

Proyecto de prueba técnica en Python, Tkinter/ttk y SQLite. **MVP funcional de los tres días:** inventario persistente, CRUD de productos, búsqueda, carrito, venta transaccional, historial, alertas de stock y exportación CSV. Incluye gráficos de existencias y ventas con paleta azul, negro y blanco. Aplicación local de escritorio sin servidor ni dependencias externas.

**Valor agregado:** ETL de productos desde CSV con normalización, vista previa, errores por fila, carga transaccional de códigos nuevos e informe exportable.

## Ejecutar en Windows / PowerShell

Para obtener el proyecto desde GitHub:

```powershell
git clone https://github.com/Eve1254/inventario-ventas-mvp.git
cd inventario-ventas-mvp
```

Abre PowerShell en la carpeta del proyecto. Entorno comprobado: Python 3.14.3 con Tk 8.6.15 y SQLite 3.50.4. No hay paquetes externos que instalar.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe main.py
```

Si ya creaste el entorno `.venv`, puedes ejecutar directamente el segundo comando. No es necesario activarlo ni modificar la política de ejecución de PowerShell.

El primer inicio crea `data/inventario.db` con `productos`, `usuarios`, `ventas` y `detalle_venta`, inicialmente vacías. Si vienes de los días 1/2, se añaden las tablas de ventas conservando productos y usuarios; la actualización se realiza dentro de una transacción y se marca con `PRAGMA user_version = 1`. Una base de una versión posterior se rechaza sin degradarla. La tabla usuarios existe, pero no hay inicio de sesión ni credenciales predeterminadas.

Si quedó abierta una versión anterior, ciérrala y vuelve a ejecutar `main.py` para cargar la interfaz nueva.

## Inventario y punto de venta

1. En **Inventario**, pulsa **Nuevo producto**, completa código, nombre, precio y stock, y guarda.
2. Selecciona una fila para **Editar** o **Eliminar**. También puedes editar con doble clic. Eliminar requiere confirmación.
3. Busca por código/nombre y pulsa **Buscar** o Enter. Deja el campo vacío para consultar todo el catálogo.
4. En **Punto de venta**, un código exacto seguido de Enter agrega una unidad. Para buscar por nombre, selecciona un resultado y pulsa **Agregar al carrito**.
5. Selecciona una línea del carrito, escribe su nueva cantidad y pulsa **Aplicar**. **Quitar** elimina esa línea; **Vaciar carrito** pide confirmación.
6. Pulsa **Procesar venta**, revisa el total y confirma. Se guarda la venta, se descuenta stock, se vacía el carrito y se actualizan inventario e historial.
7. En **Ventas**, selecciona una operación para ver los productos, cantidades y precios vendidos.

Precio de entrada: `8500,50` o `8500.50`, sin separadores de miles. Stock: entero no negativo. Cantidad en carrito: entero positivo y menor o igual al stock actual. El código se guarda sin espacios exteriores y en mayúsculas.

El carrito se mantiene al cambiar de pestaña, pero es temporal: no se guarda al cerrar. La aplicación pide confirmación antes de descartarlo al salir. **Agregar al carrito no registra una venta ni descuenta existencias; Procesar venta sí.** Si un producto está en el carrito, quítalo antes de eliminarlo del inventario. Si cambias su código o precio, quítalo y vuelve a agregarlo para aceptar el nuevo valor. Un producto con ventas asociadas no se puede eliminar; el historial conserva nombre, código y precio de la operación original.

Si otro proceso cambia un producto mientras su formulario de edición está abierto, el guardado se rechaza: cancela y vuelve a abrirlo para revisar sus datos actuales. Así, un formulario antiguo no restaura por accidente unidades ya vendidas.

## Transacción, alertas y reportes

La venta comienza con `BEGIN IMMEDIATE`, vuelve a comprobar existencia/precio/código/stock, registra cabecera y detalles y descuenta unidades con `WHERE stock >= cantidad`. Todo se confirma con un solo commit. Un fallo, incluso en el commit, revierte todo y conserva el carrito. Si otra conexión ocupa la base, se espera hasta cinco segundos y se indica que se puede reintentar. El botón se bloquea durante la confirmación y el procesamiento.

Si la venta se confirma pero falla una lectura posterior de las tablas, se avisa que ya está guardada y que debes actualizar las vistas. No repitas esa venta: el carrito ya se vació y los cambios están confirmados.

Inventario muestra **Bajo** sobre azul claro cuando hay entre 1 y 4 unidades, **Agotado** con fondo negro y texto blanco cuando hay cero y **Disponible** desde 5. La columna Estado permite reconocer la alerta sin depender del color. La paleta azul, negro y blanco se aplica a las cinco pestañas; los diálogos nativos conservan la apariencia del sistema operativo.

**Exportar CSV** en Inventario exporta todo el catálogo, aunque exista una búsqueda activa. En Ventas exporta una fila por detalle de todas las ventas confirmadas, sin repetir el total de cabecera. Los archivos usan UTF-8 con BOM, punto y coma como separador y coma decimal sin miles. Excel puede requerir elegir ese separador al importar; configura la columna código como texto si deseas conservar ceros iniciales frente a su conversión automática.

Los campos de texto que comienzan como fórmulas se prefijan con un apóstrofo (visible para lectores CSV) y se protegen la base y sus archivos auxiliares como destinos. La escritura usa un temporal y reemplaza el destino solo cuando termina; si el archivo está abierto/bloqueado, se informa el error sin afirmar éxito. El diálogo solicita confirmación para sobrescribir un archivo existente.

## Probar con productos de ejemplo

Con la aplicación cerrada o desde una segunda terminal en esta carpeta:

```powershell
.\.venv\Scripts\python.exe -m app.demo
```

Abre la aplicación o pulsa **Actualizar inventario** / **F5**. Aparecerán cinco productos. Repetir la carga no duplica códigos ni sobrescribe productos existentes; vuelve a añadir ejemplos que hayan sido eliminados.

Los precios se guardan en centavos: `850000` se muestra como `8.500,00`. Los datos de ejemplo son ficticios.

## Gráficos dentro de la aplicación

La cuarta pestaña, **Gráficos**, muestra los diez productos con menos existencias (incluye stock cero) y las ventas confirmadas de los últimos siete días de calendario local, incluyendo hoy. Las barras parten de cero y muestran valores exactos; los días sin ventas muestran 0,00. No se inventan datos si la base está vacía. Los indicadores resumen todo el catálogo y la suma vendida en esos siete días.

Se actualizan al guardar/eliminar productos, confirmar una venta, entrar en la pestaña, pulsar Actualizar gráficos o F5. Un fallo de lectura conserva los datos anteriores y avisa que pueden estar desactualizados. Los gráficos usan Canvas de Tkinter; no requieren Matplotlib. Consulta la [guía de gráficos y sustentación](docs/guia_graficos.md).

## Ejecutar las pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas crean bases temporales; no cambian `data/inventario.db`. Las pruebas de interfaz requieren Tkinter y una sesión gráfica disponible. La suite cubre los tres días, incluidos rollback tras escrituras parciales y fallo al confirmar, concurrencia real, bloqueo de SQLite, CSV, alertas y recorridos con Tkinter. Consulta los resultados en [Pruebas finales](docs/pruebas_finales.md).

Resultado actual con ETL: **102 pruebas aprobadas, ninguna omitida**. En [examples](examples/README.md) hay CSV ficticios de exportación e importación.

## Importar productos mediante ETL

En la quinta pestaña **Importar CSV**, abre un archivo, revisa los estados y pulsa Cargar nuevos productos. El formato es UTF-8 con/sin BOM y separador punto y coma, columnas `codigo;nombre;precio;stock`, máximo 2 MiB y 2000 registros. Guardar plantilla genera los encabezados para empezar.

La vista previa limpia espacios, normaliza códigos a mayúsculas y valida precios/stock con las mismas reglas que el formulario. Los códigos duplicados dentro del archivo y las filas inválidas bloquean el lote completo. Los códigos ya existentes se omiten y conservan nombre, precio y stock actuales. Exportar informe permite guardar originales, datos normalizados y errores.

La carga usa la instantánea revisada; después de cambiar el CSV debes volver a abrirlo o pulsar F5 para ver los nuevos valores. Se insertan solo productos nuevos en una transacción: si aparece un conflicto concurrente o falla una inserción, no se carga ninguna fila. Reimportar no duplica productos ni restaura stock vendido. Se protegen la base y el archivo de entrada como destinos de informe/plantilla.

Práctica: abre `examples/importacion_con_errores.csv` para observar las validaciones; después abre `examples/importacion_valida.csv` y confirma sus códigos nuevos. La confirmación sí escribe en tu inventario. La [guía ETL](docs/guia_etl.md) explica el flujo, los límites y cómo sustentarlo.

## Aprender y sustentar

- [Guía del Día 1, paso a paso](docs/guia_paso_a_paso.md).
- [Guía del Día 2: formularios y carrito](docs/guia_dia_2.md).
- [Guía del Día 3: ventas, stock y CSV](docs/guia_dia_3.md).
- [Preguntas y guion para la sustentación](docs/sustentacion.md).
- [Sustentación del Día 2](docs/sustentacion_dia_2.md).
- [Guion final de sustentación y demostración](docs/sustentacion_final.md).
- [Gráficos: uso, colores y decisiones para explicar](docs/guia_graficos.md).
- [ETL: demostración, calidad de datos y sustentación](docs/guia_etl.md).
- [Diseño completo aprobado](docs/superpowers/specs/2026-10-28-inventario-pos-design.md).

## Archivos principales

```text
main.py                 Arranque de la aplicación
app/database.py         Conexión y creación del esquema
app/inventory.py        Consulta, creación, edición y eliminación
app/validation.py       Conversión de precios, stock y cantidades
app/ui.py               Ventana principal y pestañas
app/product_dialog.py   Formulario compartido para crear/editar
app/sales.py            Carrito, transacción y consultas de ventas
app/pos_ui.py           Búsqueda, carrito y confirmación de venta
app/sales_ui.py         Historial y detalle de ventas
app/exports.py          Exportaciones CSV
app/export_ui.py        Diálogos de exportación
app/charts.py           Datos y sumas para gráficos
app/charts_ui.py        Gráficos de barras con Canvas
app/theme.py            Paleta azul, negro y blanco
app/imports.py          Extracción, transformación y carga CSV
app/import_ui.py        Vista previa, confirmación e informe ETL
app/demo.py             Carga opcional de ejemplos
tests/                  Pruebas independientes de los datos locales
data/inventario.db      Base creada al ejecutar; excluida de Git
```

## Alcance de esta etapa

El catálogo se vuelve a consultar al abrir, actualizar, guardar cambios o cambiar de pestaña; no hay sincronización automática con otros equipos. La búsqueda literal ignora mayúsculas mediante `casefold()` de Python y conserva los acentos: `CAFÉ` encuentra `Café`, pero `cafe` sin tilde no equivale a `café`. Para este catálogo pequeño se filtran las filas después de leer SQLite; una implementación para catálogos grandes necesitaría búsqueda y paginación en la base.

El MVP trabaja con unidades enteras y una moneda, sin impuestos, descuentos, devoluciones, pagos reales, facturación fiscal, sincronización de tiendas ni autenticación. No incluye instalador `.exe`; se ejecuta con Python. Los carritos pendientes se pierden si se cierra o falla el proceso, pero las ventas confirmadas permanecen en SQLite. Las fechas se guardan en UTC con zona explícita y se muestran en la hora local del equipo.

La versión de esquema 1 es una actualización aditiva del esquema original. Cambios de estructura futuros deben incorporar migraciones explícitas; `IF NOT EXISTS` por sí solo no actualiza columnas de tablas existentes. La revisión visual por capturas depende del runtime del equipo; sus limitaciones se documentan por separado de las pruebas funcionales.

La base local, `.venv`, archivos `.env`, registros `.log` y exportaciones CSV en la raíz o en `exports/` están excluidos mediante `.gitignore`. Los CSV ficticios de `examples/` sí forman parte del repositorio. Para llevar el proyecto a otro equipo se clona el repositorio y se vuelve a crear el entorno virtual. Si se desean conservar datos reales, se copia la base por separado con la aplicación cerrada.

La entrega preparada en `dist/inventario_ventas_mvp.zip` contiene el código, las pruebas, la documentación y cuatro CSV ficticios. Descomprime y sigue los comandos del inicio de este README. El ZIP no incluye tu base local ni el entorno virtual. La evidencia de comprobación de la copia extraída está en `docs/pruebas_finales.md`.
