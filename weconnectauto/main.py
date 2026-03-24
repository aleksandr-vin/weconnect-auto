from functools import wraps
from typing import Annotated
from enum import StrEnum

import anyio
import typer
from rich import print

from weconnectauto.weconnectapi import WeConnectAPI


class OutputFormat(StrEnum):
    DICT = "dict"
    JSON = "json"
    PYTHON = "python"


state = {
    "verbose": False,
    "cookie_file": "cookies.txt",
    "state_file": "state.json",
    "last_response_file": None,
    "output_format": OutputFormat.DICT,
}


app = typer.Typer(
    no_args_is_help=True,
)


ArgVIN = Annotated[
    str | None,
    typer.Argument(
        help="VIN of the auto. If not provided, first VIN wil be fetched using `user-relations` command."
    ),
]


@app.callback()
def main(
    verbose: bool = False,
    cookie_file=state["cookie_file"],
    state_file=state["state_file"],
    last_response_file: str | None = state["last_response_file"],
    output_format: OutputFormat = state["output_format"],
):
    """
    WeConnect Auto(motive) CLI.
    """
    state["verbose"] = verbose
    state["cookie_file"] = cookie_file
    state["state_file"] = state_file
    state["last_response_file"] = last_response_file
    state["output_format"] = output_format


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        async def run():
            await f(*args, **kwargs)

        return anyio.run(run)

    return wrapper


@app.command()
@coro
async def login(
    username: Annotated[str, typer.Option(..., envvar="VW_USERNAME")],
    password: Annotated[
        str, typer.Option(prompt=True, confirmation_prompt=True, envvar="VW_PASSWORD")
    ],
):
    async with WeConnectAPI(
        username=username,
        password=password,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        await wc.login()


def output(obj):
    match state["output_format"]:
        case OutputFormat.JSON:
            print(obj.model_dump_json(indent=4))
        case OutputFormat.DICT:
            print(obj.model_dump())
        case OutputFormat.PYTHON:
            print(obj)


@app.command()
@coro
async def user():
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        user = await wc.get_user()
        output(user)


@app.command()
@coro
async def user_relations():
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        relations = await wc.get_users_me_relations()
        output(relations)


@app.command()
@coro
async def vehicle_data(vin: ArgVIN = None):
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        if not vin:
            relations = await wc.get_users_me_relations()
            vin = relations.relations[0].vehicle.vin
        vdata = await wc.get_vehicle_data(vin=vin)
        output(vdata)


@app.command()
@coro
async def vehicle_details(vin: ArgVIN = None):
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        if not vin:
            relations = await wc.get_users_me_relations()
            vin = relations.relations[0].vehicle.vin
        vdetails = await wc.get_vehicle_details(vin=vin)
        output(vdetails)


@app.command()
@coro
async def packages(vin: ArgVIN = None):
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        if not vin:
            relations = await wc.get_users_me_relations()
            vin = relations.relations[0].vehicle.vin
        packages = await wc.get_packages(vin=vin)
        output(packages)


@app.command()
@coro
async def download_file(link: str):
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        await wc.download_file(link=link)


@app.command()
@coro
async def user_caps(vin: ArgVIN = None):
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        if not vin:
            relations = await wc.get_users_me_relations()
            vin = relations.relations[0].vehicle.vin
        user_caps = await wc.get_user_caps(vin=vin)
        output(user_caps)


@app.command()
@coro
async def last_warning_lights(vin: ArgVIN = None):
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        if not vin:
            relations = await wc.get_users_me_relations()
            vin = relations.relations[0].vehicle.vin
        warning_lights = await wc.get_last_warning_lights(vin=vin)
        output(warning_lights)


@app.command()
@coro
async def last_cyclic_tripdata(vin: ArgVIN = None):
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        if not vin:
            relations = await wc.get_users_me_relations()
            vin = relations.relations[0].vehicle.vin
        last_cyclic_tripdata = await wc.get_last_cyclic_tripdata(vin=vin)
        output(last_cyclic_tripdata)


@app.command()
@coro
async def last_longterm_tripdata(vin: ArgVIN = None):
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        if not vin:
            relations = await wc.get_users_me_relations()
            vin = relations.relations[0].vehicle.vin
        last_longterm_tripdata = await wc.get_last_longterm_tripdata(vin=vin)
        output(last_longterm_tripdata)


@app.command()
@coro
async def last_shortterm_tripdata(vin: ArgVIN = None):
    async with WeConnectAPI(
        username=None,
        password=None,
        cookie_file=state["cookie_file"],
        state_file=state["state_file"],
        verbose=state["verbose"],
    ) as wc:
        if not vin:
            relations = await wc.get_users_me_relations()
            vin = relations.relations[0].vehicle.vin
        last_shortterm_tripdata = await wc.get_last_shortterm_tripdata(vin=vin)
        output(last_shortterm_tripdata)
