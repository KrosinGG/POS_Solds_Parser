import asyncio
import json
import urllib.parse
from typing import Any, Dict, List, Optional
import httpx
from core.logger import logger
from services.posnext.auth import PosNextAuth
from services.posnext.models import EventItem, TicketGroupItem


class PosNextClient:
    """Асинхронный REST API клиент к POSNext TicketNetwork."""

    BASE_URL = "https://posnext.ticketnetwork.com"

    def __init__(self, auth: Optional[PosNextAuth] = None):
        self.auth = auth or PosNextAuth()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=httpx.Timeout(30.0, connect=15.0),
                follow_redirects=True,
                http2=True
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        retry_on_401: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Выполняет защищенный запрос к API с автоматической переавторизацией при 401."""
        await self.auth.ensure_valid_session()
        client = await self._get_client()
        headers = self.auth.get_auth_headers()

        for attempt in range(3):
            try:
                resp = await client.request(
                    method=method,
                    url=path,
                    params=params,
                    headers=headers,
                    cookies=self.auth.cookies
                )

                if resp.status_code == 401 and retry_on_401:
                    logger.warning("Получен HTTP 401 Unauthorized. Обновление сессии POSNext...")
                    success = await self.auth.login_via_browser()
                    if success:
                        headers = self.auth.get_auth_headers()
                        return await self._request(method, path, params, retry_on_401=False)
                    else:
                        logger.error("Не удалось обновить сессию после 401.")
                        return None

                if resp.status_code == 429:
                    wait_time = 2.0 * (attempt + 1)
                    logger.warning(f"Rate limited (429). Ожидание {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP ошибка при запросе {path}: {e.response.status_code} - {e.response.text[:200]}")
                if attempt == 2:
                    return None
            except Exception as e:
                logger.error(f"Сетевая ошибка при запросе {path}: {e}")
                if attempt == 2:
                    return None
                await asyncio.sleep(1.0)

        return None

    async def fuzzy_search_events(
        self,
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page_size: int = 1000,
        page_number: int = 1
    ) -> List[EventItem]:
        """
        Поиск событий по названию площадки (Venue) или названию события.
        Эндпоинт: /api/Event/FuzzySearch
        """
        payload = {
            "EventName": query,
            "ShowMyEventsOnly": True,
            "ShowMyPastEvents": False,
            "ShowOnlyFavorites": False,
            "SoldEventsOnly": False,
            "FromEventDate": from_date,
            "ToEventDate": to_date,
            "Venue": None,
            "City": None,
            "State": None,
            "Country": None,
            "HasBroadcastedTickets": None,
            "Category": None,
            "SortOptions": {
                "PageSize": page_size,
                "PageNumber": page_number,
                "ColumnSortOptions": []
            }
        }

        # API POSNext ожидает сериализованный JSON в query-параметре "request"
        params = {"request": json.dumps(payload)}
        data = await self._request("GET", "/api/Event/FuzzySearch", params=params)

        if not data or not isinstance(data, dict):
            return []

        response_data = data.get("Data", {})
        items_raw = response_data.get("Items", []) if isinstance(response_data, dict) else []

        result = []
        for item in items_raw:
            try:
                result.append(EventItem.model_validate(item))
            except Exception as e:
                logger.debug(f"Ошибка парсинга элемента события: {e}")
                continue

        return result

    async def get_ticket_groups(self, event_ids: List[int]) -> List[TicketGroupItem]:
        """
        Получение информации о листингах билетов и тегах для выбранных событий.
        Эндпоинт: /api/TicketGroup
        """
        if not event_ids:
            return []

        payload = {
            "AutopricerActive": None,
            "BroadcastChannels": [],
            "CanonicalSections": [],
            "EventIds": event_ids,
            "ExchangeTicketGroupId": None,
            "FromCost": None,
            "FromCreatedDate": None,
            "FromOnHandDate": None,
            "FromUpdateDate": None,
            "HasPurchaseOrder": None,
            "HasQRScreenshots": None,
            "IsInstant": None,
            "IsSold": False,
            "IsNatbBroker": None,
            "NearTermDeliveryMethodIds": [],
            "PurchaseOrderId": None,
            "Quantity": None,
            "QuantityFilterOnPurchasable": True,
            "Row": None,
            "Section": None,
            "SplitOptionsIds": [],
            "StockTypeIds": [],
            "Tags": [],
            "ThirdPartyExchangeListingId": None,
            "ThirdPartyExchangeListingStatus": None,
            "ToCost": None,
            "ToCreatedDate": None,
            "ToOnHandDate": None,
            "ToUpdateDate": None,
            "PurchaseOrderIds": [],
            "Status": 3,
            "ShowExchangeInventory": True,
            "ShowMyInventoryFirst": True,
            "ShowMyPastEvents": False,
            "ShowUncategorizedEvents": False,
            "ShowSuggestedPrice": False,
            "SortOptions": {
                "PageNumber": 1,
                "PageSize": 100,
                "ColumnSortOptions": [
                    {"ColumnName": "Wholesale", "SortDirection": "Ascending"}
                ]
            }
        }

        params = {"request": json.dumps(payload)}
        data = await self._request("GET", "/api/TicketGroup", params=params)

        if not data or not isinstance(data, dict):
            return []

        response_data = data.get("Data", {})
        ticket_groups = response_data.get("TicketGroups", {}) if isinstance(response_data, dict) else {}
        items_raw = ticket_groups.get("Items", []) if isinstance(ticket_groups, dict) else []

        result = []
        for item in items_raw:
            try:
                result.append(TicketGroupItem.model_validate(item))
            except Exception as e:
                logger.debug(f"Ошибка парсинга группы билетов: {e}")
                continue

        return result
