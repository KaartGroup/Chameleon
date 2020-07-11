import csv
import json
import shlex
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from typing import Generator, List, Set, TextIO, Tuple
from uuid import uuid4 as uuid
from zipfile import ZipFile

import appdirs
import gevent
import overpass
import oyaml as yaml
import pandas as pd
from flask import (
    Flask,
    Response,
    render_template,
    request,
    safe_join,
    send_file,
    send_from_directory,
    stream_with_context,
)
from werkzeug.exceptions import UnprocessableEntity

from chameleon.core import (
    ChameleonDataFrame,
    ChameleonDataFrameSet,
    TYPE_EXPANSION,
)

app = Flask(__name__)

USER_FILES_BASE = Path(appdirs.user_data_dir("Chameleon"))
RESOURCES_DIR = Path("chameleon/resources")
MODULES_DIR = Path("chameleon/flask/modules/")
OVERPASS_TIMEOUT = 120

try:
    with (RESOURCES_DIR / "version.txt").open("r") as version_file:
        APP_VERSION = version_file.read()
except OSError:
    APP_VERSION = ""

error_list = []


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
    mode_count : indicates how many modes will be processed
    [overpass_complete] (if used) : signals overpass has returned
        and the countdown can stop
    [overpass_failed] (if used) : signals overpass timed out
    osm_api_max : indicates beginining of OSM API queries
    osm_api_value : signals which OSM API is being queried
    mode : signals start of mode processing and which mode is being processed
    file : signals end of processing, includes the url for the generated file
    """
    USER_DIR = USER_FILES_BASE / str(uuid())
    USER_DIR.mkdir(parents=True, exist_ok=True)

    country: str = request.form.get("location", "", str.upper)

    startdate = request.form.get("startdate", type=datetime.fromisoformat)
    enddate = request.form.get("enddate")
    if enddate:
        enddate = datetime.fromisoformat(enddate)
    # 2012-09-12 is the earliest Overpass can query
    if any(d and d < datetime(2012, 9, 12, 6, 55) for d in (startdate, enddate)):
        raise UnprocessableEntity

    filter_list = filter_processing(request.form.getlist("filters"))

    output = request.form.get("output") or "chameleon"
    # Strips leading part of Path from the file name to avoid accidental issues
    # We later use Flask's send_from_directory() to block intentional attacks
    # Also gets rid of any suffixes the user may have added
    while output != Path(output).with_suffix("").name:
        output = Path(output).with_suffix("").name

    grouping = request.form.get("grouping", False, bool)
    modes = set(request.form.getlist("modes"))
    if not modes:  # Should only happen if client-side validation slips up
        raise UnprocessableEntity
    file_format = request.form["file_format"]

    def process_data() -> Generator:
        REQUEST_INTERVAL = 0.1

        oldfile = request.files.get("old")
        newfile = request.files.get("new")

        if all((country, startdate)):
            # Running in easy mode, need to make files for the user
            yield message("mode_count", len(modes))
            yield message("overpass_start", OVERPASS_TIMEOUT)
            try:
                oldfile, newfile = overpass_getter(
                    country, filter_list, modes, startdate, enddate
                )
            except overpass.errors.TimeoutError:
                return message("overpass_failed", None)
            yield message("overpass_complete", None)
        elif all((oldfile, newfile)):
            yield message("mode_count", len(modes))
            # Manual mode
            oldfile = oldfile.stream
            newfile = newfile.stream
        else:
            # Client-side validation slipped up
            raise UnprocessableEntity
        with oldfile as old, newfile as new:
            cdfs = ChameleonDataFrameSet(old, new)

        df = cdfs.source_data

        deleted_ids = list(df.loc[df["action"] == "deleted"].index)
        if deleted_ids:
            yield message("osm_api_max", len(deleted_ids))
            for num, feature_id in enumerate(deleted_ids):
                yield message("osm_api_value", num)

                element_attribs = cdfs.check_feature_on_api(
                    feature_id, app_version=APP_VERSION
                )

                df.update(pd.DataFrame(element_attribs, index=[feature_id]))
                gevent.sleep(REQUEST_INTERVAL)

            yield message("osm_api_value", len(deleted_ids))

        cdfs.separate_special_dfs()

        # yield message("start_modes", None)
        for mode in modes:
            yield message("mode", mode)
            try:
                result = ChameleonDataFrame(
                    cdfs.source_data, mode=mode, grouping=grouping
                ).query_cdf()
            except KeyError:
                error_list.append(mode)
                continue
            cdfs.add(result)

        file_name = write_output[file_format](cdfs, USER_DIR, output)
        # return send_from_directory(
        #     str(BASE_DIR),
        #     file_name,
        #     as_attachment=True,
        #     mimetype=mimetype[file_format],
        # )
        the_path = Path(*(USER_DIR / file_name).parts[-2:])

        yield str(message("file", the_path))
        # return send_file(
        #     the_path, as_attachment=True, mimetype=mimetype[file_format],
        # )

    return Response(
        stream_with_context(process_data()), mimetype="text/event-stream",
    )


@app.route("/download/<path:unique_id>")
def download_file(unique_id):
    return send_from_directory("files", unique_id)


@app.route("/static/OSMtag.txt")
def return_osm_tag():
    return send_file(RESOURCES_DIR.resolve() / "OSMtag.txt")


@app.route("/static/sse.js")
def return_sse_js():
    return send_file(MODULES_DIR.resolve() / "sse.js/lib/sse.js")


def high_deletions_checker(cdfs) -> bool:
    deletion_percentage = (
        len(cdfs.source_data[cdfs.source_data["action"] == "deleted"])
        / len(cdfs.source_data)
    ) * 100
    return deletion_percentage > 20 and not user_confirm(
        "There is an unusually high proportion of deletions "
        f"({round(deletion_percentage,2)}%). "
        "This often indicates that the two input files have different scope. "
        "Would you like to continue?"
    )


def user_confirm(message):
    # TODO Make a real confirmation prompt
    return True


def load_extra_columns() -> dict:
    try:
        with (RESOURCES_DIR / "extracolumns.yaml").open("r") as f:
            extra_columns = yaml.safe_load(f.read())
    except OSError:
        extra_columns = {"notes": None}
    return extra_columns


def write_csv(dataframe_set, base_dir, output):
    zip_name = f"{output}.zip"
    zip_path = Path(safe_join(base_dir, zip_name)).resolve()

    with ZipFile(zip_path, "w") as myzip, TemporaryDirectory() as tempdir:
        for result in dataframe_set:
            file_name = f"{output}_{result.chameleon_mode}.csv"
            temp_path = Path(tempdir) / file_name
            with temp_path.open("w") as output_file:
                result.to_csv(output_file, sep="\t", index=True)
            myzip.write(temp_path, arcname=file_name)

    return zip_name


def write_excel(dataframe_set, base_dir, output):
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


def filter_processing(filters: List[str]) -> List[dict]:
    filter_list = []
    for filterstring in filters:
        filterstring, typestring = filterstring.rsplit(" (", 1)
        typestring = typestring[:-1]

        if typestring == "nwr":
            types = [typestring]
        else:
            types = [TYPE_EXPANSION[i] for i in typestring]

        for separator in ("=", "~"):  # Probably add more separators
            partitioned = filterstring.partition(separator)
            if partitioned[2]:
                break
        filter_dict = {
            "key": partitioned[0],
            "value": partitioned[2],
            "types": types,
        }
        if filter_dict["value"]:
            splitter = shlex.shlex(filter_dict["value"])
            splitter.whitespace += ",|"
            splitter.whitespace_split = True
            filter_dict["value"] = list(splitter)
        if any(v for k, v in filter_dict.items() if k != "types"):
            filter_list.append(filter_dict)
    return filter_list


def overpass_getter(
    location: str,
    filters: List[Tuple[str, str, Tuple]],
    tags: Set[str],
    startdate: datetime,
    enddate: datetime,
) -> Generator:
    api = overpass.API(OVERPASS_TIMEOUT)

    formatted_tags = []
    for i in filters:
        if i["value"]:
            formatted = f'~"{"|".join(i["value"])}"'
        else:
            formatted = ""
        for t in i["types"]:
            formatted_tags.append(
                f'{t}["{i["key"]}"{formatted}](area.searchArea)'
            )

    modes = tags | {"name"}
    csv_columns = [
        "::type",
        "::id",
        "::user",
        "::timestamp",
        "::version",
        "::changeset",
    ] + list(modes)
    response_format = f'csv({",".join(csv_columns)})'

    overpass_query = (
        f'area["ISO3166-1"="{location}"]->.searchArea;{"".join(formatted_tags)}'
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


def message(message_type: str, value: int) -> str:
    return f"event: {message_type}\ndata: {value}\n\n"
