"""
Роутер интеграции с курсами валют Нацбанка РБ (НБРБ) и мультивалютных конвертаций.
"""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx
from database import get_db
from models import ExchangeRateCache
from schemas import (
    ExchangeRateResponse, CurrencyConvertRequest, CurrencyConvertResponse
)

router = APIRouter(prefix="/api/currency", tags=["Currency & FX (НБРБ)"])

NBRB_USD_API_URL = "https://api.nbrb.by/exrates/rates/431?periodicity=0"
DEFAULT_FALLBACK_RATE = Decimal("2.9543")


@router.get(
    "/rates",
    response_model=ExchangeRateResponse,
    summary="Получить актуальный официальный курс USD/BYN",
    description="Возвращает кэшированный курс Нацбанка РБ из БД. Если кэш старше 24 часов, запрашивает свежий курс через API НБРБ."
)
async def get_exchange_rate(db: Session = Depends(get_db)):
    cached = db.query(ExchangeRateCache).filter(ExchangeRateCache.currency_code == "USD").first()
    
    # Проверяем свежесть кэша (если запись создана сегодня)
    now_utc = datetime.now(timezone.utc)
    if cached and cached.fetched_at and (now_utc - cached.fetched_at.replace(tzinfo=timezone.utc)) < timedelta(hours=24):
        return ExchangeRateResponse.model_validate(cached)

    # Иначе запрашиваем из API НБРБ
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(NBRB_USD_API_URL)
            if resp.status_code == 200:
                data = resp.json()
                new_rate = Decimal(str(data.get("Cur_OfficialRate", DEFAULT_FALLBACK_RATE)))
                rate_date_str = data.get("Date", "").split("T")[0]
                rate_date = date.fromisoformat(rate_date_str) if rate_date_str else date.today()

                if not cached:
                    cached = ExchangeRateCache(
                        currency_code="USD",
                        scale=int(data.get("Cur_Scale", 1)),
                        rate=new_rate,
                        rate_date=rate_date,
                        fetched_at=now_utc
                    )
                    db.add(cached)
                else:
                    cached.rate = new_rate
                    cached.rate_date = rate_date
                    cached.scale = int(data.get("Cur_Scale", 1))
                    cached.fetched_at = now_utc

                db.commit()
                db.refresh(cached)
                return ExchangeRateResponse.model_validate(cached)
    except Exception as e:
        print(f"⚠️ Ошибка вызова API НБРБ ({e}). Используется кэшированный или резервный курс.")

    # Если внешний запрос не удался, возвращаем кэш или дефолт
    if cached:
        return ExchangeRateResponse.model_validate(cached)

    fallback = ExchangeRateCache(
        currency_code="USD",
        scale=1,
        rate=DEFAULT_FALLBACK_RATE,
        rate_date=date.today(),
        fetched_at=now_utc
    )
    db.add(fallback)
    db.commit()
    db.refresh(fallback)
    return ExchangeRateResponse.model_validate(fallback)


@router.post(
    "/refresh",
    response_model=ExchangeRateResponse,
    summary="Принудительное обновление курса из API НБРБ",
    description="Принудительно делает HTTP-запрос к api.nbrb.by и сохраняет свежий курс в базу данных."
)
async def force_refresh_rates(db: Session = Depends(get_db)):
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(NBRB_USD_API_URL)
            if resp.status_code == 200:
                data = resp.json()
                new_rate = Decimal(str(data.get("Cur_OfficialRate", DEFAULT_FALLBACK_RATE)))
                rate_date_str = data.get("Date", "").split("T")[0]
                rate_date = date.fromisoformat(rate_date_str) if rate_date_str else date.today()

                cached = db.query(ExchangeRateCache).filter(ExchangeRateCache.currency_code == "USD").first()
                now_utc = datetime.now(timezone.utc)
                if not cached:
                    cached = ExchangeRateCache(
                        currency_code="USD",
                        scale=int(data.get("Cur_Scale", 1)),
                        rate=new_rate,
                        rate_date=rate_date,
                        fetched_at=now_utc
                    )
                    db.add(cached)
                else:
                    cached.rate = new_rate
                    cached.rate_date = rate_date
                    cached.scale = int(data.get("Cur_Scale", 1))
                    cached.fetched_at = now_utc

                db.commit()
                db.refresh(cached)
                return ExchangeRateResponse.model_validate(cached)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось связаться с сервером Нацбанка РБ: {str(err)}"
        )


@router.post(
    "/convert",
    response_model=CurrencyConvertResponse,
    summary="Конвертация суммы между валютами (BYN ⇄ USD)"
)
async def convert_currency(
    req: CurrencyConvertRequest,
    db: Session = Depends(get_db)
):
    fx = await get_exchange_rate(db)
    rate = fx.rate

    if req.from_currency == req.to_currency:
        converted = req.amount
    elif req.from_currency == "USD" and req.to_currency == "BYN":
        converted = req.amount * rate
    elif req.from_currency == "BYN" and req.to_currency == "USD":
        converted = req.amount / rate
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемая пара валют: {req.from_currency} -> {req.to_currency}"
        )

    return CurrencyConvertResponse(
        amount=req.amount,
        from_currency=req.from_currency,
        to_currency=req.to_currency,
        rate=rate,
        converted_amount=round(converted, 2),
        rate_date=fx.rate_date
    )
