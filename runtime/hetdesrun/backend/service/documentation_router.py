import logging

from uuid import UUID

from fastapi import APIRouter, Path, status, HTTPException

from hetdesrun.backend.models.info import DocumentationFrontendDto

from hetdesrun.persistence.dbservice.revision import (
    read_single_transformation_revision,
    update_or_create_single_transformation_revision,
)

from hetdesrun.persistence.dbservice.exceptions import (
    DBNotFoundError,
    DBIntegrityError,
)


logger = logging.getLogger(__name__)


documentation_router = APIRouter(
    prefix="/documentations",
    tags=["documentations"],
    responses={  # are these only used for display in the Swagger UI?
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Documentation not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


@documentation_router.get(
    "/{id}",
    response_model=DocumentationFrontendDto,
    summary="Returns the documentation with the given id.",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Successfully got the documentation"}
    },
    deprecated=True,
)
async def get_component_revision_by_id(
    id: UUID = Path(
        ...,
        example=UUID("123e4567-e89b-12d3-a456-426614174000"),
    ),
) -> DocumentationFrontendDto:
    """Get the documentation of a transformation revision by its id from the data base.

    This endpoint is deprecated and will be removed soon,
    use GET /api/transformations/{id} instead.
    """

    logger.info(f"get documentation {id}")

    try:
        transformation_revision = read_single_transformation_revision(id)
        logger.info(f"found documentation with id {id}")
    except DBNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))

    documentation_dto = DocumentationFrontendDto.from_transformation_revision(
        transformation_revision
    )
    logger.debug(documentation_dto.json())

    return documentation_dto


@documentation_router.put(
    "/{id}",
    response_model=DocumentationFrontendDto,
    summary="Updates a documentation.",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "Successfully updated the documentation"
        }
    },
    deprecated=True,
)
async def update_documentation(
    id: UUID,
    documentation_dto: DocumentationFrontendDto,
) -> DocumentationFrontendDto:
    """Update or store the documentation of a transformation revision in the data base.

    This endpoint is deprecated and will be removed soon,
    use PUT /api/transformations/{id} instead
    """

    logger.info(f"update documentation {id}")

    if id != documentation_dto.id:
        msg = (
            f"The id {id} does not match "
            f"the id of the documentation DTO {documentation_dto.id}"
        )
        logger.error(msg)
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=msg)

    try:
        transformation_revision = read_single_transformation_revision(id)
    except DBNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))

    transformation_revision.documentation = documentation_dto.document

    try:
        persisted_transformation_revision = (
            update_or_create_single_transformation_revision(transformation_revision)
        )
        logger.info("updated documentation {id}")
    except DBIntegrityError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except DBNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))

    persisted_documentation_dto = DocumentationFrontendDto.from_transformation_revision(
        persisted_transformation_revision
    )
    logger.debug(persisted_documentation_dto.json())

    return persisted_documentation_dto


@documentation_router.delete(
    "/{id}",
    summary="Deletes a documentation.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Successfully deleted the documentation"
        },
    },
    deprecated=True,
)
async def delete_documentation(
    id: UUID,
) -> None:
    """Change the documentation of a transformation revision in the data base to "".

    This endpoint is deprecated and will be removed soon,
    use PUT /api/transformations/{id} instead
    """

    logger.info(f"delete documentation {id}")

    try:
        transformation_revision = read_single_transformation_revision(id)
    except DBNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))

    transformation_revision.documentation = ""

    try:
        update_or_create_single_transformation_revision(transformation_revision)
        logger.info("deleted documentation {id}")
    except DBIntegrityError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except DBNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
