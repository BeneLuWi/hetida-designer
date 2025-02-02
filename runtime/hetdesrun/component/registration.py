"""Component entrypoint registration utilities"""

from typing import Dict, Callable, Optional

import asyncio
import functools

from hetdesrun.datatypes import DataType

from hetdesrun.runtime.context import execution_context

from hetdesrun.component.load import ComponentCodeImportError


class ComponentEntryPointRegistrationError(ComponentCodeImportError):
    pass


def gen_default_return_for_plot_func(outputs: dict) -> dict:
    """Generate answer for plot component if it should not be executed

    If plot component is not executed, its PlotlyJson outputs should be empty dicts.
    This function prepares this output from the provided outputs
    """
    return {key: {} for key in outputs.keys()}


def register(
    *,
    inputs: Dict[str, DataType],
    outputs: Dict[str, DataType],
    is_pure_plot_component: bool = False,
    component_name: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    uuid: Optional[str] = None,
    group_id: Optional[str] = None,
    tag: Optional[str] = None,
) -> Callable[[Callable], Callable]:
    """Additonal features for component entrypoint functions

    This decorator can be used to provide additional features for component entrypoint
    functions which may depend on datatype infos on the inputs and outputs.

    is_pure_plot_component: This marks the component as a "pure plot" component
    meaning that this component should not be executed when the appropriate
    workflow execution flag named "run_pure_plot_operators" is set to False. In this
    case it will not run the entrypoint function code and provide empty dictionaríes
    to the outputs (which must all be of PlotlyJson type!).
    """
    if is_pure_plot_component and not all(
        (output_type == DataType.PlotlyJson for output_type in outputs.values())
    ):
        raise ComponentEntryPointRegistrationError(
            (
                "If a component entrypoint function is marked as a pure plot"
                " component, all outputs must be of PlotlyJson datatype!"
            )
        )

    def wrapper_func(func: Callable) -> Callable:

        if not asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            def return_func_or_coro(*args, **kwargs):  # type: ignore
                exe_context_config = execution_context.get()

                return (
                    func(*args, **kwargs)
                    if (
                        (not is_pure_plot_component)
                        or exe_context_config.run_pure_plot_operators
                    )
                    else gen_default_return_for_plot_func(outputs)
                )

        else:

            @functools.wraps(func)
            async def return_func_or_coro(*args, **kwargs):  # type: ignore
                exe_context_config = execution_context.get()

                return (
                    await func(*args, **kwargs)
                    if (
                        (not is_pure_plot_component)
                        or exe_context_config.run_pure_plot_operators
                    )
                    else gen_default_return_for_plot_func(outputs)
                )

        # add input output infos to function attributes
        return_func_or_coro.inputs = inputs  # type: ignore
        return_func_or_coro.outputs = outputs  # type: ignore
        return_func_or_coro.registered_metadata = {  # type: ignore
            "inputs": inputs,
            "outputs": outputs,
            "name": component_name,
            "description": description,
            "category": category,
            "uuid": uuid,
            "group_id": group_id,
            "tag": tag,
        }

        return return_func_or_coro

    return wrapper_func
