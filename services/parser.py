import asyncio
from datetime import datetime, date
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from core.logger import logger
from services.posnext.client import PosNextClient
from services.posnext.models import EventItem, ParsedShow, TicketGroupItem

# Целевые теги для подсчета Active On Hand (Вариант 2)
TARGET_TAGS = {"R", "DROP", "JUMP"}


def parse_user_date(date_str: Optional[str]) -> Optional[date]:
    """
    Парсит дату пользователя из форматов:
    - MM.DD.YY (например, 10.16.26)
    - MM/DD/YY
    - MM.DD.YYYY
    - YYYY-MM-DD
    """
    if not date_str:
        return None

    cleaned = date_str.strip()
    formats = [
        "%m.%d.%y",
        "%m/%d/%y",
        "%m-%d-%y",
        "%m.%d.%Y",
        "%m/%d/%Y",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    logger.warning(f"Не удалось распознать формат даты: '{date_str}'")
    return None


def extract_event_datetime(event: EventItem) -> Tuple[Optional[datetime], str]:
    """Извлекает объект datetime и форматированную строку из события POSNext."""
    dt: Optional[datetime] = None
    formatted_str = ""

    # Пробуем распарсить EventLocalDateTime (ISO: 2026-09-10T19:00:00-04:00)
    if event.EventLocalDateTime:
        try:
            # Предотвращаем падения из-за смещения таймзоны
            raw = event.EventLocalDateTime
            if "+" in raw or "-" in raw[10:]:
                # Отрезаем таймзону для унифицированного локального времени площадки
                base_part = raw[:19]
                dt = datetime.fromisoformat(base_part)
            else:
                dt = datetime.fromisoformat(raw)
        except Exception:
            pass

    # Фоллбек на EventDateForExport (например: "9/10/2026 19:00:00")
    if dt is None and event.EventDateForExport:
        for fmt in ["%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt = datetime.strptime(event.EventDateForExport.strip(), fmt)
                break
            except Exception:
                continue

    if dt:
        # Форматируем в красивую строку: Thu, 9/10/26 7:00 PM
        formatted_str = dt.strftime("%a, %m/%d/%y %I:%M %p")
    else:
        formatted_str = event.EventDateForExport or event.EventLocalDateTime or "N/A"

    return dt, formatted_str


class SoldsParserService:
    """Сервис поиска и фильтрации шоу по списку венью."""

    def __init__(self, client: Optional[PosNextClient] = None):
        self.client = client or PosNextClient()

    def load_venues(self, filepath: str = "venues.txt") -> List[str]:
        """Загружает список названий венью из текстового файла."""
        path = Path(filepath)
        if not path.exists():
            logger.error(f"Файл венью не найден: {filepath}")
            return []

        venues = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name and not name.startswith("#"):
                    venues.append(name)

        # Дедупликация с сохранением исходного порядка
        seen = set()
        unique_venues = []
        for v in venues:
            if v.lower() not in seen:
                seen.add(v.lower())
                unique_venues.append(v)

        logger.info(f"Загружено {len(unique_venues)} уникальных венью из {filepath}")
        return unique_venues

    def _count_active_on_hand_listings(self, ticket_groups: List[TicketGroupItem]) -> int:
        """
        Вариант 2 (выбор пользователя):
        Считает количество листингов (строк билетов), у которых:
        1) Присутствует хотя бы один тег из: "R", "Drop", "Jump" (регистронезависимо).
        2) Листинг является On Hand (IsShort == False).
        """
        count = 0
        for group in ticket_groups:
            # Проверяем флаг On Hand (не Short)
            if group.IsShort:
                continue

            # Проверяем наличие целевых тегов
            group_tags = {tag.strip().upper() for tag in group.Tags if tag}
            if group_tags.intersection(TARGET_TAGS):
                count += 1

        return count

    async def run_scan(
        self,
        venues: List[str],
        from_date_str: Optional[str] = None,
        to_date_str: Optional[str] = None,
        min_solds: int = 10,
        progress_callback: Optional[Callable[[int, int, str, int], None]] = None
    ) -> Tuple[List[ParsedShow], List[ParsedShow]]:
        """
        Запускает полное сканирование по переданному списку венью.
        Возвращает: (все_подходящие_шоу, топ_3_шоу).
        """
        from_date = parse_user_date(from_date_str)
        to_date = parse_user_date(to_date_str)

        all_matching_shows: List[ParsedShow] = []
        total_venues = len(venues)

        logger.info(
            f"Старт сканирования: {total_venues} площадок | "
            f"От даты: {from_date or 'Все'} | До даты: {to_date or 'Все'} | Мин. солдов: {min_solds}"
        )

        for idx, venue_name in enumerate(venues, start=1):
            try:
                # 1. Запрашиваем события для данного венью через FuzzySearch
                events = await self.client.fuzzy_search_events(query=venue_name)

                venue_matching_events: List[Tuple[EventItem, datetime, str]] = []

                # 2. Фильтрация на уровне событий
                for ev in events:
                    # Фильтр 1: Только активные события (Status == 1)
                    if ev.Status != 1:
                        continue

                    # Фильтр 2: Порог проданных билетов
                    if ev.SoldQuantity < min_solds:
                        continue

                    # Фильтр 3: Дата события
                    dt, dt_str = extract_event_datetime(ev)
                    if dt:
                        event_date = dt.date()
                        if from_date and event_date < from_date:
                            continue
                        if to_date and event_date > to_date:
                            continue

                    venue_matching_events.append((ev, dt, dt_str))

                # 3. Для прошедших фильтрацию событий получаем листинги и считаем Active On Hand
                for ev, dt, dt_str in venue_matching_events:
                    # Запрос листингов билетов
                    ticket_groups = await self.client.get_ticket_groups(event_ids=[ev.EventId])
                    active_on_hand_count = self._count_active_on_hand_listings(ticket_groups)

                    # Формируем читаемое название площадки и локации
                    loc = ev.EventLocation
                    v_name = loc.Venue if loc and loc.Venue else venue_name
                    city_state = f"{loc.City}, {loc.State}" if loc and loc.City and loc.State else ""

                    show = ParsedShow(
                        event_id=ev.EventId,
                        event_name=ev.EventName,
                        venue=v_name,
                        city_state=city_state,
                        event_datetime_str=dt_str,
                        event_datetime=dt,
                        sold_count=ev.SoldQuantity,
                        active_on_hand=active_on_hand_count,
                        available_count=ev.AvailableQuantity,
                        total_quantity=ev.AvailableQuantity + ev.SoldQuantity
                    )
                    all_matching_shows.append(show)

            except Exception as e:
                logger.error(f"Ошибка при обработке венью '{venue_name}': {e}")

            # Уведомляем о прогрессе
            if progress_callback:
                try:
                    res = progress_callback(idx, total_venues, venue_name, len(all_matching_shows))
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as cb_err:
                    logger.debug(f"Ошибка вызова progress_callback: {cb_err}")

            # Небольшая деликатная пауза между запросами к венью (jitter)
            await asyncio.sleep(0.15)

        # Сортируем все найденные шоу по убыванию Sold (и вторично по Active On Hand)
        all_matching_shows.sort(key=lambda s: (s.sold_count, s.active_on_hand), reverse=True)

        # Выбираем Топ-3
        top_3_shows = all_matching_shows[:3]

        logger.info(f"Сканирование завершено. Всего найдено шоу: {len(all_matching_shows)}")
        return all_matching_shows, top_3_shows
