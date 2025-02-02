"""Handle execution of transformation revisions."""

from typing import List, Dict, Union
import json
import logging
from uuid import UUID, uuid4
from posixpath import join as posix_urljoin


from pydantic import (
    BaseModel,
    ValidationError,
    Field,
)  # pylint: disable=no-name-in-module
import httpx

from hetdesrun.models.wiring import WorkflowWiring
from hetdesrun.models.workflow import WorkflowNode
from hetdesrun.models.component import ComponentNode

from hetdesrun.utils import Type, get_auth_headers

from hetdesrun.backend.models.info import ExecutionResponseFrontendDto

from hetdesrun.persistence.models.workflow import WorkflowContent
from hetdesrun.persistence.dbservice.revision import read_single_transformation_revision
from hetdesrun.persistence.dbservice.exceptions import DBNotFoundError, DBIntegrityError


from hetdesrun.webservice.config import runtime_config
from hetdesrun.service.runtime_router import runtime_service

from hetdesrun.persistence.models.transformation import TransformationRevision

from hetdesrun.runtime.logging import execution_context_filter


from hetdesrun.models.run import (
    ConfigurationInput,
    WorkflowExecutionInput,
    WorkflowExecutionResult,
)

from hetdesrun.persistence.dbservice.revision import (
    get_all_nested_transformation_revisions,
)

logger = logging.getLogger(__name__)
logger.addFilter(execution_context_filter)


class ExecByIdInput(BaseModel):
    id: UUID
    wiring: WorkflowWiring
    run_pure_plot_operators: bool = Field(
        False, description="Whether pure plot components should be run."
    )
    job_id: UUID = Field(
        default_factory=uuid4,
        description="Optional job id, that can be used to track an execution job.",
    )


class TrafoExecutionError(Exception):
    pass


class TrafoExecutionNotFoundError(TrafoExecutionError):
    pass


class TrafoExecutionRuntimeConnectionError(TrafoExecutionError):
    pass


class TrafoExecutionResultValidationError(TrafoExecutionError):
    pass


def nested_nodes(
    tr_workflow: TransformationRevision,
    all_nested_tr: Dict[UUID, TransformationRevision],
) -> List[Union[ComponentNode, WorkflowNode]]:
    if tr_workflow.type != Type.WORKFLOW:
        raise ValueError

    assert isinstance(tr_workflow.content, WorkflowContent)  # hint for mypy
    ancestor_operator_ids = [operator.id for operator in tr_workflow.content.operators]
    ancestor_children: Dict[UUID, TransformationRevision] = {}
    for operator_id in ancestor_operator_ids:
        if operator_id in all_nested_tr:
            ancestor_children[operator_id] = all_nested_tr[operator_id]
        else:
            raise DBIntegrityError(
                f"operator {operator_id} of transformation revision {tr_workflow.id} "
                f"not contained in result of get_all_nested_transformation_revisions"
            )

    def children_nodes(
        workflow: WorkflowContent, tr_operators: Dict[UUID, TransformationRevision]
    ) -> List[Union[ComponentNode, WorkflowNode]]:
        sub_nodes: List[Union[ComponentNode, WorkflowNode]] = []

        for operator in workflow.operators:
            if operator.type == Type.COMPONENT:
                sub_nodes.append(
                    tr_operators[operator.id].to_component_node(
                        operator.id, operator.name
                    )
                )
            if operator.type == Type.WORKFLOW:
                tr_workflow = tr_operators[operator.id]
                assert isinstance(tr_workflow.content, WorkflowContent)  # hint for mypy
                operator_ids = [
                    operator.id for operator in tr_workflow.content.operators
                ]
                tr_children = {
                    id: all_nested_tr[id] for id in operator_ids if id in all_nested_tr
                }
                sub_nodes.append(
                    tr_workflow.content.to_workflow_node(
                        operator.id,
                        operator.name,
                        children_nodes(tr_workflow.content, tr_children),
                    )
                )

        return sub_nodes

    return children_nodes(tr_workflow.content, ancestor_children)


def prepare_execution_input(  # pylint: disable=redefined-builtin
    id: UUID, wiring: WorkflowWiring, run_pure_plot_operators: bool, job_id: UUID
) -> WorkflowExecutionInput:
    """Loads trafo revision and prepares execution input from it.

    Loads the trafo revision specified by id and prepares
    an workflow execution input object which can be executed by the runtime
    -- either code or by calling runtime rest endpoint for running
    workflows.

    Note that trafo revisions of type components will be wrapped in
    an ad-hoc workflow structure for execution.
    """
    try:
        transformation_revision = read_single_transformation_revision(id)
        logger.info("found transformation revision with id %s", str(id))
    except DBNotFoundError as e:
        raise TrafoExecutionNotFoundError() from e

    if transformation_revision.type == Type.COMPONENT:
        tr_workflow = transformation_revision.wrap_component_in_tr_workflow()
    else:
        tr_workflow = transformation_revision

    nested_transformations = get_all_nested_transformation_revisions(tr_workflow)
    nested_components = {
        tr.id: tr for tr in nested_transformations.values() if tr.type == Type.COMPONENT
    }
    workflow_node = tr_workflow.to_workflow_node(
        uuid4(), nested_nodes(tr_workflow, nested_transformations)
    )

    execution_input = WorkflowExecutionInput(
        code_modules=[
            tr_component.to_code_module() for tr_component in nested_components.values()
        ],
        components=[
            component.to_component_revision()
            for component in nested_components.values()
        ],
        workflow=workflow_node,
        configuration=ConfigurationInput(
            name=str(tr_workflow.id),
            run_pure_plot_operators=run_pure_plot_operators,
        ),
        workflow_wiring=wiring,
        job_id=job_id,
    )
    return execution_input


async def run_execution_input(
    execution_input: WorkflowExecutionInput,
) -> ExecutionResponseFrontendDto:
    """Runs the provided execution input

    Depending on configuration this either calls a function or queries the
    external runtime service endpoint (if this instance is not considered to
    act as runtime service).

    Raises subtypes of TrafoExecutionError on errors.
    """
    output_types = {
        output.name: output.type for output in execution_input.workflow.outputs
    }

    execution_result: WorkflowExecutionResult

    if runtime_config.is_runtime_service:
        execution_result = await runtime_service(execution_input)
    else:
        headers = get_auth_headers()

        async with httpx.AsyncClient(
            verify=runtime_config.hd_runtime_verify_certs
        ) as client:
            url = posix_urljoin(runtime_config.hd_runtime_engine_url, "runtime")
            try:
                response = await client.post(
                    url,
                    headers=headers,  # TODO: authentication
                    json=json.loads(
                        execution_input.json()
                    ),  # TODO: avoid double serialization.
                    # see https://github.com/samuelcolvin/pydantic/issues/1409 and
                    # https://github.com/samuelcolvin/pydantic/issues/1409#issuecomment-877175194
                )
            except httpx.HTTPError as e:
                msg = f"Failure connecting to hd runtime endpoint ({url}):\n{e}"
                logger.info(msg)
                raise TrafoExecutionRuntimeConnectionError(msg) from e
            try:
                json_obj = response.json()
                execution_result = WorkflowExecutionResult(**json_obj)
            except ValidationError as e:
                msg = (
                    f"Could not validate hd runtime result object. Exception:\n{str(e)}"
                    f"\nJson Object is:\n{str(json_obj)}"
                )
                logger.info(msg)
                raise TrafoExecutionResultValidationError(msg) from e

    execution_response = ExecutionResponseFrontendDto(
        error=execution_result.error,
        output_results_by_output_name=execution_result.output_results_by_output_name,
        output_types_by_output_name=output_types,
        result=execution_result.result,
        traceback=execution_result.traceback,
        job_id=execution_input.job_id,
    )

    return execution_response


async def execute_transformation_revision(  # pylint: disable=redefined-builtin
    id: UUID, wiring: WorkflowWiring, run_pure_plot_operators: bool, job_id: UUID
) -> ExecutionResponseFrontendDto:
    """Execute transformation revision

    raises subtypes of TrafoExecutionError on errors.
    """

    execution_context_filter.bind_context(job_id=job_id)
    execution_input = prepare_execution_input(
        id, wiring, run_pure_plot_operators, job_id
    )
    return await run_execution_input(execution_input)
