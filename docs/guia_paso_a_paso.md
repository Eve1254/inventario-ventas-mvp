# Día 1: crear la base de datos y la primera ventana

Este capítulo conserva la explicación y evidencia del Día 1. La aplicación actual también incorpora el [Día 2: formularios y carrito](guia_dia_2.md); algunos componentes visuales y la ubicación de los auxiliares monetarios evolucionaron en esa etapa.

Esta guía explica los archivos que ya están creados. No necesitas copiar y pegar un proyecto entero: abre cada archivo, relaciónalo con su explicación y ejecuta los comandos. Los ejemplos de esta guía se ejecutan desde la raíz del proyecto en PowerShell.

## 1. Entender qué estamos construyendo

Un MVP es una primera versión utilizable con las funciones esenciales. Hoy completamos la base: una aplicación de escritorio que consulta un archivo SQLite y muestra sus productos.

El recorrido de los datos es:

```text
main.py
   ├─ initialize_database() → crea data/inventario.db y sus tablas
   └─ InventoryApp(root)
          └─ reload_products()
                 └─ list_products()
                        └─ SELECT ... FROM productos
                 ← filas de SQLite
          ← filas insertadas en la tabla visual Treeview
```

La tabla de SQLite guarda la información; el Treeview es su representación visual. Borrar una fila de la vista no equivale a borrarla de la base.

## 2. Preparar el entorno

Ya se comprobó Python 3.14.3, SQLite 3.50.4 y Tk 8.6.15 en este equipo. Puedes comprobar Python con:

```powershell
python --version
```

El entorno virtual es una carpeta con un intérprete y paquetes separados para este proyecto. No es la base de datos ni una máquina virtual.

Para crearlo en un equipo nuevo:

```powershell
python -m venv .venv
```

Aquí ya se creó. Usaremos su intérprete directamente:

```powershell
.\.venv\Scripts\python.exe main.py
```

No necesitas activar el entorno, ejecutar `pip install` ni cambiar políticas de seguridad de PowerShell: este Día 1 utiliza módulos disponibles en la instalación comprobada de Python. En otros equipos debes verificar que Python incluya Tkinter.

Si necesitas una terminal nueva en la carpeta correcta:

```powershell
Set-Location -LiteralPath 'C:\ruta\al\proyecto\inventario-ventas-mvp'
```

## 3. Decidir dónde viven los datos

Abre `app/database.py`. Estas líneas construyen la ruta:

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "inventario.db"
```

- `__file__` identifica el archivo Python actual, `app/database.py`.
- `resolve()` obtiene su ruta absoluta.
- El primer `parent` es `app`; el segundo es la raíz del proyecto.
- `Path` permite unir rutas con `/`, también en Windows.

Esto evita crear una base diferente accidentalmente si inicias el programa desde otra carpeta. SQLite guarda la información en un archivo y no necesita un servidor independiente.

## 4. Crear las tablas con SQL

En `app/database.py`, `CREATE_PRODUCTS` contiene el SQL real de productos. Su estructura esencial es:

```sql
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE
        CHECK (length(trim(codigo)) > 0 AND codigo = trim(codigo)),
    nombre TEXT NOT NULL
        CHECK (length(trim(nombre)) > 0 AND nombre = trim(nombre)),
    precio INTEGER NOT NULL
        CHECK (typeof(precio) = 'integer' AND precio > 0),
    stock INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(stock) = 'integer' AND stock >= 0)
)
```

| Parte | Significado |
| --- | --- |
| `CREATE TABLE` | Crea una tabla persistente en SQLite. |
| `IF NOT EXISTS` | Evita recrearla si ya existe; no borra sus filas. |
| `INTEGER PRIMARY KEY` | Identificador único de cada registro. SQLite asigna uno si lo omites al insertar. |
| `TEXT` / `INTEGER` | Tipos utilizados para texto y números enteros. |
| `NOT NULL` | Impide que falte un valor. No impide por sí solo el texto vacío. |
| `UNIQUE` | Impide repetir un código. |
| `CHECK` | Comprueba reglas antes de aceptar datos. |
| `DEFAULT 0` | Si no se indica stock al insertar, se utiliza cero. |

`trim` quita espacios exteriores. `length` mide la longitud. Así se rechazan códigos o nombres vacíos y compuestos solo por espacios. Cuando construyamos los formularios, también normalizaremos y validaremos la entrada antes de enviarla a SQLite.

SQLite permite conversiones de tipos; por eso usamos `typeof(...) = 'integer'` junto a la validación numérica. No basta con escribir `INTEGER` para expresar toda la regla de negocio.

La tabla `usuarios` contiene `id`, `usuario` y `password`. Empieza vacía. **Todavía no hay autenticación ni hashing implementados**: al incorporar acceso, `password` deberá contener un hash con sal, no una contraseña legible. Crear una columna con ese nombre no la cifra automáticamente.

Las tablas `ventas` y `detalle_venta` se añadirán al trabajar las ventas; no son necesarias para mostrar productos hoy.

### Por qué el precio no es float

Un `float` puede aproximar valores decimales. Para dinero guardamos la cantidad en centavos enteros:

| Valor visible | Valor en SQLite |
| --- | --- |
| `0,30` | `30` |
| `10,50` | `1050` |
| `8.500,00` | `850000` |

Esto conserva exactamente las dos posiciones decimales. En el Día 2 usaremos `Decimal` para convertir lo escrito en el formulario. Hoy solo estamos leyendo y presentando enteros.

## 5. Abrir y cerrar la conexión correctamente

`connect_db()` es un administrador de contexto, construido con `@contextmanager`. Permite escribir:

```python
with connect_db(db_path) as connection:
    # Consultas dentro de este bloque.
    ...
```

Internamente:

1. `sqlite3.connect(...)` abre el archivo; si no existe, SQLite puede crearlo.
2. `row_factory = sqlite3.Row` permite leer una fila como `product["nombre"]`.
3. `PRAGMA foreign_keys = ON` prepara la conexión para respetar las relaciones que usaremos en ventas.
4. `with connection` confirma una transacción pendiente si termina bien o la revierte si hay una excepción.
5. `finally: connection.close()` libera la conexión incluso si ocurre un error.

Detalle que puedes mencionar en la entrevista: **el contexto de `sqlite3.Connection` administra transacciones, pero no cierra por sí solo la conexión**. Nuestro envoltorio realiza ambas tareas.

`initialize_database()` crea el directorio `data`, inicia una transacción con `BEGIN` y ejecuta las dos instrucciones de creación. Es seguro invocarla nuevamente para este mismo esquema: no vuelve a insertar datos ni los elimina. Si en otra etapa cambiamos las columnas, necesitaremos una migración; `IF NOT EXISTS` no actualiza la estructura de una tabla existente.

## 6. Consultar productos

Abre `app/inventory.py`. Su consulta es:

```sql
SELECT id, codigo, nombre, precio, stock
FROM productos
ORDER BY nombre COLLATE NOCASE, id
```

`SELECT` elige las columnas, `FROM` indica de dónde salen y `ORDER BY` establece el orden. `fetchall()` recoge las filas resultantes en una lista. Si no hay productos, devuelve una lista vacía. `NOCASE` ignora diferencias de mayúsculas ASCII; no es una ordenación lingüística completa del español.

La función no conoce Tkinter. Esto permite probar la consulta sin abrir una ventana y reutilizarla más adelante.

## 7. Crear la primera ventana

Abre `main.py`. Estas llamadas explican el arranque:

```python
root = tk.Tk()
initialize_database()
InventoryApp(root)
root.mainloop()
```

El archivo real también oculta la ventana mientras prepara sus componentes y presenta errores de inicio.

- `tk.Tk()` crea la ventana principal.
- `InventoryApp(root)` organiza los componentes de nuestra aplicación.
- `mainloop()` mantiene la ventana atendiendo eventos, como clics, teclas y el cierre.

En `app/ui.py` se utilizan:

| Elemento | Uso |
| --- | --- |
| `Frame` | Agrupa componentes y organiza zonas de la ventana. |
| `Label` | Muestra texto, títulos y mensajes. |
| `Button` | Ejecuta una función cuando lo pulsas. |
| `ttk.Treeview` | Muestra las filas y columnas del inventario. |
| `Scrollbar` | Permite desplazarse cuando hay muchas filas. |
| `StringVar` | Mantiene un texto que la interfaz actualiza automáticamente. |
| `grid` | Distribuye los componentes por filas y columnas. |

La relación del botón con su función es:

```python
command=self.reload_products
```

No lleva paréntesis porque estamos entregando una función para que Tkinter la llame después. Escribir `command=self.reload_products()` la ejecutaría al construir el botón.

`reload_products()` consulta los productos, limpia las filas de la **vista** e inserta los resultados. Si la consulta falla, conserva lo que estaba visible y muestra un aviso. Si no hay resultados, presenta un mensaje de inventario vacío. **Actualizar** y **F5** vuelven a consultar SQLite; todavía no hay un proceso que detecte cambios externos automáticamente.

## 8. Ejecutar y cargar ejemplos

Primero abre la aplicación:

```powershell
.\.venv\Scripts\python.exe main.py
```

En un primer inicio verás una tabla vacía. Es correcto: crear una tabla no crea productos. Cierra la ventana para recuperar esa terminal, o abre una segunda terminal en la misma carpeta y ejecuta:

```powershell
.\.venv\Scripts\python.exe -m app.demo
```

Abre otra vez `main.py`, o pulsa **Actualizar inventario** si la ventana sigue abierta.

| Código | Nombre | Precio visible | Stock |
| --- | --- | --- | --- |
| P003 | Aceite 1 L | 12.500,00 | 8 |
| P002 | Arroz 1 kg | 4.200,00 | 20 |
| P001 | Café molido 250 g | 8.500,00 | 12 |
| P004 | Leche 1 L | 3.800,00 | 4 |
| P005 | Pan integral | 6.500,00 | 0 |

En una base nueva serán cinco productos y 44 unidades en total. El orden es por nombre; los identificadores no tienen que coincidir con el orden visual.

El script utiliza `INSERT ... VALUES (?, ?, ?, ?)` con parámetros. Los valores se envían separados del SQL; no se concatenan textos ingresados por personas en las instrucciones. `ON CONFLICT(codigo) DO NOTHING` conserva un producto cuyo código ya existe.

Si ejecutas la carga dos veces seguidas, la segunda informará cero productos agregados. Si editaste previamente un ejemplo, su versión editada se conserva.

### Ejercicio para comprobar persistencia

1. Carga los ejemplos y observa los cinco productos.
2. Cierra la ventana y ábrela nuevamente.
3. Comprueba que los productos siguen apareciendo sin volver a cargar ejemplos.
4. Ejecuta otra vez `python -m app.demo` usando el intérprete del entorno virtual.
5. Comprueba que la cantidad de productos no aumentó.

Explicación: los registros están en el archivo SQLite; no dependen de que la ventana siga abierta. La carga de ejemplos evita duplicados por código.

## 9. Ejecutar las pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Resultado comprobado durante la implementación inicial: **14 pruebas aprobadas**.

- Creación de tablas vacías y preservación de datos.
- Códigos y usuarios únicos; restricciones de precios, existencias y campos obligatorios.
- Reversión ante un fallo y cierre de conexiones.
- Consulta ordenada con tildes y carga de ejemplos que no sobrescribe datos.
- Precios presentados sin pérdida de precisión.
- Ventana Tkinter real: estado vacío, lectura, actualización y conservación de filas cuando falla una consulta.

Cada prueba utiliza una carpeta temporal. No necesitas borrar la base local para repetirlas y las pruebas no modifican tus productos.

### Registro de verificación del Día 1

El arranque normal creó `data/inventario.db` con `productos` y `usuarios` vacías y abrió una ventana que Windows reportó como activa y respondiendo. La suite completa terminó con 14 pruebas aprobadas, ninguna omitida. Una revisión independiente no encontró correcciones necesarias dentro del alcance del Día 1.

También se comprobaron mediante las medidas de Tkinter los tamaños de ventana 1020 × 650 y 820 × 520: tabla y botón dentro de la ventana y cinco filas de ejemplo visibles. Esto no sustituye una revisión visual de colores, legibilidad o recortes del texto. La herramienta de captura de Windows no pudo iniciar su entorno (error: `failed to write kernel assets`), de modo que esa revisión visual queda pendiente al mirar la ventana en el equipo.

## 10. Qué puedes explicar al terminar

Puedes describir el trayecto ventana → consulta → SQLite → filas → ventana; justificar la separación de archivos; explicar una clave primaria y un código único; mostrar por qué los datos sobreviven al cierre; y ejecutar una prueba que demuestre las restricciones.

El Día 1 no incluye formularios de creación/edición, eliminación, carrito, procesamiento de ventas, alertas ni CSV. El siguiente paso es implementar el CRUD de productos y validar los datos desde formularios antes de guardarlos.

## Referencias

- [Tkinter oficial para Python 3.14](https://docs.python.org/3.14/library/tkinter.html).
- [sqlite3 y administrador de contexto](https://docs.python.org/3.14/library/sqlite3.html#how-to-use-the-connection-context-manager).
- [Transacciones de SQLite](https://www.sqlite.org/lang_transaction.html).
