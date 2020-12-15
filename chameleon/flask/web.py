import csv
import json
import os
import shlex
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from typing import Dict, Generator, Iterator, List, TextIO, Union
from uuid import UUID, uuid4
from zipfile import ZipFile

import appdirs
import gevent
import overpass
import pandas as pd
import yaml
from celery import Celery
from celery.contrib.abortable import AbortableAsyncResult, AbortableTask
from celery.exceptions import SoftTimeLimitExceeded
from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    safe_join,
    send_file,
    send_from_directory,
)
from requests import HTTPError, Timeout
from werkzeug.exceptions import UnprocessableEntity

from chameleon.core import (
    TYPE_EXPANSION,
    ChameleonDataFrame,
    ChameleonDataFrameSet,
)

app = Flask(__name__)

backend_user_password = os.getenv("CELERY_BACKEND_USER", "")
if backend_user_password and (pwd := os.getenv("CELERY_BACKEND_PASSWORD", "")):
    backend_user_password += f":{pwd}"
if backend_user_password:
    backend_user_password += "@"

backend_url_port = os.getenv("CELERY_BACKEND_URL", "")
if port := os.getenv("CELERY_BACKEND_PORT", ""):
    backend_url_port += f":{port}"


app.config[
    "CELERY_RESULT_BACKEND"
] = f"db+postgresql://{backend_user_password}{backend_url_port}/celery"
app.config["CELERY_BROKER_URL"] = "redis://"

celery = Celery(
    app.name,
    backend=app.config["CELERY_RESULT_BACKEND"],
    broker=app.config["CELERY_BROKER_URL"],
)
celery.conf.update(app.config)

USER_FILES_BASE = Path(appdirs.user_data_dir("Chameleon"))
RESOURCES_DIR = Path("chameleon/resources")
OVERPASS_TIMEOUT = (
    180  # Locked until GH mvexel/overpass-api-python-wrapper#112 is fixed
)
TASK_TIME_LIMIT = 7200

try:
    with (RESOURCES_DIR / "version.txt").open("r") as version_file:
        APP_VERSION = version_file.read()
except OSError:
    APP_VERSION = ""


class HighDeletionPercentageError(Exception):
    def __init__(self, deletion_percentage):
        super(HighDeletionPercentageError).__init__()
        self.deletion_percentage = deletion_percentage


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/result", methods=["POST"])
def result():
    """
    Yields:
    [overpass_start] (if used) : signals the start of an overpass query
        along with the timeout
    mode_count : indicates how many args['modes'] will be processed
    [overpass_complete] (if used) : signals overpass has returned
        and the countdown can stop
    [overpass_failed] (if used) : signals overpass timed out
    osm_api_max : indicates beginining of OSM API queries
    osm_api_value : signals which OSM API is being queried
    mode : signals start of mode processing and which mode is being processed
    file : signals end of processing, includes the url for the generated file
    """

    args = {
        "country": request.form.get("location", "", str.upper),
        "startdate": request.form.get("startdate", type=datetime.fromisoformat),
        "enddate": request.form.get("enddate"),
        "modes": request.form.getlist("modes"),
        "file_format": request.form["file_format"],
        "filter_list": filter_processing(request.form.getlist("filters")),
        "output": request.form.get("output") or "chameleon",
        # Uses inbuilt UUID validation before converting back to string
        "client_uuid": str(request.form.get("client_uuid", uuid4(), UUID)),
        "grouping": request.form.get("grouping", False, bool),
        "high_deletions_ok": request.form.get("high_deletions_ok", type=bool),
    }
    if not args["modes"]:
        # Should only happen if client-side validation slips up
        raise UnprocessableEntity

    user_dir = Path(safe_join(USER_FILES_BASE, args["client_uuid"]))
    user_dir.mkdir(parents=True, exist_ok=True)
    try:
        input_dir = user_dir / "input"
        input_dir.mkdir(exist_ok=True)

        args["oldfile"] = str(input_dir / "oldfile.csv")
        args["newfile"] = str(input_dir / "newfile.csv")

        request.files.get("old").save(args["oldfile"])
        request.files.get("new").save(args["newfile"])
    except (AttributeError, OSError):
        pass

    try:
        args["enddate"] = datetime.fromisoformat(args["enddate"])
    except (TypeError, ValueError):
        pass

    # 2012-09-12 is the earliest Overpass can query
    if any(
        d and d < datetime(2012, 9, 12, 6, 55)
        for d in (args["startdate"], args["enddate"])
    ):
        raise UnprocessableEntity

    # Gets rid of any suffixes the user may have added
    while args["output"] != Path(args["output"]).stem:
        args["output"] = Path(args["output"]).stem

    task = celery_task.apply_async(args=[args], task_id=args["client_uuid"])

    return (
        jsonify({"client_uuid": task.id, "mode_count": len(args["modes"])}),
        202,
    )


@celery.task(
    bind=True,
    name="chameleon.process_data",
    base=AbortableTask,
    soft_time_limit=TASK_TIME_LIMIT,
)
def celery_task(self, args: dict):
    try:
        for update in process_data(**args):
            if self.is_aborted():
                return {}
            if update["state"] == "SUCCESS":
                return {"file_name": update["meta"]["file_name"]}
            self.update_state(state=update["state"], meta=update["meta"])
    except SoftTimeLimitExceeded:
        return {}


def process_data(
    client_uuid: str,
    modes: List[str],
    file_format: str,
    startdate: datetime = None,
    enddate: datetime = None,
    country: str = "",
    oldfile: str = None,
    newfile: str = None,
    high_deletions_ok=False,
    grouping=False,
    output: str = "chameleon",
    filter_list: List[dict] = [],
    **_,
) -> Iterator[dict]:
    """
    task_metadata:
        current_mode
        current_phase = [overpass|osm_api|modes]
        mode_count
        modes_completed
        osm_api_completed
        osm_api_max
        overpass_start_time
        overpass_timeout_time
    """
    REQUEST_INTERVAL = 0.5

    error_list = []

    user_dir = USER_FILES_BASE / client_uuid
    user_dir.mkdir(parents=True, exist_ok=True)

    task_metadata = {"mode_count": len(modes)}

    easy_mode = all((country, startdate))
    if easy_mode:
        # Need to make files for the user
        overpass_start_time = datetime.now(timezone.utc)
        task_metadata.update(
            {
                "current_phase": "overpass",
                "overpass_start_time": overpass_start_time.isoformat(),
                "overpass_timeout_time": (
                    overpass_start_time + timedelta(seconds=OVERPASS_TIMEOUT)
                ).isoformat(),
            }
        )
        yield {"state": "PROGRESS", "meta": task_metadata}

        oldfile, newfile = overpass_getter(
            modes, country, startdate, enddate, filter_list,
        )
    elif all((oldfile, newfile)):
        # BYOD mode
        yield {"state": "PROGRESS", "meta": task_metadata}
        oldfile = open(oldfile, "r")
        newfile = open(newfile, "r")
    else:
        # Client-side validation slipped up
        raise UnprocessableEntity
    with oldfile as old, newfile as new:
        cdfs = ChameleonDataFrameSet(old, new)

    if (
        not easy_mode
        and not high_deletions_ok
        and (deletion_percentage := high_deletions_checker(cdfs)) > 20
    ):
        raise HighDeletionPercentageError(round(deletion_percentage, 2))

    df = cdfs.source_data

    deleted_ids = list(df.loc[df["action"] == "deleted"].index)
    task_metadata["osm_api_max"] = len(deleted_ids)
    task_metadata["current_phase"] = "osm_api"
    error_count = 0
    for num, feature_id in enumerate(deleted_ids):
        task_metadata["osm_api_completed"] = num
        yield {
            "state": "PROGRESS",
            "meta": task_metadata,
        }
        try:
            element_attribs = cdfs.check_feature_on_api(
                feature_id, app_version=APP_VERSION
            )
        except (Timeout, ConnectionError):
            if error_count > 10:
                # Too many timeouts, abandon online checker
                task_metadata["osm_api_completed"] = task_metadata["osm_api_max"]
                yield {
                    "state": "PROGRESS",
                    "meta": task_metadata,
                }
                break
            error_count += 1
        except HTTPError as e:
            if str(e.response.status_code) == "429":
                raise
        else:
            df.update(pd.DataFrame(element_attribs, index=[feature_id]))
        gevent.sleep(REQUEST_INTERVAL)

    task_metadata["osm_api_completed"] = task_metadata["osm_api_max"]
    task_metadata["current_phase"] = "modes"
    yield {
        "state": "PROGRESS",
        "meta": task_metadata,
    }

    cdfs.separate_special_dfs()

    for num, mode in enumerate(modes):
        # self.update_state(state="MODES", meta={"mode": mode})
        task_metadata["modes_completed"] = num
        task_metadata["current_mode"] = mode
        yield {
            "state": "PROGRESS",
            "meta": task_metadata,
        }

        try:
            result = ChameleonDataFrame(
                cdfs.source_data, mode=mode, grouping=grouping
            ).query_cdf()
        except KeyError:
            error_list.append(mode)
            continue
        cdfs.add(result)

    task_metadata["file_name"] = write_output[file_format](
        cdfs, user_dir, output
    )

    yield {"state": "SUCCESS", "meta": task_metadata}


@app.route("/longtask_status/<uuid:task_id>")
def longtask_status(task_id) -> Response:
    """
    Server Sent Event endpoint for monitoring a task's status until completion
    """
    # Once the UUID has been validated, we want it as a string
    task_id = str(task_id)
    task = celery_task.AsyncResult(task_id)

    def stream_events() -> Generator:
        if task.state == "PENDING":
            # job is unknown
            response = {
                "state": task.state,
                "current_phase": "pending",
            }
            yield message_task_update(response)
        else:
            # In progress
            prior_response = None
            while task.state not in {
                "SUCCESS",
                "FAILURE",
            }:
                try:
                    response = {
                        k: v
                        for k, v in task.info.items()
                        if k
                        in {
                            "current_mode",
                            "current_phase",
                            "mode_count",
                            "modes_completed",
                            "modes_max",
                            "osm_api_completed",
                            "osm_api_max",
                            "overpass_start_time",
                            "overpass_timeout_time",
                            "result",
                        }
                    }
                except AttributeError:
                    response = {}
                response["state"] = task.state

                if response != prior_response:
                    yield message_task_update(response)
                prior_response = response

                gevent.sleep(0.5)

            # Task finished
            if task.state == "SUCCESS":
                try:
                    file_name = task.info.get("file_name")
                except AttributeError:
                    # Can happen if task.info is an Exception
                    file_name = None

                yield message_task_update(
                    {
                        "state": task.state,
                        "uuid": task.id,
                        "file_name": file_name,
                    }
                )
                task.forget()
            elif hasattr(task.info, "deletion_percentage"):
                # Task failed due to high deletion percentage and needs to be reconfirmed
                yield message_task_update(
                    {
                        "state": task.state,
                        "deletion_percentage": task.info.deletion_percentage,
                    }
                )
            else:
                # something went wrong in the background job
                yield message_task_update(
                    {
                        "state": task.state,
                        "error": str(task.info),  # this is the exception raised
                    }
                )

    return Response(stream_events(), mimetype="text/event-stream")


@app.route("/abort", methods=["DELETE"])
def abort_task() -> str:
    """
    Aborts the task with the given id
    """
    task_id = request.json.get("client_uuid")
    AbortableAsyncResult(id=task_id, app=celery).abort()
    return "cancelled"


@app.route("/download/<path:unique_id>")
def download_file(unique_id) -> Response:
    return send_from_directory(
        USER_FILES_BASE.resolve(), unique_id, as_attachment=True
    )


@app.route("/static/OSMtag.txt")
def return_osm_tag() -> Response:
    return send_file(RESOURCES_DIR.resolve() / "OSMtag.txt")


def high_deletions_checker(cdfs: ChameleonDataFrameSet) -> float:
    return (
        len(cdfs.source_data[cdfs.source_data["action"] == "deleted"])
        / max(len(cdfs.source_data), 1)  # Protect against zero division
    ) * 100


def load_extra_columns() -> dict:
    try:
        with (RESOURCES_DIR / "extracolumns.yaml").open("r") as f:
            extra_columns = yaml.safe_load(f.read())
    except OSError:
        extra_columns = {"notes": None}
    return extra_columns


def write_csv(dataframe_set, base_dir, output) -> str:
    zip_name = f"{output}.zip"
    zip_path = Path(safe_join(base_dir, zip_name)).resolve()

    with ZipFile(zip_path, "w") as myzip, TemporaryDirectory() as tempdir:
        for result in dataframe_set:
            file_name = f"{output}_{result.chameleon_mode_cleaned}.csv"
            temp_path = Path(tempdir) / file_name
            with temp_path.open("w") as output_file:
                result.to_csv(output_file, sep="\t", index=True)
            myzip.write(temp_path, arcname=file_name)

    return zip_name


def write_excel(dataframe_set, base_dir, output) -> str:
    file_name = f"{output}.xlsx"
    file_path = Path(safe_join(base_dir, file_name)).resolve()

    dataframe_set.write_excel(file_path)

    return file_name


def write_geojson(dataframe_set, base_dir, output):
    try:
        response = dataframe_set.to_geojson(timeout=OVERPASS_TIMEOUT)
    except TimeoutError:
        # TODO Inform user about error
        return

    file_name = f"{output}.geojson"
    file_path = Path(safe_join(base_dir, file_name)).resolve()

    with file_path.open("w") as output_file:
        json.dump(response, output_file)

    return file_name


write_output = {
    "csv": write_csv,
    "excel": write_excel,
    "geojson": write_geojson,
}

mimetype = {
    # "csv": "text/csv",
    "csv": "application/zip",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "geojson": "application/vnd.geo+json",
}


def filter_processing(
    filters: List[str],
) -> List[Dict[str, List[Union[str, dict]]]]:
    filter_list = []
    for filter in filters:
        filterstring, typestring = filter.rsplit(" (", 1)
        typestring = typestring[:-1]

        filter_map = {
            "types": (
                [typestring]
                if typestring == "nwr"
                else [TYPE_EXPANSION[i] for i in typestring]
            )
        }

        for separator in ("=", "~"):  # Probably add more separators
            filter_map["key"], _, filter_map["value"] = filterstring.partition(
                separator
            )
            if filter_map["value"] == "*":
                filter_map["value"] = ""
                break
            if filter_map["value"]:
                splitter = shlex.shlex(filter_map["value"])
                splitter.whitespace += ",|"
                splitter.whitespace_split = True
                filter_map["value"] = list(splitter)
                break

        if filter_map.get("key") or filter_map.get("value"):
            filter_list.append(filter_map)
    return filter_list


def overpass_getter(
    modes: list,
    country: str,
    startdate: datetime,
    enddate: datetime,
    filter_list: list,
) -> Iterator[TextIO]:
    api = overpass.API(timeout=OVERPASS_TIMEOUT)

    formatted_tags = []
    for i in filter_list:
        formatted = f'~"{"|".join(i["value"])}"' if i["value"] else ""
        for t in i["types"]:
            formatted_tags.append(
                f'{t}["{i["key"]}"{formatted}](area.searchArea)'
            )

    # Cast to set to eliminate any possible duplicates that squeaked through client-side validation
    modes = set(modes) | {"name"}
    csv_columns = [
        "::type",
        "::id",
        "::user",
        "::timestamp",
        "::version",
        "::changeset",
    ] + list(modes)
    response_format = f'csv({",".join(csv_columns)})'

    overpass_query = f'area["ISO3166-1"="{country}"]->.searchArea;' + ";".join(
        formatted_tags
    )

    for date in (startdate, enddate):
        date = date or ""
        response = api.get(
            overpass_query,
            responseformat=response_format,
            verbosity="meta",
            date=date,
        )
        fp = TemporaryFile("w+")
        cwriter = csv.writer(fp, delimiter="\t")
        cwriter.writerows(response)
        fp.seek(0)
        yield fp


def message_task_update(value: dict) -> str:
    return f"event: task_update\ndata: {json.dumps(value)}\n\n"
