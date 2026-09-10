import pytest
from datetime import date, datetime
from services.parser import parse_user_date, extract_event_datetime, SoldsParserService
from services.posnext.models import EventItem, EventLocation, TicketGroupItem, ParsedShow


def test_parse_user_date():
    assert parse_user_date("10.16.26") == date(2026, 10, 16)
    assert parse_user_date("10/16/26") == date(2026, 10, 16)
    assert parse_user_date("2026-10-16") == date(2026, 10, 16)
    assert parse_user_date("10.16.2026") == date(2026, 10, 16)
    assert parse_user_date(None) is None
    assert parse_user_date("") is None
    assert parse_user_date("invalid_date") is None


def test_extract_event_datetime_iso():
    event = EventItem(
        EventId=7569949,
        EventName="Brad Williams",
        EventLocalDateTime="2026-09-10T19:00:00-04:00",
        EventDateForExport="9/10/2026 19:00:00",
        SoldQuantity=2,
        Status=1
    )
    dt, dt_str = extract_event_datetime(event)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 10
    assert dt.hour == 19
    assert "9/10/26" in dt_str


def test_count_active_on_hand_variant_2():
    parser = SoldsParserService()

    groups = [
        # 1. Листинг с тегом R, On Hand -> Должен быть учтен
        TicketGroupItem(
            TicketGroupId=1,
            Quantity=4,
            AvailableQuantity=4,
            IsShort=False,
            Tags=["danny O", "R"]
        ),
        # 2. Листинг с тегом DROP, On Hand -> Должен быть учтен
        TicketGroupItem(
            TicketGroupId=2,
            Quantity=2,
            AvailableQuantity=2,
            IsShort=False,
            Tags=["Drop"]
        ),
        # 3. Листинг с тегом Jump, но IsShort=True (не On Hand) -> НЕ должен быть учтен
        TicketGroupItem(
            TicketGroupId=3,
            Quantity=2,
            AvailableQuantity=2,
            IsShort=True,
            Tags=["Jump"]
        ),
        # 4. Листинг с другими тегами (S, GA) -> НЕ должен быть учтен
        TicketGroupItem(
            TicketGroupId=4,
            Quantity=10,
            AvailableQuantity=10,
            IsShort=False,
            Tags=["S+", "GA"]
        ),
        # 5. Листинг сразу с двумя целевыми тегами (R и Drop) -> Должен посчитаться как 1 листинг
        TicketGroupItem(
            TicketGroupId=5,
            Quantity=6,
            AvailableQuantity=6,
            IsShort=False,
            Tags=["R", "Drop"]
        ),
    ]

    count = parser._count_active_on_hand_listings(groups)
    assert count == 3  # Листинги 1, 2, 5


@pytest.mark.asyncio
async def test_run_scan_filtering_and_top_3(monkeypatch):
    class MockPosNextClient:
        async def fuzzy_search_events(self, query, **kwargs):
            return [
                # Шоу 1: Подходит (Sold=92, Active)
                EventItem(
                    EventId=101,
                    EventName="Indigo Girls",
                    EventLocalDateTime="2026-10-20T19:00:00",
                    EventLocation=EventLocation(Venue="Chautauqua Amphitheater", City="Chautauqua", State="NY"),
                    SoldQuantity=92,
                    AvailableQuantity=22,
                    Status=1
                ),
                # Шоу 2: Подходит (Sold=15, Active)
                EventItem(
                    EventId=102,
                    EventName="Brad Williams",
                    EventLocalDateTime="2026-10-25T20:00:00",
                    EventLocation=EventLocation(Venue="Warner Theatre", City="Erie", State="PA"),
                    SoldQuantity=15,
                    AvailableQuantity=10,
                    Status=1
                ),
                # Шоу 3: НЕ подходит (Status=2, Problem)
                EventItem(
                    EventId=103,
                    EventName="Rodney Carrington",
                    EventLocalDateTime="2026-10-22T19:00:00",
                    SoldQuantity=50,
                    Status=2
                ),
                # Шоу 4: НЕ подходит (Sold=4 < 10)
                EventItem(
                    EventId=104,
                    EventName="Le Grand Cirque",
                    EventLocalDateTime="2026-10-30T19:00:00",
                    SoldQuantity=4,
                    Status=1
                ),
                # Шоу 5: НЕ подходит по дате (раньше 10.16.26)
                EventItem(
                    EventId=105,
                    EventName="Past Show",
                    EventLocalDateTime="2026-10-10T19:00:00",
                    SoldQuantity=30,
                    Status=1
                ),
            ]

        async def get_ticket_groups(self, event_ids):
            return [
                TicketGroupItem(
                    TicketGroupId=1,
                    Quantity=4,
                    IsShort=False,
                    Tags=["R"]
                )
            ]

    parser = SoldsParserService(client=MockPosNextClient())
    all_shows, top_3 = await parser.run_scan(
        venues=["Test Venue"],
        from_date_str="10.16.26",
        min_solds=10
    )

    # Должны пройти только Indigo Girls (92) и Brad Williams (15)
    assert len(all_shows) == 2
    assert all_shows[0].event_name == "Indigo Girls"
    assert all_shows[0].sold_count == 92
    assert all_shows[0].active_on_hand == 1

    assert all_shows[1].event_name == "Brad Williams"
    assert all_shows[1].sold_count == 15

    assert len(top_3) == 2
