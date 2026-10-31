# Pruebas finales del MVP

**Estado actual tras añadir ETL:** 102 pruebas aprobadas, ninguna omitida. El cierre original del Día 3 tuvo 70; gráficos elevó el total a 80 y ETL añadió 22. Las ampliaciones se describen al final de este documento.

## Entorno y comando

Windows, Python 3.14.3, SQLite 3.50.4, Tk 8.6.15. Sin paquetes externos.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Resultado final del Día 3: **70 pruebas aprobadas, ninguna omitida**, con código de salida 0. Las ventas y escrituras de las pruebas usan carpetas temporales, no `data/inventario.db`.

## Matriz de cobertura

| Área | Casos comprobados |
| --- | --- |
| Esquema | Creación, inicialización repetida, actualización aditiva conservando producto/usuario previo, rechazo de versión futura. |
| Inventario | CRUD, código único normalizado, valores inválidos, consultas parametrizadas, búsqueda literal, referencias que impiden borrar. |
| Dinero | Decimal a centavos, tres unidades a 0,10, formatos de pantalla/formulario, valores fuera de rango. |
| Carrito | Acumulación, cantidad total frente al stock, quitar/vaciar, precio cambiado, producto eliminado, persistencia al cambiar pestañas. |
| Formularios | Guardar/editar, errores sin cerrar, cancelar por clic y por Enter sin escribir. |
| Edición concurrente | Formulario abierto con stock cinco, otra conexión vende cuatro, guardar el formulario antiguo no restaura cinco ni sobrescribe el nombre. |
| Venta correcta | Cabecera, detalles, stock, fecha con zona, total exacto, vaciado del carrito y persistencia posterior. |
| Venta rechazada | Carrito vacío, stock insuficiente, precio/código cambiado, producto eliminado y total excesivo. |
| Rollback parcial | Trigger que falla en el segundo detalle después de modificaciones reales; stock, cabecera y detalles íntegramente restaurados. |
| Fallo de commit | Restricción diferida que falla al confirmar; no queda venta y el carrito se conserva. |
| Competencia por stock | Dos hilos/conexiones independientes, dos carritos de cuatro unidades y stock cinco: una venta confirmada, otra rechazada, stock uno. |
| Bloqueo SQLite | Otra conexión retiene BEGIN IMMEDIATE; mensaje de reintento, sin escritura ni borrado del carrito. |
| Historial | Instantáneas tras editar nombre/código/precio y eliminación protegida por claves foráneas. |
| Alertas | Stock 0, 4 y 5; texto y tags de color; cambio de Disponible a Bajo después de vender. |
| Botón de venta | Confirmación cancelada, activación reentrante bloqueada, estado después de éxito/fallo. |
| Fallo de refresco | Fallos reales de lectura de resultados POS, inventario o historial tras el commit: venta persistida, carrito vacío y aviso de actualizar; sin mensaje que afirme vistas actualizadas. |
| CSV | UTF-8 BOM, encabezados vacíos, delimitadores/comillas/tildes, importes, instantáneas, fórmulas y lectura de todo el catálogo pese a filtro. |
| Archivos | Cancelación sin escritura, destino de base/auxiliares/hardlink protegido, reemplazo fallido conserva archivo anterior y limpia temporal. |

## Revisión independiente y correcciones

La revisión independiente ejecutó las 68 pruebas de la integración inicial y detectó dos casos adicionales: un formulario antiguo podía restaurar stock vendido; un error absorbido al refrescar podía terminar con un mensaje que sugiriera que todas las vistas estaban al día. Se reprodujeron ambos casos con pruebas que fallaron antes de la corrección. Tras añadir actualización optimista y resultados explícitos del refresco, las 70 pruebas pasan. No se descartó ninguno de estos hallazgos.

## Recorrido con Tkinter y geometría

En una base temporal se agregó por eventos Enter un carrito con tres cuadernos a 10,50 y dos lápices a 1,20: total 33,90. La venta dejó stocks tres y uno, vació el carrito y creó una cabecera con dos detalles. Se exportaron tres filas de inventario y dos de ventas; se volvió a inicializar/abrir la base y se verificó persistencia. Los CSV ficticios están en `examples/`.

Se comprobó que las tablas y botones principales de las tres pestañas quedan dentro de la ventana a 1120×760 y al mínimo 1020×680. Estos controles usan Tkinter real; los diálogos de confirmación/notificación se sustituyen en las pruebas para no requerir intervención humana.

## Inspección visual pendiente

Las pruebas con Tkinter real no certifican por sí solas apariencia o legibilidad. El runtime de capturas volvió a fallar al iniciar con `failed to write kernel assets: El sistema no puede encontrar la ruta especificada`. No se afirma inspección de capturas ni aceptación visual humana. Queda recorrer la aplicación en pantalla para evaluar legibilidad, colores y comodidad de los diálogos; esto no impidió ejecutar las pruebas funcionales ni de geometría.

## Actualización de la base local

Antes de actualizar se creó una copia mediante la API de respaldo de SQLite en `data/backups/inventario_antes_dia3_20261028_212518_761716.db`. La base pasó de versión 0 a 1; sus tablas productos y usuarios estaban vacías y permanecieron así. No se insertaron ventas de ensayo en la base local. `PRAGMA integrity_check` devolvió `ok` y `foreign_key_check` no devolvió errores.

## Prueba manual de aceptación

Crear producto con stock seis y precio 10,50; vender tres unidades; comprobar total 31,50, stock tres y estado Bajo; consultar historial/detalle; exportar los dos CSV; cerrar/reabrir y comprobar persistencia; intentar vender más de lo disponible e intentar eliminar el producto vendido. Verificar que ambas acciones se rechazan sin perder datos.

## Paquete del cierre original del Día 3

Se generó `dist/inventario_ventas_mvp.zip` con 39 archivos de código, pruebas, documentación y ejemplos ficticios. Se excluyeron `.venv`, la base local, sus respaldos, Git y archivos temporales. Se verificó la integridad del ZIP y se extrajo en una carpeta temporal independiente: **las 70 pruebas volvieron a pasar**, sin crear la base local del paquete durante los tests. Después se ejecutó el arranque de la interfaz desde esa carpeta y se comprobaron sus tres pestañas; la base se creó desde cero.

Para entregarlo: descomprime, abre PowerShell en `inventario_ventas_mvp`, ejecuta `python -m venv .venv` y después `.\.venv\Scripts\python.exe main.py`. Requiere una instalación de Python con Tkinter; no es un ejecutable autónomo.

## Ampliación: gráficos y paleta azul, negro y blanco

El paquete se actualiza con una cuarta pestaña Gráficos y una paleta compartida. Las 80 pruebas pasaron localmente y en una revisión independiente. Las diez nuevas pruebas cubren:

- Base vacía y siete días con importe cero.
- Diez productos de menor stock e indicadores de todo el catálogo.
- Conversión UTC a día local, límites inclusivos de siete fechas y exclusión de fechas ajenas al período.
- Venta con varios detalles contada una sola vez y carrito pendiente excluido.
- Suma exacta que supera el máximo INTEGER SQLite.
- Gráficos vacíos sin barras inventadas, proporción entre barras y recarga tras un cambio externo.
- Actualización después de guardar un producto o confirmar una venta.
- Conservación de datos con aviso ante fallo de lectura y venta ya confirmada conservada si falla su gráfico.

Se comprobaron los Canvas en ventanas de 1120×760 y 1020×680: tamaños de dibujo 518×349 y 468×269 respectivamente. Las etiquetas largas y los importes grandes permanecieron dentro de límites. La revisión independiente comprobó adicionalmente diez productos con stock INTEGER máximo y cien ventas de importe INTEGER máximo, sin cruces entre etiquetas y valores. No se encontraron defectos accionables.

El servicio de capturas volvió a fallar al iniciar (`failed to write kernel assets`). Sigue pendiente la inspección visual humana; las pruebas de geometría no certifican apariencia o foco perceptual. No se registraron ventas de ensayo ni se modificó el esquema de la base local en esta ampliación.

El ZIP actualizado contiene 47 archivos. Se extrajo en una carpeta temporal nueva: las 80 pruebas pasaron (5,656 s), sin crear datos locales durante los tests. Después se comprobó el arranque desde cero con cuatro pestañas y gráficos vacíos correctos. Su integridad y la exclusión de base local, respaldos, entorno y cachés quedaron verificadas.

## Ampliación: ETL de productos

Suite final de esta ampliación: **102 pruebas aprobadas**, código de salida 0. Las 22 adicionales cubren preview sin escritura, encabezados normalizados/reordenados, duplicados internos, filas de ancho inválido, comillas y saltos, UTF-8, límites de tamaño/filas, archivo vacío, carga de nuevos, existentes preservados después de una venta, snapshot del archivo, conflicto concurrente, rollback real en la segunda inserción, bloqueo SQLite, reporte/plantilla protegidos, confirmación cancelada, doble activación y refresco fallido posterior al commit.

La revisión independiente ejecutó las 101 pruebas iniciales de ETL y no encontró defectos de transacción o persistencia. Detectó que el detalle de una fila con columnas sobrantes y encabezados reordenados podía etiquetar mal los originales y ocultar el sobrante. Se reprodujo con una prueba fallida y se corrigió mostrando todas las posiciones físicas. La suite ampliada de 102 pasó después del arreglo.

Geometría: a 1120×760 la tabla de preview mide 232 px de alto; a 1020×680 mide 152 px y muestra dos filas completas, con desplazamiento vertical para el resto. Los controles principales, tabla y detalle quedaron dentro de la ventana. No se afirma revisión visual mediante capturas; la limitación anterior permanece. Todas las cargas de ensayo usaron bases temporales y no hubo cambios de esquema.

Entrega ETL: ZIP de 56 archivos extraído en carpeta temporal; 102 pruebas aprobadas (14,666 s), exit code 0. Después se comprobó el flujo integrado con cinco pestañas: CSV con cuatro errores, CSV válido con dos nuevos, carga confirmada, informe con estado Cargado, venta de 31,50 y revisión del mismo CSV con dos existentes y stock restante tres. Ninguna carga de ensayo utilizó la base local.

## Distribución Windows 1.0.0 — 30 de octubre de 2026

Suite completa: **107 pruebas aprobadas**, ninguna omitida, exit code 0 (11,940 s). Las cinco adicionales comprueban la ruta fuente, la ruta de datos del ejecutable, el fallback sin LOCALAPPDATA válido, conservación de SQLite y diagnóstico de interfaz lista frente a error de inicialización.

Construcción real con Python 3.14.3 x64, PyInstaller 6.22.3 e Inno Setup 7.1.1 x64 en Windows 11. Compilador descargado desde su publicación oficial y validado mediante Authenticode de Pyrsys B.V. El producto final no está firmado digitalmente.

El script `scripts/smoke_windows.py` ejecutó los artefactos finales:

- Extracción del ZIP con CRC válido en ruta con espacios y acentos.
- Arranque y reinicio del ejecutable con perfil LOCALAPPDATA aislado y PATH sin Python.
- Comprobación de la señal de interfaz inicializada correspondiente al PID actual, emitida después de construir y mostrar la ventana y procesar su geometría.
- Instalación por usuario en directorio de prueba, igualdad del ejecutable instalado y el portable, reinstalación y desinstalación.
- Conservación del producto de prueba y de su precio/stock después de todo el recorrido.

La revisión independiente no encontró pérdida de datos ni filtración de base/credenciales. Señaló que la primera versión del smoke solo probaba tablas y proceso vivo; se corrigió exigiendo el diagnóstico de interfaz lista y se añadieron pruebas de éxito y fallo. El smoke reforzado rechazó el binario anterior y aprobó el recompilado. Evidencia local: `build/smoke/926b78764e3147178e4a7dcd36aa9582/resultado.json`.

Artefactos finales:

| Archivo | Bytes | SHA-256 |
| --- | ---: | --- |
| InventarioVentas-1.0.0-Windows-x64-Setup.exe | 12022488 | `0ba1ae2296bc42edcf722d22de8ffd468f7da7baee2a04887d11392433d00b48` |
| InventarioVentas-1.0.0-Windows-x64.zip | 14007590 | `02b07d626dc4a3067557efa71be74559611c82918a922c7609fbc48e208ebbc9` |

No se utilizó la base local de la demostración para las cargas de prueba. No se certifica inspección visual mediante capturas ni ejecución en un segundo equipo o Windows 10. La instalación de prueba se desinstaló; sus datos aislados y evidencia permanecen dentro de `build/`, excluido de Git.

Publicación: [Release v1.0.0](https://github.com/Eve1254/inventario-ventas-mvp/releases/tag/v1.0.0), asociada al commit `12f132c`. Instalador, ZIP y SHA256SUMS.txt se descargaron sin autenticación y se compararon con los archivos locales: coinciden tamaños y SHA-256.
