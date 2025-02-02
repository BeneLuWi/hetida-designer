from typing import List
import logging

from fastapi import APIRouter, status, HTTPException

from hetdesrun.webservice.config import runtime_config

from hetdesrun.backend.models.adapter import AdapterFrontendDto

logger = logging.getLogger(__name__)


adapters = runtime_config.hd_adapters


adapter_router = APIRouter(
    prefix="/adapters",
    tags=["adapters"],
    responses={  # are these only used for display in the Swagger UI?
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


@adapter_router.get(
    "/",
    response_model=List[AdapterFrontendDto],
    summary="Returns all adapters",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Successfully got list of adapters"}
    },
)
async def get_all_adapters() -> List[AdapterFrontendDto]:
    """Get all adapters."""
    logger.info(f"get adapters")
    adapter_list: List[AdapterFrontendDto] = []

    if adapters is None:
        return adapter_list

    for adapter in adapters.split(","):
        adapter_properties = adapter.split("|")

        if len(adapter_properties) != 4:
            msg = 'Wrong adapter configuration format - must be "id|name|url|internalUrl,id2|name2|url2|internalUrl2,..."'
            logger.error(msg)
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=msg)

        adapter_list.append(
            AdapterFrontendDto(
                id=adapter_properties[0],
                name=adapter_properties[1],
                url=adapter_properties[2],
                internalUrl=adapter_properties[3],
            )
        )

    return adapter_list
