from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from exceptions import DatabaseError, FeedbackError, RateLimitError, ValidationError
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


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/api/v1/feedback")
def submit_feedback(
    body: FeedbackRequest,
    request: Request,
    handler: FeedbackHandler = Depends(get_feedback_handler),
):
    client_ip = _get_client_ip(request)
    try:
        return handler.submit_feedback(
            blog_id=body.blog_id,
            type=body.type,
            content=body.content,
            client_ip=client_ip,
            name=body.name,
            email=body.email,
            website=body.website,
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
    except DatabaseError:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code=500,
                message="Sorry, your feedback couldn't be processed. Please try again later.",
            ),
        )
    except FeedbackError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message=str(exc)),
        )
