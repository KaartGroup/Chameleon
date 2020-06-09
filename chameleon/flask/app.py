import csv
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from typing import Generator
from uuid import uuid4 as uuid
from zipfile import ZipFile

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

from chameleon.core import ChameleonDataFrame, ChameleonDataFrameSet

app = Flask(__name__)

USER_FILES_BASE = Path("chameleon/flask/files")
RESOURCES_DIR = Path("chameleon/resources")
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
    USER_DIR = USER_FILES_BASE / str(uuid())
    USER_DIR.mkdir(exist_ok=True)

    country: str = request.form.get("location", "", str.upper)

    startdate = request.form.get("startdate", type=datetime.fromisoformat)
    enddate = request.form.get("enddate")
    if enddate:
        enddate = datetime.fromisoformat(enddate)
    # 2012-09-12 is the earliest Overpass can query
    if any(d and d < datetime(2012, 9, 12, 6, 55) for d in (startdate, enddate)):
        raise UnprocessableEntity

    oldfile = request.files.get("old")
    newfile = request.files.get("new")

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

    if all((country, startdate)):
        # Running in easy mode, need to make files for the user
        oldfile, newfile = overpass_getter(country, modes, startdate, enddate)
    elif all((oldfile, newfile)):
        # Manual mode
        oldfile = oldfile.stream
        newfile = newfile.stream
    else:
        # Client-side validation slipped up
        raise UnprocessableEntity
    with oldfile as old, newfile as new:
        cdf_set = ChameleonDataFrameSet(old, new)

    def check_api_deletions(cdfs: ChameleonDataFrameSet) -> Generator:
        REQUEST_INTERVAL = 0.1

        df = cdfs.source_data

        deleted_ids = list(df.loc[df["action"] == "deleted"].index)
        if deleted_ids:
            yield str(Message("max", len(deleted_ids)))
            for num, feature_id in enumerate(deleted_ids):
                yield str(Message("value", num))

                element_attribs = cdfs.check_feature_on_api(
                    feature_id, app_version=APP_VERSION
                )

                df.update(pd.DataFrame(element_attribs, index=[feature_id]))
                gevent.sleep(REQUEST_INTERVAL)

            yield str(Message("value", len(deleted_ids) + 1))

        cdf_set.separate_special_dfs()

        for mode in modes:
            try:
                result = ChameleonDataFrame(
                    cdf_set.source_data, mode=mode, grouping=grouping
                ).query_cdf()
            except KeyError:
                error_list.append(mode)
                continue
            cdf_set.add(result)

        file_name = write_output[file_format](cdf_set, USER_DIR, output)
        # return send_from_directory(
        #     str(BASE_DIR),
        #     file_name,
        #     as_attachment=True,
        #     mimetype=mimetype[file_format],
        # )
        the_path = Path(*(USER_DIR / file_name).parts[-2:])

        yield str(Message("file", the_path))
        # return send_file(
        #     the_path, as_attachment=True, mimetype=mimetype[file_format],
        # )

    return Response(
        stream_with_context(check_api_deletions(cdf_set)),
        mimetype="text/event-stream",
    )


@app.route("/download/<path:unique_id>")
def download_file(unique_id):
    return send_from_directory("files", unique_id)


@app.route("/static/OSMtag.txt")
def return_osm_tag():
    return send_file(RESOURCES_DIR.resolve() / "OSMtag.txt")


def high_deletions_checker(cdf_set) -> bool:
    deletion_percentage = (
        len(cdf_set.source_data[cdf_set.source_data["action"] == "deleted"])
        / len(cdf_set.source_data)
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
    timeout = 120
    try:
        response = dataframe_set.to_geojson(timeout=timeout)
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


def overpass_getter(
    location: str, tags: set, startdate: datetime, enddate: datetime,
) -> Generator:
    api = overpass.API(OVERPASS_TIMEOUT)
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
    formatted_tags = [f'nwr["{tag}"](area.searchArea);' for tag in tags]

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


class Message:
    def __init__(self, message_type: str, value: int):
        self.type = message_type
        self.value = value

    def __str__(self):
        return f"event: {self.type}\ndata: {self.value}\n\n"
