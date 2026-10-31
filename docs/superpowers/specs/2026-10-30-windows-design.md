# Aplicación descargable para Windows

## Objetivo y alcance

Entregar el MVP existente como aplicación Windows x64 que se abre con doble clic sin instalar Python. Conservar Tkinter, SQLite, gráficos y ETL. El usuario pidió una aplicación descargable y ya autorizó el repositorio público Eve1254/inventario-ventas-mvp.

## Alternativas y decisión de implementación

- Un ejecutable de un solo archivo simplifica la copia, pero extrae dependencias en cada inicio.
- Una carpeta con ejecutable y dependencias permite comprobar y distribuir directamente el runtime. Se empaqueta en ZIP y en un instalador por usuario con acceso directo. Esta es la elección del implementador para el MVP.
- Una tienda de aplicaciones o firma comercial añade trámites ajenos a esta entrega.

## Datos y actualizaciones

En desarrollo se conserva `data/inventario.db`. En el ejecutable se utiliza `%LOCALAPPDATA%/InventarioVentas/inventario.db`, fuera de la carpeta instalada. Si esa variable falta o no es absoluta, se usa `Path.home()/AppData/Local`. El primer inicio crea una base vacía. No se incorpora ni migra automáticamente la base de práctica del desarrollador. Instalador, actualización y desinstalación no eliminan los datos del usuario.

## Distribución

PyInstaller 6.22.3, compilado con Python 3.14 x64 en Windows. Inno Setup genera un instalador por usuario sin elevación, acceso en Inicio y acceso de escritorio opcional. Se incluyen ejemplos CSV, guía de uso y avisos de los componentes distribuidos. Versionado inicial 1.0.0. Artefactos y SHA-256 se publican como Release del repositorio; no se guardan binarios en Git. No hay actualización automática ni firma digital de esta primera entrega.

## Comprobación

Pruebas de ruta de datos y conservación tras reiniciar; suite funcional completa; compilación real; inicio del ejecutable con perfil de datos aislado y PATH sin Python; instalación en directorio de prueba, arranque, actualización y desinstalación comprobando conservación de SQLite. Las pruebas no utilizan la base de la demostración. Una prueba en este equipo no sustituye una validación en todos los Windows compatibles.
