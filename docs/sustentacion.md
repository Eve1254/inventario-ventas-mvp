# Sustentación — base del Día 1

Este guion conserva la explicación del Día 1. El CRUD y el carrito ya se explican en [Sustentación del Día 2](sustentacion_dia_2.md). El procesamiento definitivo de ventas sigue pendiente para el Día 3.

## Explicación en un minuto

«Construí la base de una aplicación de escritorio en Python con Tkinter y SQLite. SQLite guarda los productos y la estructura de usuarios en un archivo local. Separé la creación de la base, las consultas y la interfaz para poder probarlas y modificarlas de forma independiente. Al iniciar se crean las tablas si aún no existen; después se consultan los productos y se muestran en un Treeview. El botón Actualizar vuelve a consultar la base. Definí restricciones para impedir códigos duplicados, precios inválidos y stock negativo. Además, guardo los precios en centavos enteros para evitar aproximaciones de float. Las pruebas usan bases temporales, así que no alteran los datos de la aplicación.»

Adáptalo a tu forma de hablar y asegúrate de poder mostrar cada afirmación en el código.

## Preguntas probables

**¿Por qué Tkinter?**

Ya estaba disponible en el entorno, permite crear una aplicación de escritorio sin paquetes adicionales y cubre las necesidades de formularios y tablas de este MVP. El plazo favorece usar herramientas conocidas y suficientes.

**¿Por qué SQLite?**

El enunciado requiere datos locales. SQLite es persistente, admite SQL y transacciones, y evita instalar un servidor. No lo presentaría como una solución de sincronización entre múltiples tiendas.

**¿Qué diferencia hay entre id y codigo?**

`id` identifica internamente un registro; `codigo` identifica el producto para la operación del negocio. Ambos son únicos, pero tienen propósitos distintos. El usuario trabajará principalmente con el código.

**¿Por qué validar en la base si después habrá formularios?**

Los formularios ofrecerán mensajes claros antes de guardar. Las restricciones SQL protegen la integridad también cuando los datos vienen de otro script o de un futuro módulo.

**¿Por qué usar parámetros en SQL?**

Para separar la instrucción de sus valores. Evita tratar como SQL el texto de un producto y permite manejar comillas sin concatenaciones manuales. Puedes mostrar `app/demo.py`.

**¿Qué ocurre al cerrar la ventana?**

Se cierra la interfaz, pero los datos ya confirmados continúan en `data/inventario.db`. Las conexiones de cada operación se cierran mediante el administrador de contexto.

**¿Qué significa commit y rollback?**

Commit confirma una transacción; rollback la deshace. En esta etapa ya se prueba que un fallo durante dos inserciones revierte la primera. En ventas utilizaremos esa misma propiedad para guardar venta y stock como una operación coherente.

**¿Ya hay inicio de sesión?**

No. La tabla usuarios está creada, pero no se insertan usuarios ni contraseñas predeterminadas. La autenticación no se implementó en esta etapa. Si se añade, se usarán hashes con sal; la columna password por sí sola no protege una contraseña.

**¿Cómo se actualiza la tabla?**

Al abrir y al pulsar Actualizar o F5 se hace una nueva consulta SELECT. El listado no está escrito a mano. Por ahora no hay observación automática de cambios externos ni sincronización en red.

**¿Qué demostrarías con las pruebas?**

Que las tablas se crean sin borrar datos, las restricciones rechazan entradas inválidas, una transacción fallida no deja inserciones parciales, la consulta recupera filas reales y Tkinter refleja cambios persistidos al actualizar.

## Demostración de dos minutos

1. Ejecutar `main.py` y mostrar la ventana y sus columnas.
2. Si no hay datos, cargar los ejemplos desde otra terminal y pulsar Actualizar.
3. Mostrar los cinco productos, las tildes y los precios con dos decimales.
4. Cerrar y volver a abrir para demostrar persistencia.
5. Ejecutar la suite y mostrar el resultado.
6. Abrir `database.py`, `inventory.py` y `ui.py` para explicar sus responsabilidades.

## Preguntas para practicar sin mirar el código

- Si eliminas filas del Treeview, ¿se eliminan también de SQLite? ¿Por qué?
- ¿Qué pasaría si usaras una ruta relativa a la terminal para guardar la base?
- ¿Por qué `command=self.reload_products` no lleva paréntesis?
- ¿Cómo se guarda internamente un precio de 10,50?
- ¿Qué diferencia hay entre `NOT NULL`, `UNIQUE` y `CHECK`?
- ¿Qué parte cambiarías para mostrar una nueva columna en pantalla?
