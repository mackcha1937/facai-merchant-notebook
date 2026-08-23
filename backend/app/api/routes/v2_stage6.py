"""阶段6 SQL 推荐、今日事项、复制话术和反馈 API。"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.application import recommendation_service
from app.core.database import get_db
from app.schemas.recommendation import (
    MessageCopyRequest, MessageRewriteRequest, RecommendationActionRequest,
    RecommendationFeedbackRequest, RecommendationReadRequest,
    RecommendationRefreshRequest,
)


router = APIRouter(prefix="/api", tags=["v2-stage6"])


@router.post("/owner/recommendations/refresh")
def refresh_recommendations(data: RecommendationRefreshRequest, db: Session = Depends(get_db)):
    return recommendation_service.refresh(db, data)


@router.get("/owner/recommendations/today")
def today_recommendations(
    scope: str = Query(default="top3", pattern="^(top3|all)$"),
    target_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
):
    return recommendation_service.list_today(db, scope=scope, target_date=target_date)


@router.get("/owner/recommendations/{recommendation_id}")
def recommendation_detail(recommendation_id: int, db: Session = Depends(get_db)):
    return recommendation_service.get_detail(db, recommendation_id)


@router.post("/owner/recommendations/{recommendation_id}/read")
def read_recommendation(
    recommendation_id: int, data: RecommendationReadRequest, db: Session = Depends(get_db),
):
    return recommendation_service.mark_read(db, recommendation_id, data)


@router.post("/owner/recommendations/{recommendation_id}/actions")
def recommendation_action(
    recommendation_id: int, data: RecommendationActionRequest, db: Session = Depends(get_db),
):
    return recommendation_service.act(db, recommendation_id, data)


@router.post("/owner/recommendations/{recommendation_id}/messages/rewrite")
def rewrite_message(
    recommendation_id: int, data: MessageRewriteRequest, db: Session = Depends(get_db),
):
    return recommendation_service.rewrite_message(db, recommendation_id, data)


@router.post("/owner/recommendations/{recommendation_id}/messages/{draft_id}/copy")
def copy_message(
    recommendation_id: int, draft_id: int, data: MessageCopyRequest,
    db: Session = Depends(get_db),
):
    return recommendation_service.copy_message(db, recommendation_id, draft_id, data)


@router.post("/owner/recommendations/{recommendation_id}/feedback")
def recommendation_feedback(
    recommendation_id: int, data: RecommendationFeedbackRequest, db: Session = Depends(get_db),
):
    return recommendation_service.feedback(db, recommendation_id, data)


@router.get("/admin/recommendation-rules")
def recommendation_rules_readonly(db: Session = Depends(get_db)):
    return recommendation_service.list_rules_readonly(db)


@router.get("/v2-stage6/status")
def stage6_status(db: Session = Depends(get_db)):
    result = recommendation_service.stage_status(db)
    try:
        result["migration"] = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except OperationalError:
        result["migration"] = "metadata-test-db"
    root = Path(__file__).resolve().parents[4]
    report = root / "v2.0" / "stage-6-delivery" / "test-results.json"
    result["test_results"] = {"status": "未验证"}
    if report.exists():
        try:
            result["test_results"] = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            result["test_results"] = {"status": "未验证", "detail": "测试报告暂不可读"}
    return result
