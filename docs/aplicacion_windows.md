# Inventario y Ventas 1.0.0 para Windows

Aplicación de escritorio para Windows 10/11 de 64 bits. Incluye Python, Tkinter y SQLite: el usuario final no necesita instalar Python ni ejecutar comandos. Funciona localmente sin conexión a Internet.

## Descargar e instalar

1. Abre https://github.com/Eve1254/inventario-ventas-mvp/releases/latest
2. Descarga `InventarioVentas-1.0.0-Windows-x64-Setup.exe`.
3. Abre el instalador y sigue el asistente. La instalación es para tu usuario, sin solicitar permisos de administrador.
4. Deja marcada la opción de acceso directo y abre **Inventario y Ventas** desde el escritorio o Inicio.

Esta primera distribución no tiene firma digital de editor; Windows puede mostrar **Editor desconocido**. El repositorio indicado es la fuente de descarga de esta entrega. En la versión publicada también se incluyen las sumas SHA-256 para comprobar los archivos.

## Ejecutar sin instalar

Descarga `InventarioVentas-1.0.0-Windows-x64.zip`, pulsa **Extraer todo** y abre `InventarioVentas.exe` dentro de la carpeta extraída. Conserva la carpeta `_internal` junto al ejecutable: contiene sus dependencias. No ejecutes directamente desde la vista del ZIP.

Esta alternativa no registra un instalador; sus datos también se guardan en el perfil del usuario, no dentro del ZIP ni en un pendrive. Instalador y ZIP comparten la misma base cuando los ejecuta el mismo usuario de Windows.

## Primer uso

El catálogo empieza vacío. Puedes agregar productos en Inventario o importar `examples/importacion_valida.csv` desde la pestaña Importar CSV. Revisa la vista previa y confirma la carga. Los ejemplos son ficticios. El precio `10.50` significa 10,50, no diez mil quinientos.

Las pestañas permiten gestionar productos, vender mediante un carrito, consultar ventas, ver gráficos e importar productos. Los botones Exportar CSV guardan los datos donde elijas.

## Dónde quedan mis datos

La base de la aplicación descargada está en:

`%LOCALAPPDATA%\InventarioVentas\inventario.db`

Puedes pegar `%LOCALAPPDATA%\InventarioVentas` en la barra de direcciones del Explorador. Para hacer una copia de respaldo, cierra todas las ventanas de la aplicación y copia `inventario.db` a un lugar seguro.

En esa carpeta también queda `inicio.log`, un diagnóstico de arranque con tamaño limitado. Permite distinguir una interfaz inicializada de un error al abrir la aplicación; no contiene el inventario ni las ventas.

Actualizar, reinstalar o desinstalar el programa conserva esta carpeta de datos. Para actualizar, cierra la aplicación e instala la nueva versión. Cada usuario de Windows tiene su propia base.

La ejecución desde código fuente sigue utilizando `data/inventario.db` dentro del proyecto. No se incluye la base de práctica en la descarga. Si quieres trasladarla al ejecutable: cierra ambas aplicaciones, respalda las dos bases si existen y copia la base elegida a la ruta anterior. No reemplaces una base con ventas que necesites conservar: esta copia sustituye el archivo completo y no combina inventarios.

## Construir desde el código

En Windows, con Python 3.14 de 64 bits:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/build_windows.py --iscc "C:\ruta\a\Inno Setup\ISCC.exe"
```

El compilador de Inno Setup se obtiene en https://jrsoftware.org/isdl.php (esta entrega usa 7.1.1 x64). Si omites `--iscc`, se genera solamente el ZIP. Los archivos finales y `SHA256SUMS.txt` quedan en `dist/releases/v1.0.0/`. El ejecutable sin comprimir queda en `dist/windows/InventarioVentas/`.

El proceso de construcción no copia bases locales, exportaciones ni credenciales. Las licencias de Python, Tcl/Tk y PyInstaller se incluyen en `Licencias/`. Las dependencias de construcción no son requisitos para quien descarga la aplicación.

## Alcance

Esta entrega es para Windows x64; no se ha generado una aplicación para macOS o Linux. No incluye actualización automática, sincronización entre equipos, autenticación ni instalador firmado. El código fuente y las pruebas siguen disponibles en el repositorio.
