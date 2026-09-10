import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional
from playwright.async_api import async_playwright
from core.config import settings
from core.logger import logger


class PosNextAuth:
    """Управление авторизацией и сессией в POSNext TicketNetwork."""

    def __init__(self, session_path: str = settings.SESSION_FILE_PATH):
        self.session_path = Path(session_path)
        self.bearer_token: Optional[str] = settings.POSNEXT_BEARER_TOKEN
        self.bid: Optional[str] = settings.POSNEXT_BID
        self.uid: Optional[str] = settings.POSNEXT_UID
        self.cookies: Dict[str, str] = {}
        self._load_session()

    def _load_session(self) -> bool:
        """Загружает сохраненную сессию из файла."""
        if not self.session_path.exists():
            return False

        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.bearer_token = data.get("bearer_token") or self.bearer_token
                self.bid = data.get("bid") or self.bid
                self.uid = data.get("uid") or self.uid
                self.cookies = data.get("cookies", {})
                logger.info("Сессия POSNext успешно загружена из session.json")
                return bool(self.bearer_token)
        except Exception as e:
            logger.error(f"Ошибка при чтении {self.session_path}: {e}")
            return False

    def save_session(self) -> None:
        """Сохраняет текущую сессию в файл."""
        try:
            data = {
                "bearer_token": self.bearer_token,
                "bid": self.bid,
                "uid": self.uid,
                "cookies": self.cookies,
            }
            with open(self.session_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Сессия POSNext успешно сохранена в session.json")
        except Exception as e:
            logger.error(f"Ошибка при сохранении сессии: {e}")

    def get_auth_headers(self) -> Dict[str, str]:
        """Возвращает HTTP заголовки для API запросов."""
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://posnext.ticketnetwork.com/",
            "Host": "posnext.ticketnetwork.com"
        }
        if self.bearer_token:
            token = self.bearer_token
            if not token.lower().startswith("bearer "):
                token = f"Bearer {token}"
            headers["Authorization"] = token
        if self.bid:
            headers["Bid"] = str(self.bid)
        if self.uid:
            headers["Uid"] = str(self.uid)
        return headers

    async def login_via_browser(self, headless: bool = True) -> bool:
        """
        Выполняет вход через Playwright, перехватывает Authorization Bearer token,
        Bid, Uid и куки сессии, и сохраняет в session.json.
        """
        if not settings.POSNEXT_EMAIL or not settings.POSNEXT_PASSWORD:
            logger.error("POSNEXT_EMAIL или POSNEXT_PASSWORD не заданы в .env")
            return False

        logger.info("Запуск браузера для авторизации в POSNext...")
        captured_token: Optional[str] = None
        captured_bid: Optional[str] = None
        captured_uid: Optional[str] = None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Перехватываем заголовки сетевых запросов к API
            async def handle_request(req):
                nonlocal captured_token, captured_bid, captured_uid
                if "posnext.ticketnetwork.com/api/" in req.url:
                    headers = req.headers
                    auth_hdr = headers.get("authorization")
                    if auth_hdr:
                        captured_token = auth_hdr
                    if headers.get("bid"):
                        captured_bid = headers.get("bid")
                    if headers.get("uid"):
                        captured_uid = headers.get("uid")

            page.on("request", handle_request)

            try:
                logger.info("Открытие страницы https://posnext.ticketnetwork.com/#/?tab=inventory")
                await page.goto("https://posnext.ticketnetwork.com/#/?tab=inventory", wait_until="networkidle", timeout=45000)

                # Проверяем, произошел ли редирект на страницу авторизации
                current_url = page.url
                logger.info(f"Текущий URL после перехода: {current_url}")

                if "login" in current_url.lower() or "identity" in current_url.lower():
                    logger.info("Обнаружена форма логина, ввод учетных данных...")
                    # Селекторы полей формы
                    email_selector = "input[type='email'], input[name='Email'], input[placeholder*='Email' i], #Email"
                    pass_selector = "input[type='password'], input[name='Password'], #Password"

                    await page.wait_for_selector(email_selector, timeout=15000)
                    await page.fill(email_selector, settings.POSNEXT_EMAIL)
                    await page.fill(pass_selector, settings.POSNEXT_PASSWORD)

                    # Галочка "Keep Me Logged In"
                    keep_logged = page.locator("input[type='checkbox'], #KeepMeLoggedIn")
                    if await keep_logged.count() > 0:
                        try:
                            await keep_logged.first.check()
                        except Exception:
                            pass

                    # Кнопка отправки формы
                    submit_button = page.locator("button:has-text('Log In'), input[type='submit'], button[type='submit']")
                    if await submit_button.count() > 0:
                        await submit_button.first.click()
                    else:
                        await page.keyboard.press("Enter")

                    # Ждем редиректа обратно на POSNext
                    logger.info("Ожидание редиректа на posnext.ticketnetwork.com...")
                    await page.wait_for_url(lambda u: "posnext.ticketnetwork.com" in u and "login" not in u.lower(), timeout=45000)

                # Ждем появления сетевых запросов с авторизацией
                for _ in range(20):
                    if captured_token:
                        break
                    await asyncio.sleep(0.5)

                # Забираем куки
                cookies_list = await context.cookies()
                cookies_dict = {c["name"]: c["value"] for c in cookies_list}

                if captured_token:
                    self.bearer_token = captured_token
                    self.bid = captured_bid or self.bid
                    self.uid = captured_uid or self.uid
                    self.cookies = cookies_dict
                    self.save_session()
                    logger.info("Авторизация через браузер прошла успешно! Токен захвачен.")
                    return True
                else:
                    logger.warning("Не удалось автоматически захватить Bearer-токен из запросов.")
                    return False

            except Exception as e:
                logger.error(f"Ошибка при браузерной авторизации: {e}")
                return False
            finally:
                await browser.close()

    async def ensure_valid_session(self) -> bool:
        """Проверяет наличие токена или запускает процесс авторизации."""
        if self.bearer_token:
            return True
        return await self.login_via_browser(headless=settings.HEADLESS)
