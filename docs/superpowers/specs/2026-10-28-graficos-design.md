# Gráficos y paleta azul, negro y blanco

La usuaria solicita gráficos dentro de la aplicación y esos tres colores. Se mantiene el MVP local de Tkinter/SQLite y la preparación posterior de la sustentación.

Decisiones de implementación comunicadas: una cuarta pestaña Gráficos; existencias de los diez productos con menor stock (incluye cero), y ventas confirmadas de los siete días de calendario local hasta hoy. Los días sin ventas muestran cero. No se usan carritos, proyecciones ni datos ficticios para rellenar las gráficas. Las barras parten de cero y se acompañan de valores exactos.

Alternativas consideradas: Canvas nativo y una librería de gráficos. Se elige Canvas porque los dos gráficos de barras son simples y conserva la ejecución sin dependencias externas. La elección es de implementación, no una preferencia técnica atribuida a la usuaria.

Paleta: blanco para superficies, negro para texto y cabecera, azul para acciones, selección y barras; tintes de azul para stock bajo y negro/blanco para agotado. Conservar los estados textuales y foco de teclado. Los diálogos del sistema mantienen su apariencia nativa.

Leer datos del catálogo y cabeceras de ventas en una única instantánea de SQLite. Sumar centavos con enteros de Python, convertir fechas UTC a fecha local antes de agrupar. No alterar esquema ni datos. Refrescar al entrar en la pestaña, F5, guardar/eliminar productos y confirmar ventas. Si falla la lectura, conservar lo mostrado con aviso explícito de desactualización; no presentar una venta ya confirmada como fallida.

Comprobar bases vacías, ventana de fechas y cambio de día UTC/local, ventas con varios detalles sin doble conteo, cifras grandes, dibujo proporcional, redimensionado y refresco tras venta. Actualizar documentación y ZIP. Inspección visual depende de disponibilidad del servicio de capturas; las comprobaciones geométricas no la sustituyen.
