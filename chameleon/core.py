"""
UI-independent classes for processing data
"""
from __future__ import annotations

import itertools
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Generator, List, Mapping, Set, TextIO, Tuple, Union

import appdirs
import geojson
import numpy as np
import overpass
import pandas as pd
import requests_cache
import yaml
from more_itertools import chunked as pager
from requests_cache.backends import sqlite

pd.options.mode.chained_assignment = None

logger = logging.getLogger(__name__)

SPECIAL_MODES = {"new", "deleted"}
TYPE_EXPANSION = {"n": "node", "w": "way", "r": "relation"}
GEOJSON_OSM = {"Point": "node", "LineString": "way", "Polygon": "way"}
JOSM_URL = "http://localhost:8111/load_object?new_layer=true&objects="
OSMCHA_URL = "https://osmcha.mapbox.com/changesets/"
OVERPASS_TIMEOUT = (
    180  # Locked until GH mvexel/overpass-api-python-wrapper#112 is fixed
)
CACHE_LOCATION = Path(appdirs.user_cache_dir("Chameleon", "Kaart"))
HIGH_DELETIONS_THRESHOLD = 5


class ChameleonDataFrame(pd.DataFrame):
    """
    Dataframe with some relevant attributes and preset queries as methods
    """

    # pandas will maintain these instance attributes across manipulations
    _metadata = ["chameleon_mode", "grouping"]

    def __init__(
        self,
        df: pd.DataFrame = None,
        mode: str = "",
        grouping=False,
        dtype=None,
        config: Mapping = None,
    ):
        # dtypes = {
        #     '@id': int,
        #     '@version': int
        #     '@timestamp': datetime
        # }

        self.chameleon_mode = mode
        self.grouping = grouping
        self.config = config or {}
        # Initialize as an "empty" dataframe,
        # with the source data in an attribute
        super().__init__(data=df, index=None, dtype=dtype, copy=False)

    @property
    def _constructor(self):
        """
        Required for subclassing pandas classes,
        otherwise manipulation will return vanilla pandas classes
        instead of our subclass
        """
        return ChameleonDataFrame

    def __hash__(self):
        return hash(self.chameleon_mode)

    @property
    def chameleon_mode_cleaned(self) -> str:
        """
        Removes special characters from column and file names
        """
        return self.chameleon_mode.replace("@", "").replace(":", "_")

    def query_cdf(self) -> ChameleonDataFrame:
        """
        Takes a dataframe that has already been merged from two input files
        and queries it for changes in the given tag
        """
        intermediate_df = (
            self.loc[
                (
                    self[f"{self.chameleon_mode_cleaned}_old"].fillna("")
                    != self[f"{self.chameleon_mode_cleaned}_new"].fillna("")
                )
            ]
            if self.chameleon_mode not in SPECIAL_MODES
            else self
        )
        # self = ChameleonDataFrame(
        #     mode=self.chameleon_mode, grouping=self.grouping)

        self["url"] = JOSM_URL + self.index
        self["user"] = intermediate_df["user_new"].fillna(
            intermediate_df["user_old"]
        )
        self["timestamp"] = pd.to_datetime(
            intermediate_df["timestamp_new"].fillna(
                intermediate_df["timestamp_old"]
            )
        ).dt.strftime("%Y-%m-%d")
        self["version"] = intermediate_df["version_new"].fillna(
            intermediate_df["version_old"]
        )

        # Drop all but these columns
        self = self[["url", "user", "timestamp", "version"]]
        try:
            # Succeeds if both csvs had changeset columns
            self["changeset"] = intermediate_df["changeset_new"]
            self["osmcha"] = OSMCHA_URL + self["changeset"]
        except KeyError:
            try:
                # Succeeds if one csv had a changeset column
                self["changeset"] = intermediate_df["changeset"]
                self["osmcha"] = OSMCHA_URL + self["changeset"]
            except KeyError:
                # If neither had one, we just won't include in the output
                pass
        if self.chameleon_mode != "name":
            try:
                self["name"] = intermediate_df["name_new"].fillna(
                    intermediate_df["name_old"]
                )
            except KeyError:
                try:
                    # Succeeds if one csv had a name column
                    self["name"] = intermediate_df["name"]
                except KeyError:
                    pass
        if self.chameleon_mode != "highway":
            try:
                # Succeeds if both csvs had highway columns
                self["highway"] = intermediate_df["highway_new"].fillna(
                    intermediate_df["highway_old"]
                )
            except KeyError:
                try:
                    # Succeeds if one csv had a highway column
                    self["highway"] = intermediate_df["highway"]
                except KeyError:
                    # If neither had one, we just won't include in the output
                    pass

        # Renaming columns to be consistent with old Chameleon outputs
        if (
            self.chameleon_mode not in SPECIAL_MODES
        ):  # Skips the new and deleted DFs
            self[f"old_{self.chameleon_mode_cleaned}"] = intermediate_df[
                f"{self.chameleon_mode_cleaned}_old"
            ]
            self[f"new_{self.chameleon_mode_cleaned}"] = intermediate_df[
                f"{self.chameleon_mode_cleaned}_new"
            ]

        self["action"] = intermediate_df["action"]
        if self.grouping:
            self = self.group()
        self.dropna(subset=["action"], inplace=True)
        self.fillna("", inplace=True)
        self.sort()
        return self

    def group(self) -> ChameleonDataFrame:
        """
        Groups changes by type of change.
        (Each combination of old_value, new_value, and action)
        """
        self["count"] = self["id"] = self.index
        agg_functions = {
            "id": lambda i: ",".join(i),
            "count": "count",
            "user": lambda user: ",".join(user.unique()),
            "timestamp": "max",
            "version": "max",
            "changeset": lambda changeset: ",".join(changeset.unique()),
        }
        if self.chameleon_mode != "name":
            agg_functions["name"] = lambda name: ",".join(
                str(i) for i in name.unique() if pd.notna(i)
            )
        if self.chameleon_mode != "highway":
            agg_functions["highway"] = lambda highway: ",".join(
                str(i) for i in highway.unique() if pd.notna(i)
            )
        # Create the new dataframe
        grouped_df = self.groupby(
            [
                f"old_{self.chameleon_mode_cleaned}",
                f"new_{self.chameleon_mode_cleaned}",
                "action",
            ],
            as_index=False,
        ).aggregate(agg_functions)

        # Get the grouped columns out of the index to be more visible
        grouped_df.reset_index(inplace=True)
        grouped_df.set_index("id", inplace=True)

        grouped_df["url"] = JOSM_URL + grouped_df.index

        # Send those columns to the end of the frame
        new_column_order = [
            "url",
            "count",
            "user",
            "timestamp",
            "version",
            "changeset",
        ]
        if self.chameleon_mode != "name":
            new_column_order += ["name"]
        if self.chameleon_mode != "highway":
            new_column_order += ["highway"]
        new_column_order += [
            f"old_{self.chameleon_mode_cleaned}",
            f"new_{self.chameleon_mode_cleaned}",
            "action",
        ]
        grouped_df = grouped_df[new_column_order]

        grouped_df.rename(
            columns={
                "user": "users",
                "timestamp": "latest_timestamp",
                "changeset": "changesets",
            },
            inplace=True,
        )
        # TODO Once GH pandas-dev/pandas#28330 is fixed, change to grouping in place
        self = ChameleonDataFrame(
            df=grouped_df, mode=self.chameleon_mode, grouping=self.grouping
        )
        return self

    def sort(self) -> ChameleonDataFrame:
        sortable_values = (
            ["action", "users", "latest_timestamp"]
            if self.grouping
            else ["action", "user", "timestamp"]
        )
        try:
            self.sort_values(sortable_values, inplace=True)
        except KeyError:
            pass
        return self

    def filter(self) -> ChameleonDataFrame:
        # Drop rows with Kaart users tagged
        if whitelist := self.config.get("user_whitelist", []):
            self = self[self["user"] not in whitelist]

        highway_vals = {
            "motorway": 1,
            "trunk": 2,
            "primary": 3,
            "secondary": 4,
            "tertiary": 5,
            "unclassified": 6,
            "residential": 6,
            "service": 6,
            "track": 6,
            "footway": 6,
            "path": 6,
            "steps": 6,
            "cycleway": 6,
        }
        self["highway_change_score"] = abs(
            self["old_highway"].map(highway_vals)
            - self["new_highway"].map(highway_vals)
        )

        if type_filter := self.config.get("type_filter"):
            self = self[
                self["old_highway"] in type_filter.get("always_include", [])
                or self["new_highway"] in type_filter.get("always_include", [])
                or self["highway_change_score"]
                >= type_filter.get("highway_step_change", 0)
            ]

        return self


class ChameleonDataFrameSet(set):
    """
    Specialized dict that holds all dataframes in a run until they are written
    """

    page_length = 2000

    def __init__(
        self,
        old: Union[str, Path, TextIO],
        new: Union[str, Path, TextIO],
        use_api=False,
        extra_columns=None,
        config: Union[Mapping, str, Path] = None,
    ):
        super().__init__(self)
        if extra_columns is None:
            extra_columns = {}
        self.oldfile = old
        self.newfile = new
        if isinstance(self.oldfile, str):
            self.oldfile = Path(self.oldfile)
        if isinstance(self.newfile, str):
            self.newfile = Path(self.newfile)

        self.extra_columns = extra_columns

        if isinstance(config, Mapping):
            self.config = config
        elif config:
            with open(config) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}

        self.source_data = None
        self.deleted_way_members = {}
        self.overpass_result_attribs = {}

        self.merge_files()

    def __getitem__(self, key) -> ChameleonDataFrame:
        return next(
            i
            for i in self
            if i.chameleon_mode == key or i.chameleon_mode_cleaned == key
        )

    @property
    def modes(self) -> Set[str]:
        return {i.chameleon_mode for i in self}

    @property
    def modes_cleaned(self) -> Set[str]:
        return {i.chameleon_mode_cleaned for i in self}

    def merge_files(self) -> ChameleonDataFrameSet:
        """
        Merge two csv inputs into a single combined dataframe
        """
        # dtypes = {
        #     # '@id': int,
        #     # '@version': int
        #     '@timestamp': datetime
        # }
        old_df = pd.read_csv(self.oldfile, sep="\t", index_col="@id", dtype=str)
        new_df = pd.read_csv(self.newfile, sep="\t", index_col="@id", dtype=str)
        # Cast a couple items to more specific types
        # for col, col_type in dtypes.items():
        # old_df[col] = old_df[col].astype(col_type)
        # new_df[col] = new_df[col].astype(col_type)
        # Used to indicate which sheet(s) each row came from post-join
        old_df["present"] = new_df["present"] = True

        self.source_data = old_df.join(
            new_df, how="outer", lsuffix="_old", rsuffix="_new"
        )
        self.source_data["present_old"].fillna(False, inplace=True)
        self.source_data["present_new"].fillna(False, inplace=True)

        # Eliminate special chars that mess pandas up
        self.source_data.columns = self.source_data.columns.str.replace("@", "")
        self.source_data.columns = self.source_data.columns.str.replace(":", "_")
        # Strip whitespace
        self.source_data.columns = self.source_data.columns.str.strip()

        self.source_data.index = self.source_data["type_old"].fillna(
            self.source_data["type_new"]
        ).str[0] + self.source_data.index.astype(str)
        self.source_data.index.rename("id", inplace=True)

        try:
            self.source_data.loc[
                self.source_data.present_old & self.source_data.present_new,
                "action",
            ] = "modified"
            self.source_data.loc[
                self.source_data.present_old & ~self.source_data.present_new,
                "action",
            ] = "deleted"
            self.source_data.loc[
                ~self.source_data.present_old & self.source_data.present_new,
                "action",
            ] = "new"
        except ValueError:
            # No change for this mode, add a placeholder column
            self.source_data["action"] = np.nan
        return self

    def separate_special_dfs(self) -> ChameleonDataFrameSet:
        """
        Separate creations and deletions into their own dataframes
        """
        special_dataframes = {
            "new": self.source_data[self.source_data["action"] == "new"],
            "deleted": self.source_data[self.source_data["action"] == "deleted"],
        }
        # Remove the new/deleted ways from the source_data
        self.source_data = self.source_data[
            ~self.source_data["action"].isin(SPECIAL_MODES)
        ]
        for mode, df in special_dataframes.items():
            i = ChameleonDataFrame(
                df=df, mode=mode, config=self.config
            ).query_cdf()
            self.add(i)
        return self

    def check_feature_on_api(
        self, feature_id: str, app_version: str = ""
    ) -> Tuple(dict, bool):
        """
        Checks whether a way was deleted on the server
        """
        expiry = timedelta(hours=12)
        session = requests_cache.CachedSession(
            backend=sqlite.DbCache(
                location=str(CACHE_LOCATION / "cache"),
                expire_after=expiry,
            )
        )

        if app_version:
            app_version = f" {app_version}".rstrip()

        if feature_id in self.overpass_result_attribs:
            return self.overpass_result_attribs[feature_id]
        feature_type, feature_id_num = split_id(feature_id)
        response = session.get(
            "https://www.openstreetmap.org/api/0.6/"
            f"{feature_type}/{feature_id_num}/history.json",
            timeout=5,
            headers={
                "User-Agent": f"Kaart Chameleon{app_version}",
                "From": "dev@kaart.com",
            },
        )
        # Raises exceptions for non-successful status codes
        response.raise_for_status()

        loaded_response = response.json()
        latest_version = loaded_response["elements"][-1]
        element_attribs = {
            "user_new": latest_version["user"],
            "changeset_new": str(latest_version["changeset"]),
            "version_new": str(latest_version["version"]),
            "timestamp_new": latest_version["timestamp"],
        }
        if not latest_version.get("visible", True):
            # The most recent way version has the way deleted
            prior_version_num = latest_version["version"] - 1
            try:
                prior_version = next(
                    i
                    for i in loaded_response["elements"]
                    if i["version"] == prior_version_num
                )
            except IndexError:
                # Prior version doesn't exist for some reason, possibly redaction
                pass
            else:
                # Save last members of the deleted way
                # for later use in detecting splits/merges
                if feature_type == "way":
                    self.deleted_way_members[feature_id] = prior_version["nodes"]
        else:
            # The way was not deleted, just dropped from the latter dataset
            element_attribs.update({"action": "dropped"})
        return (element_attribs, response.from_cache)

    def write_excel(self, file_name: Union[Path, str]):
        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            for result in self:
                # Points at first cell (blank) of last column written
                # Set before adding the other columns
                column_pointer = len(result.columns) + 1
                for k in self.extra_columns.keys():
                    result[k] = ""
                result.to_excel(
                    writer,
                    sheet_name=result.chameleon_mode_cleaned,
                    index=True,
                    freeze_panes=(1, 0),
                )

                if self.extra_columns:
                    sheet = writer.sheets[result.chameleon_mode_cleaned]

                    for count, (k, v) in enumerate(self.extra_columns.items()):
                        if v is not None and v.get("validate", None):
                            sheet.data_validation(
                                1,
                                column_pointer + count,
                                len(result),
                                column_pointer + count,
                                v,
                            )

    class OverpassQuery:
        """
        Manages and tracks the progress of Overpass query or queries
        """

        request_interval = 5  # Time to wait between queries

        def __init__(self, parent):
            self.parent = parent
            self.timeout = OVERPASS_TIMEOUT
            self.api = overpass.API(timeout=self.timeout)
            self.queries_completed = 0
            self._response_features = []

        def get(self) -> Generator[None, None, None]:
            sleeptime = 0
            for query in self.parent.overpass_query_pages:
                self.overpass_start_time = (
                    datetime.now().astimezone() + timedelta(seconds=sleeptime)
                )
                self.overpass_timeout_time = (
                    self.overpass_start_time + timedelta(seconds=self.timeout)
                )
                yield
                time.sleep(sleeptime)
                logger.info(
                    "Making query number %s of %s from Overpass.",
                    self.queries_completed + 1,
                    self.number_of_queries,
                )
                r = self.api.get(
                    query,
                    verbosity="meta geom",
                    responseformat="geojson",
                )
                logger.info("done")
                self.queries_completed += 1
                self._response_features += r["features"]
                sleeptime = self.request_interval

        @property
        def geojson(self) -> geojson.FeatureCollection:
            if not self.complete:
                raise RuntimeError
            response_by_id = {
                GEOJSON_OSM[i["geometry"]["type"]][0] + str(i["id"]): i
                for i in self._response_features
            }
            agg_functions = {
                "user": lambda user: ",".join(user.unique()),
                "timestamp": "max",
                "version": "max",
                "changeset": lambda changeset: ",".join(changeset.unique()),
                "name": lambda changeset: ",".join(changeset.unique()),
                "highway": lambda changeset: ",".join(changeset.unique()),
                "old_tag": lambda old_tag: ",".join(old_tag.unique()),
                "new_tag": lambda new_tag: ",".join(new_tag.unique()),
                "change_type": ",".join,
            }

            combined = pd.concat(self.with_mode_column)
            combined.fillna("", inplace=True)
            combined = combined.astype(str)
            combined.reset_index(inplace=True)
            combined = combined.groupby("id").aggregate(agg_functions)

            columns_to_keep = ["user", "timestamp", "version"]
            if "changeset" in combined.columns and "osmcha" in combined.columns:
                columns_to_keep += ["changeset", "osmcha"]
            columns_to_keep += [
                "name",
                "highway",
                "old_tag",
                "new_tag",
                "change_type",
            ]
            combined = combined[columns_to_keep]

            return geojson.FeatureCollection(
                [
                    geojson.Feature(
                        id=fid,
                        geometry=response_by_id.get(fid, {}).get("geometry"),
                        properties=dict(row),
                    )
                    for fid, row in combined.iterrows()
                    if response_by_id.get(fid)
                ]
            )

        @property
        def complete(self) -> bool:
            return self.queries_completed >= self.number_of_queries

        @property
        def number_of_queries(self) -> int:
            return len(self.parent.overpass_query_pages)

        @property
        def with_mode_column(self) -> Generator[ChameleonDataFrame, None, None]:
            # the_cdfs = set()
            for cdf in self.parent.nondeleted:
                cdf_copy = cdf.copy()
                cdf_copy.rename(
                    columns={
                        next(
                            (
                                name
                                for name in cdf.columns
                                if name.startswith("old_")
                            ),
                            "old",
                        ): "old_tag",
                        next(
                            (
                                name
                                for name in cdf.columns
                                if name.startswith("new_")
                            ),
                            "new",
                        ): "new_tag",
                    },
                    inplace=True,
                )
                cdf_copy["change_type"] = cdf.chameleon_mode
                yield cdf_copy

    @property
    def nondeleted(self) -> Set[ChameleonDataFrame]:
        return {i for i in self if i.chameleon_mode != "deleted"}

    @property
    def overpass_query_pages(self) -> List[str]:
        all_ids = sorted(
            set(itertools.chain(*(df.index for df in self.nondeleted)))
        )
        query_pages = []
        for page in pager(all_ids, self.page_length):
            feature_ids = separate_ids_by_feature_type(page)
            query_page = ";".join(
                f"{ftype}(id:{','.join(sorted(fid))})"
                for ftype, fid in feature_ids.items()
                if ftype != "relation" and fid
            )
            if query_page:
                # Relations will create empty query pages, skip those
                query_pages.append(query_page)
        return query_pages


def split_id(feature_id: Union[str, int]) -> Tuple[str, str]:
    """
    Separates an id like "n12345678" into the tuple ('node', '12345678')
    """
    feature_id = str(feature_id)
    typeregex = re.compile(r"\A[nwr]")
    idregex = re.compile(r"\d+\Z")

    typematch = typeregex.search(feature_id)
    ftype = TYPE_EXPANSION.get(typematch.group()) if typematch else None
    idmatch = idregex.search(feature_id).group()
    return ftype, idmatch


def separate_ids_by_feature_type(mixed: List[str]) -> Dict[str, List[str]]:
    """
    Separates a list of mixed type feature ids
    into a dict with types as keys and lists of ids as values

    Parameters
    ----------
    mixed:List[str]: a list of feature ids, of mixed feature types

    Returns
    -------
    Dict[str, List[str]]: a dict with keys 'nodes', 'ways', and 'relations'
    and lists of ids as values
    """
    f_type_id: List[Tuple[str, str]] = [split_id(i) for i in mixed]

    the_dict = {}
    for k, v in f_type_id:
        the_dict.setdefault(k, []).append(v)

    return the_dict


def clean_for_presentation(user_input: str) -> str:
    """
    Sanitizes user input so that they can still recognize what they entered
    """
    user_input = user_input.strip(" \"'")
    user_input = user_input.partition("=")[0]
    return user_input
