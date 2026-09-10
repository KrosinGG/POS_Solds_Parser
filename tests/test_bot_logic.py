import pytest
from services.parser import SoldsParserService
from bot.handlers.run import make_progress_bar
from services.posnext.models import TicketGroupItem


def test_make_progress_bar():
    bar_0 = make_progress_bar(0, 100, length=10)
    assert "0%" in bar_0
    assert "░" * 10 in bar_0

    bar_50 = make_progress_bar(50, 100, length=10)
    assert "50%" in bar_50
    assert "█" * 5 in bar_50

    bar_100 = make_progress_bar(100, 100, length=10)
    assert "100%" in bar_100
    assert "█" * 10 in bar_100


def test_venues_loader(tmp_path):
    v_file = tmp_path / "venues_test.txt"
    v_file.write_text(
        "# Список театров\n"
        "Warner Theatre\n"
        "\n"
        "Kleinhans Music Hall\n"
        "warner theatre\n"  # Дубликат в другом регистре
        "Chautauqua Institution Amphitheater\n",
        encoding="utf-8"
    )

    parser = SoldsParserService()
    venues = parser.load_venues(str(v_file))

    assert len(venues) == 3
    assert venues[0] == "Warner Theatre"
    assert venues[1] == "Kleinhans Music Hall"
    assert venues[2] == "Chautauqua Institution Amphitheater"


def test_active_on_hand_case_and_whitespace():
    parser = SoldsParserService()
    groups = [
        TicketGroupItem(IsShort=False, Tags=["  r  "]),
        TicketGroupItem(IsShort=False, Tags=["dRoP"]),
        TicketGroupItem(IsShort=False, Tags=["  JUMP "]),
        TicketGroupItem(IsShort=True, Tags=["R"]),  # Short (not on hand) -> ignore
        TicketGroupItem(IsShort=False, Tags=["VIP", "S+"]),  # Other tags -> ignore
        TicketGroupItem(IsShort=False, Tags=[]),  # Empty tags -> ignore
    ]
    assert parser._count_active_on_hand_listings(groups) == 3
