import openpyxl
from pathlib import Path
from services.exporter import ExcelExporter
from services.posnext.models import ParsedShow


def test_excel_exporter(tmp_path):
    exporter = ExcelExporter(output_dir=str(tmp_path))

    shows = [
        ParsedShow(
            event_id=1,
            event_name="Indigo Girls",
            venue="Chautauqua Amphitheater",
            city_state="Chautauqua, NY",
            event_datetime_str="Thu, 10/20/26 7:00 PM",
            sold_count=92,
            active_on_hand=3,
            available_count=22,
            total_quantity=114
        ),
        ParsedShow(
            event_id=2,
            event_name="Brad Williams",
            venue="Warner Theatre - PA",
            city_state="Erie, PA",
            event_datetime_str="Fri, 10/25/26 8:00 PM",
            sold_count=15,
            active_on_hand=1,
            available_count=10,
            total_quantity=25
        )
    ]

    report_path = exporter.export(shows, filename_prefix="test_report")
    assert report_path.exists()

    wb = openpyxl.load_workbook(report_path)
    ws = wb.active
    assert ws.title == "POSNext Solds"

    # Проверяем заголовки
    headers = [ws.cell(1, col).value for col in range(1, 6)]
    assert headers == ["Show Name", "Venue", "Date & Time", "Sold", "Active On Hand"]

    # Проверяем строку 1
    assert ws.cell(2, 1).value == "Indigo Girls"
    assert "Chautauqua Amphitheater" in ws.cell(2, 2).value
    assert ws.cell(2, 3).value == "Thu, 10/20/26 7:00 PM"
    assert ws.cell(2, 4).value == 92
    assert ws.cell(2, 5).value == 3

    # Проверяем строку 2
    assert ws.cell(3, 1).value == "Brad Williams"
    assert ws.cell(3, 4).value == 15
    assert ws.cell(3, 5).value == 1
