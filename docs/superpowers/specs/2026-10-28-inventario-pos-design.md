# Propuesta de diseño: inventario y ventas de escritorio

Fecha: 28 de octubre de 2026.
Estado: diseño aprobado por la usuaria. Los tres días están implementados con Tkinter: venta transaccional, historial, alertas y CSV incluidos. Suite final: 70 pruebas aprobadas. La inspección visual humana queda pendiente por el fallo del runtime de capturas; ver `docs/pruebas_finales.md`.

Ampliación posterior solicitada: gráficos dentro de la aplicación con azul, negro y blanco, implementados como cuarta pestaña; suite ampliada de 80 pruebas aprobadas. El detalle está en `2026-10-28-graficos-design.md`. La paleta actual sustituye las alertas roja/ámbar del cierre inicial.

## Propósito

Construir en tres días un MVP de escritorio en Python con inventario, punto de venta y persistencia local en SQLite. La entrega debe funcionar y la candidata debe poder explicar las decisiones, recorrer el código y demostrar cómo se probaron las operaciones críticas.

El enunciado exige productos y usuarios, una tabla de productos, creación y modificación, carrito, total, procesamiento transaccional de ventas, alerta de stock menor a cinco y exportación CSV. El título CRUD también sugiere eliminación; se incluirá con protección del historial.

## Entorno comprobado

La carpeta del proyecto contiene un repositorio Git sin commits ni código. Se verificaron Python 3.14.3, SQLite 3.50.4 y Tk 8.6.15. Se pudo crear y cerrar una ventana de Tkinter sin errores. No hay instrucciones AGENTS.md en la carpeta ni en los directorios superiores revisados.

## Alternativas

1. **Python + Tkinter/ttk + SQLite — opción aprobada por la usuaria.** Ya está disponible en el equipo. Permite construir formularios, pestañas y tablas sin dependencias externas. Su apariencia requiere trabajo de estilos, pero su alcance encaja con el plazo.
2. **Python + PyQt + SQLite.** Tiene más componentes visuales y herramientas para interfaces complejas; añade instalación, empaquetado y conceptos que no son necesarios para este MVP.

Se descarta pythonnet para esta entrega porque el enunciado permite evitar su complejidad. Las decisiones siguientes utilizan Tkinter, conforme a la aprobación recibida.

## Alcance y límites

- Aplicación local en un equipo, con una base SQLite guardada en `data/inventario.db` dentro del proyecto.
- Productos vendidos por unidades enteras; una sola moneda, sin conversión ni cálculo de impuestos o descuentos.
- Interfaz en español, tamaños legibles, acciones claras y mensajes comprensibles.
- Sin servicios web, sincronización, facturación fiscal, pagos reales ni instalación de un servidor.
- Se crea la tabla usuarios solicitada. El enunciado no exige autenticación: una pantalla de acceso queda como mejora opcional después de completar y probar lo obligatorio. No se introducirán contraseñas predeterminadas ni se almacenarán contraseñas en texto plano.
- Un ejecutable empaquetado también será opcional; la entrega obligatoria se ejecutará con Python y tendrá instrucciones reproducibles.

## Arquitectura propuesta

Separar responsabilidades en pocos módulos, sin añadir un framework de arquitectura:

```text
main.py                  Inicio de la aplicación
app/database.py          Conexiones, esquema y restricciones SQLite
app/inventory.py         Consulta, validación y CRUD de productos
app/sales.py             Carrito y transacción de venta
app/exports.py           Exportaciones CSV
app/ui.py                Ventanas, formularios, pestañas y eventos
tests/                   Pruebas con bases temporales independientes
data/                    Base local, excluida de Git
README.md                Instalación, ejecución y limitaciones
docs/guia_paso_a_paso.md  Explicación por etapas y ejercicios
docs/sustentacion.md      Guion de demostración y preguntas técnicas
```

La interfaz recibe datos, llama a la lógica de negocio y muestra resultados. La lógica valida reglas y opera sobre SQLite. Las consultas usan parámetros; no se construyen sentencias SQL concatenando lo que escribe una persona. Los nombres exactos de clases y funciones quedan a criterio de implementación.

## Modelo de datos

| Tabla | Campos principales | Finalidad |
| --- | --- | --- |
| productos | id, codigo, nombre, precio, stock | Catálogo y existencias actuales |
| usuarios | id, usuario, password | Estructura mínima solicitada; password se reserva para una representación de hash con sal si se habilita acceso |
| ventas | id, fecha, total | Cabecera de cada venta confirmada |
| detalle_venta | id, venta_id, producto_id, codigo, nombre, cantidad, precio_unitario, subtotal | Productos y precios realmente vendidos |

Reglas de integridad:

- Identificadores enteros y claves primarias; código y usuario únicos.
- Código sin espacios exteriores, normalizado a mayúsculas; nombre obligatorio y sin espacios exteriores.
- Precio estrictamente positivo; stock entero mayor o igual a cero; cantidad de venta entera y positiva.
- `precio`, `precio_unitario`, `subtotal` y `total` son enteros de unidades monetarias mínimas: 10,50 se guarda como 1050. La interfaz admite hasta dos decimales, los convierte con `Decimal` y nunca usa `float` para dinero. No se aceptan separadores de miles en los formularios; se indicará con un ejemplo.
- Claves foráneas activadas en cada conexión y restricciones `CHECK` para las reglas numéricas.
- No se elimina un producto con ventas asociadas. Se explica el motivo al usuario. Un producto sin ventas sí puede eliminarse tras una confirmación.
- El detalle guarda una copia de código, nombre y precio para conservar el historial aunque el producto cambie después.
- Las fechas se almacenan con zona horaria explícita y se muestran en la hora local del equipo.

Las tablas ventas y detalle_venta son necesarias para registrar movimientos y poder exportar ventas. Una cabecera puede tener varias líneas; cada línea corresponde a un producto.

## Pantallas y comportamiento

### Inventario

Tabla con código, nombre, precio y stock. Buscar por código o nombre. Botones para crear, editar, eliminar, actualizar y exportar. Formularios con validación y errores junto a la acción que los origina. Cancelar un formulario no guarda cambios.

Las filas con stock menor a cinco se resaltan y muestran una indicación textual; stock cero se identifica como agotado. No se dependerá únicamente del color.

La tabla se consulta al abrir la aplicación, al volver a la pestaña, después de cada cambio y después de una venta. Un botón Actualizar permite releer SQLite. Este es el alcance de actualización inmediata del MVP local; no incluye sincronización con otros equipos.

### Punto de venta

Campo para código o nombre y resultados seleccionables. Un código exacto seguido de Enter agrega una unidad, compatible con un lector que funcione como teclado. No se promete soporte de hardware específico sin probarlo.

Carrito con producto, precio unitario, cantidad y subtotal. Agregar el mismo producto aumenta su cantidad, sin duplicar líneas. Se puede cambiar la cantidad, quitar una línea y vaciar el carrito. Total actualizado con cada cambio. No se reserva ni descuenta stock al agregar al carrito.

Se bloquean cantidades inválidas y cantidades superiores al stock disponible consultado. Al procesar se vuelve a comprobar el estado real en la base de datos. Un carrito vacío no se procesa.

### Ventas

Lista de ventas confirmadas con fecha y total, consulta de sus detalles y exportación CSV. Mostrar también cantidad de ventas y suma de los totales del listado. Para el MVP se muestra todo el historial; filtros por fecha son opcionales.

## Venta transaccional

1. Validar que el carrito tenga líneas válidas y agrupar cantidades por producto.
2. Abrir una conexión con claves foráneas activadas e iniciar `BEGIN IMMEDIATE`.
3. Volver a leer productos y comprobar existencia, cantidades y precios dentro de la transacción. Si un precio cambió frente al carrito, cancelar la operación y pedir actualizar el carrito para revisar el nuevo total; nunca cobrar un total diferente sin avisar.
4. Registrar cabecera y detalles, y descontar stock con una condición que exija existencias suficientes. Comprobar las filas afectadas.
5. Ejecutar `COMMIT` únicamente cuando todas las operaciones terminan bien.
6. Ante cualquier error, ejecutar `ROLLBACK`: no debe quedar una venta parcial ni stock parcialmente descontado. Conservar el carrito para corregir o reintentar.
7. Tras confirmar, mostrar el identificador de la venta, vaciar el carrito y actualizar inventario e historial.

Mientras se procesa, impedir la activación repetida del botón. Si la base está bloqueada, terminar con un mensaje que permita reintentar. No se requiere un sistema de colas para este uso local.

Ejemplo para la sustentación: si una compra contiene dos productos y el segundo ya no tiene existencias, se revierte también cualquier cambio hecho al primero. La operación completa se guarda o se deshace.

## Exportaciones

- Inventario: código, nombre, precio legible y stock de todo el catálogo actual; una búsqueda en pantalla no cambia el alcance de la exportación.
- Ventas: una fila por detalle con identificador de venta, fecha, código, nombre, cantidad, precio unitario y subtotal. El total de cabecera no se repite como columna sumable para evitar doble conteo.
- Archivo CSV con encabezados y codificación UTF-8 con BOM para facilitar la lectura de tildes en Excel. Se informará el separador usado.
- Diálogo de destino, confirmación de sobrescritura y mensaje de éxito únicamente tras completar la escritura. Cancelar el diálogo no crea un archivo.
- Utilizar `csv` para comillas y delimitadores, y tratar como texto los campos que una hoja de cálculo pudiera interpretar como fórmulas.

## Etapas de tres días

| Etapa | Resultado verificable | Conceptos para explicar |
| --- | --- | --- |
| Día 1 | Entorno reproducible, esquema y ventana con inventario obtenido desde SQLite | Módulos, conexión, tabla, clave primaria, SELECT, eventos de interfaz |
| Día 2 | Crear, editar y eliminar productos; buscar y operar el carrito con total correcto | CRUD, validaciones, código único, estado del carrito, dinero exacto |
| Día 3 | Venta persistida, stock consistente, alertas, historial, CSV y pruebas | Transacciones, COMMIT/ROLLBACK, claves foráneas, casos de error y límites del MVP |

Cada etapa se explica con: objetivo, archivos implicados, flujo de datos, comandos, prueba manual y una breve formulación que la candidata pueda adaptar con sus propias palabras. Habrá pequeños ejercicios de verificación, no solo instrucciones para copiar.

## Criterios de aceptación y pruebas

Las pruebas automáticas usan `unittest` y bases temporales; no modifican datos de demostración. Las pruebas de interfaz se complementan con un recorrido manual real.

1. Un inicio desde cero crea las tablas y abre la ventana; un segundo inicio conserva los datos.
2. Crear y editar actualiza la tabla. Código duplicado, nombre vacío, precio inválido y stock negativo producen errores comprensibles.
3. Se elimina un producto sin historial; un producto vendido conserva su referencia y su historial.
4. Agregar dos veces un código incrementa la cantidad; quitar productos y editar cantidades recalcula el total.
5. Ejemplos como tres unidades a 0,10 dan 0,30 exactamente.
6. Una venta de dos unidades con stock inicial de diez deja ocho y registra cabecera y detalle correctos.
7. Stock insuficiente, producto eliminado o precio cambiado después de armar el carrito cancelan la venta sin cambios parciales.
8. Provocar un fallo después de empezar a modificar datos demuestra que el rollback restaura todo, incluso en un carrito con varios productos.
9. Un segundo carrito desactualizado no puede vender las unidades ya consumidas por una venta anterior.
10. La alerta aparece con cuatro unidades y no con cinco; cero se identifica como agotado.
11. CSV conserva tildes, comas y comillas, muestra precios legibles y refleja los datos confirmados.
12. Recorrido completo: crear producto, cerrar y abrir, vender, comprobar stock e historial y abrir exportación.

## Entrega y defensa

Entrega mínima: código fuente, instrucciones de ejecución, pruebas, guía de aprendizaje, guion de demostración y limitaciones documentadas. Los datos de ejemplo deben ser opcionales y no sobrescribir datos existentes.

La demostración seguirá el flujo de crear un producto, vender varias unidades, observar el stock, intentar una venta inválida y exportar. La candidata debe poder justificar SQLite por el uso local, la separación de responsabilidades, los enteros para dinero y la transacción para mantener la coherencia.

## Referencias técnicas

- Tkinter: https://docs.python.org/3.14/library/tkinter.html
- sqlite3: https://docs.python.org/3.14/library/sqlite3.html
- Transacciones de SQLite: https://www.sqlite.org/lang_transaction.html

## Estado de entrega

MVP funcional implementado y probado, con actualización aditiva aplicada a la base local después de respaldarla. Incluye guía del Día 3, sustentación final, evidencia de pruebas y CSV ficticios. La revisión independiente produjo dos regresiones corregidas (edición concurrente y refresco posterior al commit). No se afirma inspección visual humana ni empaquetado ejecutable; la entrega se ejecuta con Python.
