# Valor agregado: ETL de productos con control de calidad

Este ETL resuelve una necesidad concreta: cargar un catálogo inicial desde una hoja de cálculo sin crear cada producto manualmente. La quinta pestaña **Importar CSV** permite revisar la información antes de guardarla. El proceso usa Python estándar, Tkinter y SQLite; no requiere pandas ni un servicio externo.

## 1. Explicar qué significa ETL

| Etapa | Qué hace esta aplicación | Ejemplo |
| --- | --- | --- |
| Extract / extraer | Lee un archivo CSV UTF-8 separado por punto y coma. | Obtiene código, nombre, precio y stock de cada fila. |
| Transform / transformar | Normaliza y valida con las mismas reglas del formulario. | ` etl001 ` se convierte en `ETL001`; `10.50` se guarda como 1050 centavos; `006` se convierte en 6. |
| Load / cargar | Inserta los productos nuevos en una transacción SQLite. | Confirma todo el lote válido o revierte todas sus inserciones. |

La vista previa es una fase intermedia de revisión en memoria: todavía no modifica el inventario. No es un sistema de inteligencia de negocios ni un almacén analítico; es una integración de datos por lotes para este MVP.

## 2. Formato de entrada

```csv
codigo;nombre;precio;stock
 etl001 ;Cuaderno ETL;10.50;006
ETL002;Lápiz ETL;1,20;12
```

Guarda en UTF-8, con o sin BOM, separado por `;`. Los encabezados son `codigo`, `nombre`, `precio` y `stock`; pueden estar en otro orden y usar mayúsculas o espacios exteriores. No se admiten columnas adicionales o repetidas. Precio positivo con máximo dos decimales y sin miles; stock entero no negativo. Los códigos se conservan como texto, incluidos los ceros iniciales.

La carga está limitada a **2 MiB y 2000 registros** por archivo para mantener la respuesta de esta aplicación local. Las líneas completamente vacías se ignoran. Una celda con punto y coma o salto de línea debe ir entre comillas según las reglas CSV.

## 3. Demostración paso a paso

1. Ejecuta `.\.venv\Scripts\python.exe main.py` desde la carpeta del proyecto y abre Importar CSV.
2. Pulsa Abrir CSV y selecciona `examples/importacion_con_errores.csv`. En una base sin esos códigos verás cinco filas: cuatro errores y un producto nuevo. Cargar nuevos productos permanece deshabilitado. Selecciona filas para revisar valores originales y motivos.
3. Pulsa Exportar informe y guarda el resultado fuera del archivo de entrada. Explica que permite devolver al proveedor una lista de filas por corregir. El informe conserva valores originales y normalizados.
4. Abre `examples/importacion_valida.csv`. Verás dos productos nuevos si sus códigos todavía no existen. Selecciona el primero para comparar sus datos originales con los normalizados de la tabla.
5. Pulsa Cargar nuevos productos y confirma. Después del commit las filas muestran Cargado y se actualizan inventario, POS y gráficos.
6. Vende tres unidades de ETL001: su stock pasa de seis a tres y la venta suma 31,50.
7. Vuelve a abrir el CSV válido. Sus códigos se clasifican como Existente y no se vuelven a insertar. El stock vendido permanece en tres.

Guardar plantilla produce únicamente los encabezados, sin productos ficticios. F5 en Importar CSV vuelve a leer el archivo seleccionado y revisar los códigos; cambiar de pestaña conserva la vista previa actual.

## 4. Reglas de calidad

- **Nuevo:** datos válidos y código que no existe al revisar. Es candidato a carga.
- **Existente:** código ya presente; se omite y conserva TODOS sus datos actuales aunque el archivo contenga otros valores.
- **Error:** se detectó una fila inválida o un código repetido dentro del archivo. Todas las apariciones de un código duplicado se marcan como error.
- **Cargado:** la inserción ya se confirmó. El botón no permite aplicar de nuevo esa vista previa.

Si una fila es inválida, no se carga ninguna. Se informa el primer motivo de validación por fila; al corregirlo y volver a abrir el archivo pueden aparecer otras validaciones de esa misma fila. Los códigos repetidos se revisan después de normalizarlos, por lo que `p01` y ` P01 ` entran en conflicto.

No se eliminan apóstrofos automáticamente: forman parte del texto. Las exportaciones de la aplicación anteponen un apóstrofo a textos que parecen fórmulas; si importas esos campos, debes revisar el texto en la vista previa. Para conservar códigos con ceros iniciales al editar en Excel, configura su columna como texto.

Si una fila tiene más o menos columnas de las requeridas, el detalle enumera todas sus posiciones físicas; así no atribuye un dato al encabezado equivocado ni oculta columnas sobrantes.

## 5. Concurrencia y transacción

Al confirmar se utiliza la copia inmutable de las filas revisadas. Cambiar el archivo en disco después de abrirlo no cambia silenciosamente lo que se cargará; para usar otra versión hay que volver a abrirla o pulsar F5.

`load_import()` inicia `BEGIN IMMEDIATE` y comprueba de nuevo los códigos. Si otra conexión creó un código que estaba marcado Nuevo, se rechaza todo el lote y se pide revisar otra vez. No se actualiza un producto existente ni se decide reemplazarlo automáticamente.

Todas las inserciones utilizan la misma conexión. Si falla la segunda, también se revierte la primera. La interfaz marca las filas Cargado solo después de que termine el commit. Un error al recargar tablas posteriormente se avisa como un problema de actualización de vistas: la carga sigue guardada y no debe repetirse.

## 6. Recorrer los archivos

- `app/imports.py`: tipos inmutables, lectura y validación, clasificación, transacción e informe.
- `app/inventory.py`: `validate_product()`, compartida con creación/edición manual.
- `app/import_ui.py`: vista previa, estados, confirmación, plantilla e informe.
- `app/exports.py`: auxiliares reutilizados para CSV seguro, escritura temporal y protección de la base como destino.
- `tests/test_imports.py` y `tests/test_import_ui.py`: reglas del ETL e integración con Tkinter y SQLite reales.

El informe se escribe primero en un temporal y luego reemplaza el destino. Las fórmulas potenciales se neutralizan. Se protegen la base, sus archivos auxiliares y el CSV de entrada, incluyendo enlaces que apunten al mismo archivo.

## 7. Respuestas para la sustentación

**¿Cuál es el valor agregado?**

«Además del CRUD incorporé una carga masiva con control de calidad. El usuario puede importar un catálogo, revisar la normalización y corregir errores antes de escribir. Esto reduce trabajo manual y hace visibles los problemas de datos.»

**¿Por qué es ETL y no solo abrir un CSV?**

«Tiene tres fases separadas: extraigo las filas, transformo códigos e importes y valido reglas de negocio; después cargo los productos nuevos en SQLite. La lectura por sí sola no modifica la base.»

**¿Qué significa idempotencia aquí?**

«Revisar y cargar otra vez el mismo archivo no crea productos duplicados. El código normalizado actúa como clave de negocio. Los existentes se omiten, por lo que volver a importar tampoco restablece existencias ya vendidas. No es una sincronización ni una actualización masiva de stock.»

**¿Por qué bloquear todo si una fila está mal?**

«Elegí una política todo-o-nada fácil de revisar en este MVP. El usuario corrige el archivo completo antes de confirmar y no tiene que reconciliar qué parte de un lote se cargó.»

**¿Por qué no pandas?**

«El archivo tiene cuatro columnas y lotes acotados. El módulo csv ya maneja comillas y delimitadores y permite reutilizar las validaciones existentes sin añadir dependencias. Para transformaciones analíticas mayores evaluaría otras herramientas.»

**¿Cómo pruebas que no sobrescribes datos?**

«Una prueba importa un producto, vende parte de su stock y revisa otro CSV con el mismo código y valores diferentes. El código se omite y conserva el precio, el nombre y el stock restante. Otra fuerza un fallo real en la segunda inserción y comprueba rollback total.»

## 8. Límites honestos

Importa productos nuevos; no importa ventas, no modifica existentes y no interpreta hojas XLSX. El informe puede exportarse, pero no hay historial de lotes persistido en tablas adicionales. No es una integración programada ni distribuida. El propósito es demostrar ETL, validación, repetibilidad y transacciones en un MVP local.

La suite actual tiene 102 pruebas aprobadas. Incluye 22 casos añadidos para ETL: parser, normalización, errores, límites, repetición, conflicto concurrente, rollback, bloqueo, protección de archivos y flujo de interfaz. La inspección visual humana sigue pendiente por el fallo del servicio de capturas; se comprobó la geometría de la pestaña en los tamaños de ventana establecidos.
