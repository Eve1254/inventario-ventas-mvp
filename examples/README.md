# CSV de demostración

Los archivos de esta carpeta contienen **datos ficticios**. Los dos primeros se generaron con una base temporal y no son exportaciones de tu inventario local. Abrir un CSV fuera de la aplicación no carga productos ni ventas.

- `inventario_demo.csv`: tres productos, con existencias después de la venta de prueba.
- `ventas_demo.csv`: dos detalles de una venta de tres cuadernos a 10,50 y dos lápices a 1,20; la suma de subtotales es 33,90.
- `importacion_valida.csv`: dos productos para practicar ETL. El primero muestra limpieza de código, conversión de precio con punto y stock con ceros iniciales. Al confirmar la carga en Importar CSV se guardan los códigos nuevos en tu inventario.
- `importacion_con_errores.csv`: cinco filas, cuatro con error (dos códigos duplicados, un precio cero y un stock negativo). La quinta es válida, pero el lote se bloquea hasta corregir todos sus errores.

Formato: UTF-8 con BOM, punto y coma y coma decimal. Si la hoja de cálculo no separa columnas, elige esos parámetros al importar. Para generar tus propios archivos, usa Exportar CSV en Inventario o en Ventas.
