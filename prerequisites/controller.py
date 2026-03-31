from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from exceptions import DatabaseError, LLMUnreachableError, NotFoundError, UnauthorizedError
from prerequisites.dao import PrerequisiteDAO
from prerequisites.handler import PrerequisiteHandler
from prerequisites.service import PrerequisiteService
from schemas import APIResponse, ErrorDetail

router = APIRouter()


def get_prerequisite_handler(db: Session = Depends(get_db)) -> PrerequisiteHandler:
    prerequisite_dao = PrerequisiteDAO(db)
    return PrerequisiteHandler(
        prerequisite_service=PrerequisiteService(prerequisite_dao),
    )


@router.get("/api/v1/prerequisites/{topic_name}")
async def get_prerequisite(
    topic_name: str,
    request: Request,
    handler: PrerequisiteHandler = Depends(get_prerequisite_handler),
):
    try:
        return handler.get_prerequisite(topic_name=topic_name, request=request)
    except UnauthorizedError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=401, message=str(exc)),
        )
    except NotFoundError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=404, message=str(exc)),
        )
    except LLMUnreachableError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=502, message=str(exc)),
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
