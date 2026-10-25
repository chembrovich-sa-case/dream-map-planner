"""
Роутер аналитики и исторических данных (UC: Баланс жизни во времени).
Предоставляет REST API для работы с таблицами balance_snapshots и balance_snapshot_items.
"""

import math
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import BalanceSnapshot, BalanceSnapshotItem, LifeSphere, User
from schemas import (
    BalanceSnapshotCreate,
    BalanceSnapshotResponse,
    BalanceSnapshotItemResponse,
    AnalyticsTrendResponse,
    AnalyticsSphereSeries
)
from routers.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Balance Snapshots (История и срезы)"])


def calculate_harmony(scores: List[float]) -> float:
    """
    Расчет индекса гармоничности колеса баланса (от 0.10 до 1.00).
    Основан на оценке дисперсии и стандартного отклонения баллов сфер жизни:
    чем ровнее распределены баллы по сферам, тем выше показатель гармонии.
    """
    if not scores:
        return 1.0
    mean = sum(scores) / len(scores)
    if mean == 0:
        return 0.5
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)
    raw_harmony = 1.0 - (std_dev / 5.0)
    return max(0.10, min(1.00, round(raw_harmony, 2)))


@router.post(
    "/snapshots",
    response_model=BalanceSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Зафиксировать исторический срез баланса жизни",
    description="Сохраняет точку среза в таблице balance_snapshots. Если список сфер не передан, автоматически берет актуальные баллы текущих сфер жизни пользователя и рассчитывает индекс гармонии."
)
def create_snapshot(
    snapshot_in: BalanceSnapshotCreate = BalanceSnapshotCreate(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recorded_at = snapshot_in.recorded_at or datetime.now(timezone.utc)
    
    # Получаем сферы пользователя
    user_spheres = db.query(LifeSphere).filter(LifeSphere.user_id == current_user.id).order_by(LifeSphere.sort_order.asc()).all()
    if not user_spheres:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя нет настроенных сфер жизни для фиксации среза"
        )
    
    # Автоматически пересчитываем текущие баллы сфер перед срезом
    for s in user_spheres:
        s.recalculate_score()
    db.commit()

    items_data = []
    scores = []
    
    if snapshot_in.items and len(snapshot_in.items) > 0:
        # Пользователь явно передал баллы
        for it in snapshot_in.items:
            items_data.append({
                "sphere_id": it.sphere_id,
                "score": it.score,
                "target_score": it.target_score
            })
            scores.append(float(it.score))
    else:
        # Автоматический срез по всем сферам пользователя
        for s in user_spheres:
            score = s.current_score
            target = s.target_score
            items_data.append({
                "sphere_id": s.id,
                "score": score,
                "target_score": target
            })
            scores.append(float(score))

    harmony = Decimal(str(calculate_harmony(scores)))

    snapshot = BalanceSnapshot(
        user_id=current_user.id,
        overall_harmony_index=harmony,
        notes=snapshot_in.notes or f"Срез баланса от {recorded_at.strftime('%d.%m.%Y %H:%M')}",
        recorded_at=recorded_at
    )
    db.add(snapshot)
    db.flush()

    # Сохраняем строки среза balance_snapshot_items
    sphere_map = {s.id: s for s in user_spheres}
    result_items = []
    for it_dict in items_data:
        item = BalanceSnapshotItem(
            snapshot_id=snapshot.id,
            sphere_id=it_dict["sphere_id"],
            score=it_dict["score"],
            target_score=it_dict["target_score"]
        )
        db.add(item)
        db.flush()
        
        s_obj = sphere_map.get(item.sphere_id)
        result_items.append(
            BalanceSnapshotItemResponse(
                id=item.id,
                snapshot_id=snapshot.id,
                sphere_id=item.sphere_id,
                score=item.score,
                target_score=item.target_score,
                sphere_title=s_obj.title if s_obj else "Сфера",
                sphere_color=s_obj.color if s_obj else "#3B82F6",
                sphere_icon=s_obj.icon if s_obj else "compass"
            )
        )

    db.commit()
    db.refresh(snapshot)

    resp = BalanceSnapshotResponse.model_validate(snapshot)
    resp.items = result_items
    return resp


@router.get(
    "/snapshots",
    response_model=List[BalanceSnapshotResponse],
    summary="Получить историю срезов баланса пользователя",
    description="Возвращает хронологический список срезов из таблицы balance_snapshots с деталями по сферам (balance_snapshot_items)."
)
def get_snapshots(
    days: Optional[int] = Query(None, description="Фильтр по количеству дней (например, 30, 90)"),
    limit: int = Query(50, ge=1, le=200, description="Максимальное количество срезов"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(BalanceSnapshot).options(
        joinedload(BalanceSnapshot.items).joinedload(BalanceSnapshotItem.sphere)
    ).filter(BalanceSnapshot.user_id == current_user.id)

    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.filter(BalanceSnapshot.recorded_at >= since)

    snapshots = query.order_by(BalanceSnapshot.recorded_at.asc()).limit(limit).all()

    result = []
    for sn in snapshots:
        sn_dict = BalanceSnapshotResponse.model_validate(sn)
        items_resp = []
        for it in sn.items:
            s_obj = it.sphere
            items_resp.append(
                BalanceSnapshotItemResponse(
                    id=it.id,
                    snapshot_id=sn.id,
                    sphere_id=it.sphere_id,
                    score=it.score,
                    target_score=it.target_score,
                    sphere_title=s_obj.title if s_obj else "Сфера",
                    sphere_color=s_obj.color if s_obj else "#3B82F6",
                    sphere_icon=s_obj.icon if s_obj else "compass"
                )
            )
        sn_dict.items = items_resp
        result.append(sn_dict)

    return result


@router.get(
    "/trend",
    response_model=AnalyticsTrendResponse,
    summary="Получить агрегированный тренд аналитики для графиков Chart.js",
    description="Возвращает подготовленные временные ряды: метки дат, динамику общего индекса гармонии (%) и баллы по каждой жизненной сфере."
)
def get_analytics_trend(
    days: Optional[int] = Query(None, description="Период в днях (по умолчанию все)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Получаем срезы
    snapshots = get_snapshots(days=days, limit=100, db=db, current_user=current_user)
    
    # Если срезов нет, автоматически создаем первоначальный срез на основе текущего состояния
    if not snapshots:
        initial = create_snapshot(BalanceSnapshotCreate(notes="Начальный срез колеса баланса"), db=db, current_user=current_user)
        snapshots = [initial]

    labels = []
    dates = []
    harmony_series = []
    
    # Словарь сфер: sphere_id -> { "sphere_id", "title", "color", "icon", "scores": [] }
    spheres_dict = {}

    all_spheres = db.query(LifeSphere).filter(LifeSphere.user_id == current_user.id).order_by(LifeSphere.sort_order.asc()).all()
    for s in all_spheres:
        spheres_dict[str(s.id)] = {
            "sphere_id": s.id,
            "title": s.title,
            "color": s.color,
            "icon": s.icon,
            "scores": []
        }

    for sn in snapshots:
        dt = sn.recorded_at
        labels.append(dt.strftime("%d.%m"))
        dates.append(dt.isoformat())
        
        h_val = float(sn.overall_harmony_index or 0.5) * 100.0
        harmony_series.append(round(h_val, 1))

        sn_items_map = {str(it.sphere_id): float(it.score) for it in sn.items}
        for s_id_str, s_info in spheres_dict.items():
            sc = sn_items_map.get(s_id_str, 0.0)
            s_info["scores"].append(round(sc, 1))

    cur_h = harmony_series[-1] if harmony_series else 50.0
    earliest_h = harmony_series[0] if harmony_series else 50.0
    delta = round(cur_h - earliest_h, 1)
    percent_growth = round(((cur_h - earliest_h) / earliest_h * 100.0), 1) if earliest_h > 0 else 0.0

    spheres_series_objs = [
        AnalyticsSphereSeries(
            sphere_id=s_info["sphere_id"],
            title=s_info["title"],
            color=s_info["color"],
            icon=s_info["icon"],
            scores=s_info["scores"]
        )
        for s_info in spheres_dict.values()
    ]

    return AnalyticsTrendResponse(
        labels=labels,
        dates=dates,
        harmony_series=harmony_series,
        spheres_series=spheres_series_objs,
        snapshots_count=len(snapshots),
        current_harmony_index=round(cur_h / 100.0, 2),
        earliest_harmony_index=round(earliest_h / 100.0, 2),
        improvement_delta=delta,
        improvement_percent=percent_growth
    )


@router.delete(
    "/snapshots/{snapshot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить срез баланса"
)
def delete_snapshot(
    snapshot_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    snapshot = db.query(BalanceSnapshot).filter(BalanceSnapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Срез баланса не найден"
        )
    if current_user.role != "admin" and snapshot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления данного среза"
        )
    db.delete(snapshot)
    db.commit()
    return None
