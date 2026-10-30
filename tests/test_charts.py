"""Los gráficos muestran datos confirmados, en días locales y sin duplicarlos."""

from datetime import date, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.database import connect_db, initialize_database
from app.inventory import create_product
from app.sales import Cart, process_sale
from app.charts import load_chart_data


class ChartDataTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "charts.db"
        initialize_database(self.db)

    def test_empty_database_has_seven_calendar_days_with_zero_sales(self):
        data = load_chart_data(self.db, today=date(2026, 10, 28))
        self.assertEqual(data.stock, ())
        self.assertEqual(data.product_count, 0)
        self.assertEqual([point.day.day for point in data.sales], [22, 23, 24, 25, 26, 27, 28])
        self.assertEqual([point.total_cents for point in data.sales], [0] * 7)

    def test_stock_prioritizes_ten_lowest_but_summary_counts_all(self):
        for index in reversed(range(12)):
            create_product(f"P{index:02}", f"Producto {index}", "1", str(index), self.db)
        data = load_chart_data(self.db)
        self.assertEqual([point.units for point in data.stock], list(range(10)))
        self.assertEqual(data.stock[0].code, "P00")
        self.assertEqual(data.product_count, 12)
        self.assertEqual(data.low_stock_count, 5)
        self.assertEqual(data.unit_count, 66)

    def test_local_day_boundaries_exclude_outside_period_and_sum_exactly(self):
        # UTC - 5: 04:59 UTC todavía es el día anterior.
        fixtures = [("2026-10-22T04:59:59+00:00", 10000),
                    ("2026-10-22T05:00:00+00:00", 10),
                    ("2026-10-23T04:59:59+00:00", 20),
                    ("2026-10-29T04:59:59+00:00", 1050),
                    ("2026-10-29T05:00:00+00:00", 20000)]
        with connect_db(self.db) as connection:
            connection.executemany("INSERT INTO ventas(fecha,total) VALUES (?,?)", fixtures)
        data = load_chart_data(self.db, today=date(2026, 10, 28), local_zone=timezone(timedelta(hours=-5)))
        self.assertEqual([point.total_cents for point in data.sales], [30, 0, 0, 0, 0, 0, 1050])
        self.assertEqual(data.sales_count, 3)
        self.assertEqual(data.sales_total_cents, 1080)

    def test_multiline_sale_is_counted_once_and_pending_cart_is_excluded(self):
        first = create_product("A", "A", "0,10", "10", self.db)
        second = create_product("B", "B", "1,20", "10", self.db)
        cart = Cart(self.db)
        cart.add(first, 3)
        cart.add(second, 2)
        process_sale(cart)  # 30 + 240 = 270 centavos.
        cart.add(first, 2)  # Todavía pendiente, no pertenece al gráfico.
        data = load_chart_data(self.db)
        self.assertEqual(data.sales_count, 1)
        self.assertEqual(data.sales_total_cents, 270)
        self.assertEqual(data.sales[-1].total_cents, 270)

    def test_daily_sum_can_exceed_sqlite_integer_without_float_rounding(self):
        with connect_db(self.db) as connection:
            connection.executemany("INSERT INTO ventas(fecha,total) VALUES (?,?)", [
                ("2026-10-28T12:00:00+00:00", 9223372036854775807),
                ("2026-10-28T13:00:00+00:00", 1)])
        data = load_chart_data(self.db, today=date(2026, 10, 28), local_zone=timezone.utc)
        self.assertEqual(data.sales[-1].total_cents, 9223372036854775808)


if __name__ == "__main__":
    unittest.main()
