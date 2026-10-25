"""
Асинхронный HTTP-клиент для взаимодействия с REST API бэкенда FastAPI «Горизонт».
Обеспечивает авторизацию по JWT, кэширование токенов по Telegram User ID,
получение баланса колеса жизни, списка целей и создание новых карточек.
"""

from typing import Dict, Any, Optional, List
import httpx
from config import API_BASE_URL, REQUEST_TIMEOUT


class BackendConnectionError(Exception):
    """Исключение при невозможности связаться с бэкендом FastAPI."""
    pass


class AuthenticationError(Exception):
    """Исключение при ошибке авторизации или истечении токена."""
    pass


class HorizontApiClient:
    """
    Клиент взаимодействия с бэкендом «Горизонт» через httpx.AsyncClient.
    Хранит токены авторизованных пользователей Telegram в памяти.
    """

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        # Сессии пользователей: telegram_id -> {"token": "...", "user": {...}}
        self._sessions: Dict[int, Dict[str, Any]] = {}

    def get_session(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить сохраненную сессию пользователя."""
        return self._sessions.get(telegram_id)

    def is_authenticated(self, telegram_id: int) -> bool:
        """Проверить, авторизован ли пользователь Telegram."""
        sess = self.get_session(telegram_id)
        return bool(sess and sess.get("token"))

    def get_token(self, telegram_id: int) -> Optional[str]:
        """Получить JWT-токен пользователя."""
        sess = self.get_session(telegram_id)
        return sess.get("token") if sess else None

    def logout(self, telegram_id: int) -> bool:
        """Удалить сессию пользователя."""
        if telegram_id in self._sessions:
            del self._sessions[telegram_id]
            return True
        return False

    async def check_health(self) -> bool:
        """Проверить доступность сервера FastAPI."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def login(self, telegram_id: int, login_or_email: str, password: str) -> Dict[str, Any]:
        """
        Авторизация пользователя на бэкенде.
        Сохраняет полученный JWT-токен в сессию пользователя Telegram.
        """
        identifier = login_or_email.strip().lower()
        payload = {
            "username": identifier,
            "email": identifier if "@" in identifier else None,
            "password": password
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.post(f"{self.base_url}/auth/login", json=payload)
        except (httpx.ConnectError, httpx.TimeoutException) as err:
            raise BackendConnectionError(
                f"Не удалось подключиться к серверу «Горизонт» ({self.base_url}). Проверьте, запущен ли FastAPI."
            ) from err

        if resp.status_code == 400 or resp.status_code == 401:
            err_data = resp.json() if resp.headers.get("content-type") == "application/json" else {}
            detail = err_data.get("detail", "Неверный логин или пароль")
            raise AuthenticationError(detail)

        if not resp.is_success:
            raise BackendConnectionError(f"Ошибка сервера ({resp.status_code}): {resp.text}")

        data = resp.json()
        token = data.get("access_token")
        user_info = data.get("user", {})

        if not token:
            raise AuthenticationError("Сервер не вернул токен авторизации")

        # Сохраняем сессию
        self._sessions[telegram_id] = {
            "token": token,
            "user": user_info
        }
        return user_info

    def _get_headers(self, telegram_id: int) -> Dict[str, str]:
        """Сформировать заголовки запроса с Bearer-токеном."""
        token = self.get_token(telegram_id)
        if not token:
            raise AuthenticationError("Пользователь не авторизован в боте. Используйте /login.")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    async def get_spheres(self, telegram_id: int) -> List[Dict[str, Any]]:
        """Получить список сфер жизни пользователя с баллами."""
        headers = self._get_headers(telegram_id)
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(f"{self.base_url}/spheres", headers=headers)
        except (httpx.ConnectError, httpx.TimeoutException) as err:
            raise BackendConnectionError("Сбой соединения с сервером при получении сфер") from err

        if resp.status_code == 401:
            self.logout(telegram_id)
            raise AuthenticationError("Сессия истекла. Пожалуйста, выполните повторный вход через /login.")

        if not resp.is_success:
            raise BackendConnectionError(f"Ошибка при запросе сфер: {resp.status_code}")

        return resp.json()

    async def get_goals(self, telegram_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получить реестр целей пользователя."""
        headers = self._get_headers(telegram_id)
        params = {}
        if status and status != "all":
            params["status"] = status

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(f"{self.base_url}/goals", headers=headers, params=params)
        except (httpx.ConnectError, httpx.TimeoutException) as err:
            raise BackendConnectionError("Сбой соединения с сервером при получении целей") from err

        if resp.status_code == 401:
            self.logout(telegram_id)
            raise AuthenticationError("Сессия истекла. Пожалуйста, выполните повторный вход через /login.")

        if not resp.is_success:
            raise BackendConnectionError(f"Ошибка при запросе целей: {resp.status_code}")

        return resp.json()

    async def get_exchange_rate(self) -> float:
        """Получить официальный курс USD/BYN от Нацбанка РБ."""
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(f"{self.base_url}/currency/rates")
                if resp.is_success:
                    data = resp.json()
                    return float(data.get("rate", 2.9543))
        except Exception:
            pass
        return 2.9543

    async def create_goal(
        self,
        telegram_id: int,
        title: str,
        sphere_id: str,
        cost_amount: float = 0.0,
        currency: str = "BYN",
        priority: str = "medium",
        deadline: Optional[str] = None
    ) -> Dict[str, Any]:
        """Создать новую цель через REST API."""
        headers = self._get_headers(telegram_id)
        payload = {
            "title": title.strip(),
            "sphere_id": sphere_id,
            "cost_amount": cost_amount,
            "currency": currency.upper(),
            "priority": priority,
            "deadline": deadline,
            "steps": []
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.post(f"{self.base_url}/goals", headers=headers, json=payload)
        except (httpx.ConnectError, httpx.TimeoutException) as err:
            raise BackendConnectionError("Сбой соединения с сервером при создании цели") from err

        if resp.status_code == 401:
            self.logout(telegram_id)
            raise AuthenticationError("Сессия истекла. Пожалуйста, выполните повторный вход.")

        if not resp.is_success:
            err_msg = resp.text
            try:
                err_msg = resp.json().get("detail", err_msg)
            except Exception:
                pass
            raise BackendConnectionError(f"Не удалось создать цель: {err_msg}")

        return resp.json()

    async def get_status_overview(self, telegram_id: int) -> Dict[str, Any]:
        """
        Сводная аналитика для команды /status:
        - Индекс гармонии колеса баланса (%)
        - Средний балл сфер
        - Список сфер и их баллы
        - Количество целей по статусам
        - Суммарный бюджет в BYN и USD
        - Курс валюты НБРБ
        """
        spheres = await self.get_spheres(telegram_id)
        goals = await self.get_goals(telegram_id)
        fx_rate = await self.get_exchange_rate()
        user_info = self.get_session(telegram_id).get("user", {})

        # Расчет индекса гармонии
        scores = [float(s.get("current_score", 0.0)) for s in spheres]
        avg_score = (sum(scores) / len(scores)) if scores else 0.0

        harmony_percent = 80
        if scores:
            mean = avg_score
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            std_dev = variance ** 0.5
            harmony_percent = max(10, min(100, int(round((1.0 - (std_dev / 5.0)) * 100))))

        # Статистика целей
        total_goals = len(goals)
        in_progress_count = sum(1 for g in goals if g.get("status") == "in_progress")
        achieved_count = sum(1 for g in goals if g.get("status") == "achieved")
        draft_count = sum(1 for g in goals if g.get("status") == "draft")

        # Мультивалютный подсчет бюджета
        total_byn = 0.0
        total_usd = 0.0
        for g in goals:
            amt = float(g.get("cost_amount") or 0.0)
            cur = (g.get("currency") or "BYN").upper()
            if cur == "BYN":
                total_byn += amt
                total_usd += amt / fx_rate
            else:
                total_usd += amt
                total_byn += amt * fx_rate

        return {
            "user": user_info,
            "harmony_percent": harmony_percent,
            "avg_score": round(avg_score, 1),
            "spheres": spheres,
            "total_goals": total_goals,
            "in_progress_goals": in_progress_count,
            "achieved_goals": achieved_count,
            "draft_goals": draft_count,
            "total_byn": round(total_byn, 2),
            "total_usd": round(total_usd, 2),
            "fx_rate": fx_rate
        }


# Глобальный синглтон API-клиента
api_client = HorizontApiClient()
