from typing import Literal

from datetime import datetime

from hetdesrun.backend.models.transformation import TransformationRevisionFrontendDto
from hetdesrun.backend.models.io import ConnectorFrontendDto
from hetdesrun.backend.models.wiring import WiringFrontendDto
from hetdesrun.utils import Type, State

from hetdesrun.persistence.models.transformation import TransformationRevision
from hetdesrun.persistence.models.io import IOInterface

from hetdesrun.models.wiring import WorkflowWiring
from hetdesrun.models.code import CodeBody


class ComponentRevisionFrontendDto(TransformationRevisionFrontendDto):
    type: Literal[Type.COMPONENT]
    code: str

    class Config:
        arbitrary_types_allowed = True

    def to_transformation_revision(
        self, documentation: str = ""
    ) -> TransformationRevision:
        return TransformationRevision(
            id=self.id,
            revision_group_id=self.group_id,
            name=self.name,
            description=self.description,
            category=self.category,
            version_tag=self.tag,
            released_timestamp=datetime.now() if self.state == State.RELEASED else None,
            disabled_timestamp=datetime.now() if self.state == State.DISABLED else None,
            state=self.state,
            type=self.type,
            documentation=documentation,
            io_interface=IOInterface(
                inputs=[input.to_io() for input in self.inputs],
                outputs=[output.to_io() for output in self.outputs],
            ),
            content=self.code,
            test_wiring=self.wirings[0].to_wiring()
            if len(self.wirings) > 0
            else WorkflowWiring(),
        )

    @classmethod
    def from_transformation_revision(
        cls, transformation_revision: TransformationRevision
    ) -> "ComponentRevisionFrontendDto":
        assert isinstance(transformation_revision.content, str)  # hint for mypy
        return ComponentRevisionFrontendDto(
            id=transformation_revision.id,
            groupId=transformation_revision.revision_group_id,
            name=transformation_revision.name,
            description=transformation_revision.description,
            category=transformation_revision.category,
            type=transformation_revision.type,
            state=transformation_revision.state,
            tag=transformation_revision.version_tag,
            inputs=[
                ConnectorFrontendDto.from_io(io)
                for io in transformation_revision.io_interface.inputs
            ],
            outputs=[
                ConnectorFrontendDto.from_io(io)
                for io in transformation_revision.io_interface.outputs
            ],
            wirings=[
                WiringFrontendDto.from_wiring(
                    transformation_revision.test_wiring, transformation_revision.id
                )
            ]
            if not (
                transformation_revision.test_wiring.input_wirings == []
                and transformation_revision.test_wiring.output_wirings == []
            )
            else [],
            code=transformation_revision.content,
        )
