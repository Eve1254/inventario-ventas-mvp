"""Datos de los gráficos: lecturas consistentes y dinero en centavos enteros."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo
from pathlib import Path

from app.database import DEFAULT_DB_PATH, connect_db


@dataclass(frozen=True)
class StockPoint:
    code: str
    name: str
    units: int


@dataclass(frozen=True)
class DaySales:
    day: date
    total_cents: int


@dataclass(frozen=True)
class ChartData:
    stock: tuple[StockPoint, ...]
    sales: tuple[DaySales, ...]
    product_count: int
    low_stock_count: int
    unit_count: int
    sales_count: int

    @property
    def sales_total_cents(self) -> int:
        return sum(point.total_cents for point in self.sales)


def load_chart_data(db_path: Path = DEFAULT_DB_PATH, *, today: date | None = None,
                    local_zone: tzinfo | None = None) -> ChartData:
    """Diez menores existencias y siete fechas locales, incluida la de hoy.

    La zona y fecha opcionales permiten probar los límites sin cambiar el reloj.
    En la aplicación, astimezone() utiliza la configuración local del equipo.
    """
    today = today if today is not None else datetime.now(local_zone).date()
    days = {today - timedelta(days=offset): 0 for offset in reversed(range(7))}
    with connect_db(db_path) as connection:
        # Los dos SELECT ven la misma instantánea aunque otra ventana venda.
        connection.execute("BEGIN")
        products = connection.execute(
            "SELECT codigo, nombre, stock FROM productos ORDER BY stock, id"
        ).fetchall()
        sales = connection.execute("SELECT fecha, total FROM ventas").fetchall()

    sales_count = 0
    for sale in sales:
        timestamp = datetime.fromisoformat(sale["fecha"])
        if timestamp.tzinfo is None:
            raise ValueError("Hay una venta sin zona horaria; revisa su fecha antes de graficar.")
        day = timestamp.astimezone(local_zone).date()
        if day in days:
            # Cabeceras, no JOIN con detalles: una venta se suma una sola vez.
            # Python mantiene exactitud aunque el agregado exceda INTEGER SQLite.
            days[day] += sale["total"]
            sales_count += 1
    return ChartData(
        stock=tuple(StockPoint(row["codigo"], row["nombre"], row["stock"]) for row in products[:10]),
        sales=tuple(DaySales(day, total) for day, total in days.items()),
        product_count=len(products),
        low_stock_count=sum(row["stock"] < 5 for row in products),
        unit_count=sum(row["stock"] for row in products),
        sales_count=sales_count,
    )
