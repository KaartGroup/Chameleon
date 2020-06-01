import json
import time
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Generator
from uuid import uuid4 as uuid
from zipfile import ZipFile

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

from chameleon import core

app = Flask(__name__)

RESOURCES_DIR = Path()
BASE_DIR = Path("chameleon/flask/files") / str(uuid())
BASE_DIR.mkdir(exist_ok=True)

error_list = []
extra_columns = Path("resources/extracolumns.yaml")


@app.route("/about/")
def about():
    return render_template("about.html")


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/result/", methods=["POST"])
def result():
    # country: str = request.form["country"]
    # startdate = request.form.get("startdate", type=datetime)
    # enddate = request.form.get("enddate", type=datetime)
    oldfile = request.files["old"]
    newfile = request.files["new"]

    output = "chameleon"
    if request.form.get("output"):
        output = request.form["output"]
    output = Path(output).name

    grouping = request.form.get("grouping", False, bool)
    modes = set(request.form.getlist("modes"))
    if not modes:  # Should only happen if client-side validation slips up
        raise KeyError
    file_format = request.form["file_format"]

    cdf_set = core.ChameleonDataFrameSet(oldfile.stream, newfile.stream)

    def check_api_deletions(cdfs: core.ChameleonDataFrameSet) -> Generator:
        REQUEST_INTERVAL = 0.1

        df = cdfs.source_data

        deleted_ids = list(df.loc[df["action"] == "deleted"].index)
        yield str(Message("max", len(deleted_ids)))
        for num, feature_id in enumerate(deleted_ids):
            yield str(Message("value", num))

            element_attribs = cdfs.check_feature_on_api(
                feature_id, app_version=APP_VERSION
            )

            df.update(pd.DataFrame(element_attribs, index=[feature_id]))
            time.sleep(REQUEST_INTERVAL)

        cdf_set.separate_special_dfs()

        for mode in modes:
            try:
                result = core.ChameleonDataFrame(
                    cdf_set.source_data, mode=mode, grouping=grouping
                ).query_cdf()
            except KeyError:
                error_list.append(mode)
                continue
            cdf_set.add(result)

        file_name = write_output[file_format](cdf_set, output)
        # return send_from_directory(
        #     str(BASE_DIR),
        #     file_name,
        #     as_attachment=True,
        #     mimetype=mimetype[file_format],
        # )
        the_path = (BASE_DIR / file_name).resolve()

        yield str(Message("file", the_path))
        # return send_file(
        #     the_path, as_attachment=True, mimetype=mimetype[file_format],
        # )

    return Response(
        stream_with_context(check_api_deletions(cdf_set)),
        mimetype="text/event-stream",
    )


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


def write_csv(dataframe_set, output):
    zip_name = f"{output}.zip"
    zip_path = Path(safe_join(BASE_DIR, zip_name)).resolve()

    with ZipFile(zip_path, "w") as myzip, TemporaryDirectory() as tempdir:
        for result in dataframe_set:
            file_name = f"{output}_{result.chameleon_mode}.csv"
            temp_path = Path(tempdir) / file_name
            with temp_path.open("w") as output_file:
                result.to_csv(output_file, sep="\t", index=True)
            myzip.write(temp_path, arcname=file_name)

    return zip_name


def write_excel(dataframe_set, output):
    file_name = f"{output}.xlsx"
    file_path = Path(safe_join(BASE_DIR, file_name)).resolve()

    dataframe_set.write_excel(file_path)

    return file_name


def write_geojson(dataframe_set, output):
    timeout = 120
    try:
        response = dataframe_set.to_geojson(timeout=timeout)
    except TimeoutError:
        # TODO Inform user about error
        return

    file_name = f"{output}.geojson"
    file_path = Path(safe_join(BASE_DIR, file_name)).resolve()

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


class Message:
    def __init__(self, message_type: str, value: int):
        self.type = message_type
        self.value = value

    def __str__(self):
        return f"event: {self.type}\ndata: {self.value}\n\n"
