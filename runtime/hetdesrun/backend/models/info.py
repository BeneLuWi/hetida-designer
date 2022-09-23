import datetime
from typing import Optional
from uuid import UUID, uuid4

# pylint: disable=no-name-in-module
from pydantic import BaseModel, Field, validator

from hetdesrun.backend.service.utils import to_camel
from hetdesrun.datatypes import AdvancedTypesOutputSerializationConfig
from hetdesrun.persistence.models.transformation import TransformationRevision
from hetdesrun.utils import State, Type


class BasicInformation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    group_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., max_length=60)
    description: str
    category: str = Field(..., max_length=60)
    type: Type
    state: State
    tag: str = Field(..., max_length=20)

    @validator("tag")
    # pylint: disable=no-self-argument
    def tag_not_latest(cls, tag: str) -> str:
        if tag != "latest":
            return tag
        raise ValueError("'latest' is a tag value for internal use only!")

    class Config:
        alias_generator = to_camel


class DocumentationFrontendDto(BaseModel):
    id: UUID
    document: str

    @classmethod
    def from_transformation_revision(
        cls, transformation_revision: TransformationRevision
    ) -> "DocumentationFrontendDto":
        return DocumentationFrontendDto(
            id=transformation_revision.id,
            document=transformation_revision.documentation,
        )


class ExecutionResponseFrontendDto(BaseModel):
    error: Optional[str]
    execution_id: Optional[UUID]
    output_results_by_output_name: dict = {}
    output_types_by_output_name: dict = {}
    response: Optional[str]
    result: str
    traceback: Optional[str]
    job_id: UUID
    pure_execution_time: Optional[datetime.timedelta] = Field(
        None,
        description=(
            "Pure execution time after parsing workflow/data "
            "and before serializing/sending results."
            " Only available if execution was successful."
        ),
    )

    runtime_service_handling_time: Optional[datetime.timedelta] = Field(
        None,
        description=(
            "Full runtime handling duration."
            " Includes Workflow parsing, data loading via adapters,"
            " execution, sending result data via adapters."
            " Does not include parsing the execution request itself and"
            " serialization/sending its response."
            " Only available if execution was successful."
        ),
    )

    load_data_duration: Optional[datetime.timedelta] = Field(
        None,
        description=(
            "Duration of loading data via adapter system as specified in wiring"
            " Includes parsing of directly provisioned data"
            " (i.e. as part of request json)."
            " Only available if execution was successful."
        ),
    )

    send_data_duration: Optional[datetime.timedelta] = Field(
        None,
        description=(
            "Duration of sending result data via adapter system as specified in wiring"
            " Includes serialization of directly provisioned data for"
            " (i.e. as part of request response)."
            " Only available if execution was successful."
        ),
    )

    prepare_execution_input_duration: Optional[datetime.timedelta] = Field(
        None,
        description=(
            "Duration of loading transformation revision(s) from db,"
            " and preparing execution input"
            " Only available if execution was successful."
        ),
    )

    Config = AdvancedTypesOutputSerializationConfig  # enable Serialization of some advanced types


class ExecutionResultReceived(BaseModel):
    ok: bool
