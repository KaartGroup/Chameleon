from datetime import datetime

import pandas as pd
from flask import Flask, request

from chameleon import core

app = Flask(__name__)

error_list = []

write_output = {
    "csv": write_csv,
    "excel": write_excel,
    "geojson": write_geojson,
}


@app.route("/upload", methods=["POST"])
def run():
    # country: str = request.form["country"]
    # startdate: datetime = request.form["startdate"]
    # enddate: datetime = request.form["enddate"]
    oldfile = request.files["old"]
    newfile = request.files["new"]
    output: str = request.form["output"]
    grouping: bool = request.form["grouping"]
    modes = set(request.form["modes"])

    cdf_set = core.ChameleonDataFrameSet(oldfile, newfile)

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

        write_output[format](cdf_set)


# def high_deletions_checker():


def write_csv():
    pass


def write_excel():
    pass


def write_geojson():
    pass
