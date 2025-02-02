from typing import Dict, List
import asyncio


import pandas as pd
import numpy as np

from httpx import AsyncClient

from hetdesrun.adapters.exceptions import AdapterOutputDataError

from hetdesrun.models.data_selection import FilteredSink

from hetdesrun.adapters.generic_rest.send_framelike import post_framelike_records
from hetdesrun.webservice.config import runtime_config


def dataframe_to_list_of_dicts(df: pd.DataFrame) -> List[Dict]:
    if len(df) == 0:
        return []
    if not isinstance(df, pd.DataFrame):
        raise AdapterOutputDataError(
            (
                "Did not receive Pandas DataFrame as expected from workflow output."
                f" Got {str(type(df))} instead."
            )
        )

    return df.replace({np.nan: None}).to_dict(orient="records")  # type: ignore


async def post_dataframe(
    df: pd.DataFrame, ref_id: str, adapter_key: str, client: AsyncClient
) -> None:

    records = dataframe_to_list_of_dicts(df)

    await post_framelike_records(
        records,
        ref_id=ref_id,
        adapter_key=adapter_key,
        endpoint="dataframe",
        client=client,
    )


async def post_dataframes(
    dfs: List[pd.DataFrame], ref_ids: List[str], adapter_key: str
) -> None:
    async with AsyncClient(verify=runtime_config.hd_adapters_verify_certs) as client:
        await asyncio.gather(
            *(
                post_dataframe(df, ref_id, adapter_key=adapter_key, client=client)
                for df, ref_id in zip(dfs, ref_ids)
            )
        )


async def send_dataframes_to_adapter(
    filtered_sinks: Dict[str, FilteredSink],
    data_to_send: Dict[str, pd.DataFrame],
    adapter_key: str,
) -> None:

    keys = filtered_sinks.keys()
    ref_ids: List[str] = [str(filtered_sinks[key].ref_id) for key in keys]
    dfs = [data_to_send[key] for key in keys]

    await post_dataframes(dfs, ref_ids=ref_ids, adapter_key=adapter_key)
