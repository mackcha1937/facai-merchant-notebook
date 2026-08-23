"""阶段7离线测评与管理员发布治理API。"""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.application import evaluation_service
from app.core.database import get_db
from app.schemas.evaluation import (
    ConfigDraftCreate, EvaluationRunCreate, ManualResultsImport,
    ReleasePublishRequest, ReleaseRollbackRequest,
)

router = APIRouter(prefix="/api", tags=["v2-stage7"])


@router.get("/v2-stage7/status")
def stage7_status(db: Session = Depends(get_db)):
    return evaluation_service.status(db)


@router.get("/admin/evaluations/drafts")
def drafts(db: Session = Depends(get_db)):
    return evaluation_service.list_drafts(db)


@router.post("/admin/evaluations/drafts")
def create_draft(data: ConfigDraftCreate, db: Session = Depends(get_db)):
    return evaluation_service.create_draft(db, data)


@router.get("/admin/evaluations/runs")
def runs(db: Session = Depends(get_db)):
    return evaluation_service.list_runs(db)


@router.post("/admin/evaluations/runs")
def start_run(data: EvaluationRunCreate, db: Session = Depends(get_db)):
    return evaluation_service.start_run(db, data)


@router.get("/admin/evaluations/runs/{run_id}")
def run_detail(run_id: int, db: Session = Depends(get_db)):
    return evaluation_service.run_detail(db, run_id)


@router.get("/admin/evaluations/runs/{run_id}/workbook.csv", response_class=PlainTextResponse)
def export_workbook(run_id: int, db: Session = Depends(get_db)):
    return PlainTextResponse(evaluation_service.export_csv(db, run_id), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="evaluation-run-{run_id}.csv"'})


@router.post("/admin/evaluations/runs/{run_id}/workbook")
def import_workbook(run_id: int, data: ManualResultsImport, db: Session = Depends(get_db)):
    return evaluation_service.import_csv(db, run_id, data.csv_text)


@router.get("/admin/evaluations/releases")
def releases(db: Session = Depends(get_db)):
    return evaluation_service.list_releases(db)


@router.get("/admin/evaluations/audits")
def audits(db: Session = Depends(get_db)):
    return evaluation_service.list_audits(db)


@router.post("/admin/evaluations/releases/publish")
def publish(data: ReleasePublishRequest, db: Session = Depends(get_db)):
    return evaluation_service.publish(db, data)


@router.post("/admin/evaluations/releases/rollback")
def rollback(data: ReleaseRollbackRequest, db: Session = Depends(get_db)):
    return evaluation_service.rollback(db, data)
