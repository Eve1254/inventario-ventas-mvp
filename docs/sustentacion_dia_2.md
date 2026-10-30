# Sustentación del Día 2

Este guion conserva lo construido en esa etapa. Para presentar el MVP completo utiliza la [sustentación final](sustentacion_final.md).

## Explicación breve

«Agregué el CRUD de productos con formularios de creación y edición, confirmación de eliminación y búsqueda. Separé las validaciones de la interfaz: los precios se convierten con Decimal a centavos enteros y el stock admite únicamente enteros no negativos. Las consultas usan parámetros y la base mantiene restricciones de integridad. Para el POS construí un carrito en memoria indexado por producto: si se agrega dos veces, acumula la cantidad. Antes de cambiar cantidades se revisan el precio y las existencias actuales. El total se calcula en enteros. El carrito todavía no descuenta stock; la confirmación transaccional se implementará en el Día 3.»

## Preguntas que debes poder responder

**¿Qué significa CRUD y dónde está?**

Create, Read, Update y Delete: crear, consultar, actualizar y eliminar. Está en `app/inventory.py`; se corresponde con INSERT, SELECT, UPDATE y DELETE.

**¿Por qué reutilizar el formulario?**

Crear y editar requieren los mismos campos y validaciones. La diferencia es si existe un ID que actualizar. Reutilizar el formulario evita que una validación se aplique al crear pero se olvide al editar.

**¿Cómo evitas modificar todos los productos?**

UPDATE y DELETE usan `WHERE id = ?`. El ID pertenece a la fila seleccionada y no cambia aunque se edite el código. También se verifica si la operación afectó una fila.

**¿Por qué validar dos veces, en Python y en SQLite?**

Python da mensajes comprensibles y normaliza los datos. SQLite impide guardar estados inválidos incluso si otro módulo escribe en la base. Cumplen funciones complementarias.

**¿Qué evita los códigos duplicados?**

El código se normaliza a mayúsculas sin espacios exteriores y la columna tiene una restricción UNIQUE. Si SQLite rechaza el código, se convierte la excepción en un mensaje del formulario.

**¿Qué diferencia hay entre Decimal y float en este proyecto?**

Decimal interpreta exactamente el texto monetario. Después lo convierto a centavos enteros. Los cálculos del carrito usan esos enteros, así que no acumulan aproximaciones binarias de float.

**¿Por qué un diccionario para el carrito?**

Su clave es el ID del producto. Permite encontrar una línea y sumar cantidades sin crear filas duplicadas. La vista recibe líneas inmutables para evitar modificaciones que salten las validaciones.

**¿Qué pasa si el stock cambia después de agregar al carrito?**

Al agregar de nuevo o cambiar cantidad se consulta el stock actual. Si no alcanza, se conserva el carrito y se muestra un error. Esto no reserva stock ni sustituye la comprobación transaccional que deberá hacerse al confirmar la venta.

**¿Qué pasa si cambia el precio?**

El carrito conserva el precio con que se agregó la línea. Al intentar cambiarla se detecta la diferencia y se pide quitarla y agregarla otra vez. Así el usuario puede revisar el nuevo total.

**¿Agregar al carrito ya es una venta?**

No. El carrito es una intención de compra en memoria. La venta será un registro persistido que se guardará junto con el descuento de existencias dentro de una transacción.

**¿Qué diferencia hay entre Quitar y Eliminar?**

Quitar afecta una línea temporal del carrito. Eliminar borra un producto de SQLite y pide confirmación. Un producto presente en el carrito debe retirarse de él antes de eliminarse del inventario.

**¿Cómo comprobaste los errores?**

Con pruebas de entradas inválidas, duplicados, edición fallida que conserva valores anteriores, cantidades acumuladas superiores al stock y cambios de precio. También hay pruebas de Tkinter real para guardar/cancelar formularios y manipular el carrito.

## Ejercicio para sustentar sin memorizar

1. Crea un producto a 10,50 con stock seis.
2. Agrégalo dos veces: explica por qué aparece una sola línea de cantidad dos.
3. Cambia la cantidad a tres: explica el cálculo de 31,50.
4. Intenta cantidad siete: muestra el error y la conservación del total anterior.
5. Regresa al inventario: demuestra que el stock sigue en seis.
6. Explica qué falta para confirmar la venta de forma segura en el Día 3.
