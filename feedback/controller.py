from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from exceptions import DatabaseError, RateLimitError, UnauthorizedError, ValidationError
from feedback.dao import FeedbackDAO
from feedback.handler import FeedbackHandler
from feedback.schemas import FeedbackRequest
from feedback.service import FeedbackService
from schemas import APIResponse, ErrorDetail

router = APIRouter()


def get_feedback_handler(db: Session = Depends(get_db)) -> FeedbackHandler:
    feedback_dao = FeedbackDAO(db)
    return FeedbackHandler(
        feedback_service=FeedbackService(feedback_dao),
    )


@router.post("/api/v1/feedback")
async def submit_feedback(
    body: FeedbackRequest,
    request: Request,
    handler: FeedbackHandler = Depends(get_feedback_handler),
):
    try:
        handler.submit_feedback(
            blog_id=body.blog_id,
            type=body.type,
            content=body.content,
            request=request,
        )
        return APIResponse(success=True, data=None, error=None)
    except UnauthorizedError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=401, message=str(exc)),
        )
    except RateLimitError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=429, message=str(exc)),
        )
    except ValidationError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=422, message=str(exc)),
        )
    except DatabaseError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message=str(exc)),
        )
    except Exception as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message=str(exc)),
        )
