# 🎫 POSNext Solds Parser & Telegram Bot

Высокопроизводительный асинхронный сервис мониторинга и парсинга шоу в POSNext (TicketNetwork).
Позволяет гибко настраивать фильтрацию событий (по дате, порогу проданных билетов, площадкам) через Telegram-бота, отслеживает специфические листинги с тегами (`R`, `Drop`, `Jump`), выводит сводку Топ-3 шоу по солдам и формирует подробный отчет в формате Excel (`.xlsx`).

---

## ⚡ Особенности и возможности

- **Гибридный сбор данных:** Автоматическая тихая авторизация через браузер (Playwright) один раз с сохранением сессии в `session.json`, а весь дальнейший опрос сотен площадок — через прямой асинхронный REST API (`httpx`) за считанные секунды.
- **Интуитивный Telegram-бот (aiogram 3.x):**
  - Кнопки быстрой настройки дат «От» и «До» (формат `MM.DD.YY`, например `10.16.26`).
  - Настройка минимального количества проданных билетов `SoldQuantity >= N`.
  - Динамическое меню управления доступом по Telegram ID для коллег с сохранением в `allowed_users.json`.
  - Живой прогресс-бар с безопасным троттлингом (защита от 429 Flood Control).
- **Подсчет метрики `Active On Hand`:** Фильтрация листингов, содержащих целевые теги `R`, `Drop`, `Jump` при активном признаке On Hand (`IsShort == False`).
- **Профессиональный экспорт Excel (.xlsx):** Таблица с автошириной колонок, шапкой, сеткой, фильтрами и зебра-расцветкой строк.
- **Полная контейнеризация:** Готовые `Dockerfile` и `docker-compose.yml` со всеми системными зависимостями Chromium.

---

## 📁 Структура проекта

```text
c:\POS_Solds_Parser\
├── bot/                      # Модуль Telegram-бота
│   ├── handlers/             # Обработчики (start, settings, access, run)
│   ├── keyboards/            # Инлайн-клавиатуры
│   ├── middlewares/          # Авторизация по Telegram ID
│   ├── states/               # FSM состояния ввода параметров
│   ├── bot_instance.py       # Инициализация бота и диспетчера
│   └── user_state.py         # Состояние фильтров в памяти
├── core/                     # Ядро системы
│   ├── config.py             # Настройки Pydantic Settings
│   ├── logger.py             # Цветное логирование Loguru
│   └── security.py           # Управление правами доступа Telegram ID
├── services/                 # Бизнес-логика
│   ├── posnext/              # Клиент к API TicketNetwork
│   │   ├── auth.py           # Менеджер сессий и браузерный логин
│   │   ├── client.py         # REST клиент (FuzzySearch, TicketGroup)
│   │   └── models.py         # Pydantic схемы данных
│   ├── parser.py             # Логика обхода, фильтрации и Топ-3
│   └── exporter.py           # Генерация Excel отчетов (.xlsx)
├── tests/                    # Набор тестов (pytest)
├── venues.txt                # Список площадок (построчно)
├── Dockerfile                # Сборка контейнера
├── docker-compose.yml        # Конфигурация Docker Compose
├── pyproject.toml / requirements.txt # Зависимости Python
├── main.py                   # Точка входа в приложение
└── README.md                 # Документация
```

---

## 🚀 Установка и запуск

### Вариант 1: Локальный запуск в виртуальном окружении

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/KrosinGG/POS_Solds_Parser.git
   cd POS_Solds_Parser
   ```

2. **Создайте и активируйте виртуальное окружение:**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Установите зависимости и браузер Chromium:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Настройте переменные окружения:**
   Скопируйте `.env.example` в `.env` и заполните ваши данные:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ADMIN_TELEGRAM_ID=987654321

   POSNEXT_EMAIL=your_email@domain.com
   POSNEXT_PASSWORD=your_password
   ```

5. **Заполните список театров в `venues.txt`:**
   ```text
   Warner Theatre
   Kleinhans Music Hall
   Chautauqua Institution Amphitheater
   ```

6. **Запустите приложение:**
   ```bash
   python main.py
   ```

---

### Вариант 2: Запуск в Docker / Docker Compose

1. **Создайте и настройте `.env`:**
   ```bash
   cp .env.example .env
   # отредактируйте .env
   ```

2. **Запустите контейнер:**
   ```bash
   docker compose up -d --build
   ```

3. **Просмотр логов:**
   ```bash
   docker compose logs -f
   ```

---

## 🧪 Запуск тестов

Для проверки работоспособности всех компонентов выполните:
```bash
pytest -v
```

---

## 🔒 Безопасность

- Все секреты (`.env`), файлы сессии (`session.json`), отчеты и виртуальное окружение внесены в `.gitignore`.
- Доступ к Telegram-боту имеют строго доверенные лица, указанные в `ADMIN_TELEGRAM_ID` и добавленные администратором через меню управления доступом.
