# Valor agregado: ETL de productos desde CSV

La usuaria propone ETL u otra mejora y autoriza aplicarla para destacar en la prueba técnica. Se elige una carga inicial masiva verificable; aprovecha el formato CSV, las validaciones y las transacciones del MVP. Otras opciones eran alertas de reposición (ya cubiertas parcialmente) o auditoría completa de stock (amplía el modelo); ETL aporta un flujo nuevo demostrable con alcance acotado.

Una pestaña Importar CSV en azul/negro/blanco contiene abrir archivo, plantilla, vista previa, detalle de fila, cargar nuevos y exportar informe. La extracción admite UTF-8 con/sin BOM, punto y coma, cuatro columnas codigo/nombre/precio/stock en cualquier orden, encabezados sin espacios exteriores y sin distinguir mayúsculas. Máximo 2 MiB y 2000 filas de datos; el alcance queda visible.

Transformar: recortar extremos, normalizar código a mayúsculas, validar mediante las mismas reglas del formulario, convertir dinero a centavos exactos y stock a entero. Duplicados internos tras normalizar son errores en todas sus filas. Cada fila muestra estado Nuevo, Existente o Error, con motivo y datos originales. Un código existente se omite sin modificar ningún campo, aunque el CSV proponga otros valores. Se informa explícitamente esta política.

Cargar: si hay errores se bloquea todo el lote; un lote sin nuevos tampoco se carga. Se insertan únicamente las filas nuevas de la instantánea revisada, sin releer el archivo al confirmar. BEGIN IMMEDIATE y nueva comprobación de códigos; si un nuevo código apareció desde la vista previa, rechazar todo y pedir nueva revisión. Cualquier error revierte todo. Confirmación antes de escribir, bloqueo de doble activación y estado Cargado únicamente después del commit. La repetición del archivo genera Existentes, sin duplicar ni restaurar stock vendido.

Informe CSV: fila, estado, valores originales, valores normalizados y motivo. Se utiliza escritura atómica, UTF-8 BOM, protección de fórmulas y de base/auxiliares como destino. Se protege también el archivo de entrada para no reemplazarlo al exportar el informe o plantilla. No se quitan apóstrofos automáticamente: son texto literal y se explica el comportamiento en la guía.

Sin nuevas dependencias ni cambios de esquema; no se importan ventas ni se ajustan existencias de códigos existentes. Los errores bloquean la carga completa para que sea fácil explicar y probar todo-o-nada. Refrescar catálogo, POS y gráficos después de confirmar; un fallo de lectura posterior no deshace la carga ni invita a repetirla.

Entrega: ejemplos ficticios válidos/con errores, guía de ETL y sustentación, pruebas de parser/normalización/duplicados/rollback/concurrencia/interfaz/archivos, ZIP actualizado. La inspección visual sigue limitada por el servicio de capturas.
