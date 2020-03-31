"""
UI-independent classes for processing data
"""
from __future__ import annotations

import json
import logging
from collections import UserDict
from pathlib import Path
from typing import Union

import pandas as pd
import requests

logger = logging.getLogger(__name__)

SPECIAL_MODES = {'new', 'deleted'}
JOSM_URL = "http://localhost:8111/load_object?new_layer=true&objects="
OSMCHA_URL = "https://osmcha.mapbox.com/changesets/"


class ChameleonDataFrame(pd.DataFrame):
    """
    Dataframe with some relevant attributes and preset queries as methods
    """
    # pandas will maintain these instance attributes across manipulations
    _metadata = ['chameleon_mode', 'grouping']

    def __init__(self, df: pd.DataFrame = None, mode: str = '', grouping=False, dtype=None):
        # dtypes = {
        #     '@id': int,
        #     '@version': int
        #     '@timestamp': datetime
        # }

        self.chameleon_mode = mode
        self.grouping = grouping
        # Initialize as an "empty" dataframe, with the source data in an attribute
        super().__init__(data=df, index=None, dtype=dtype, copy=False)

    @property
    def _constructor(self):
        """
        Required for subclassing pandas classes,
        otherwise manipulation will return vanilla pandas classes
        instead of our subclass
        """
        return ChameleonDataFrame

    def query_cdf(self) -> ChameleonDataFrame:
        """
        Takes a dataframe that has already been merged from two input files and queries it
        for changes in the given tag
        """
        if self.chameleon_mode not in SPECIAL_MODES:
            intermediate_df = self.loc[(
                self[f"{self.chameleon_mode}_old"].fillna('') !=
                self[f"{self.chameleon_mode}_new"].fillna('')
            )]
        else:
            # New and deleted frames
            intermediate_df = self
        # self = ChameleonDataFrame(
        #     mode=self.chameleon_mode, grouping=self.grouping)

        self['id'] = (
            intermediate_df['type_old'].fillna(intermediate_df['type_new']).str[0] +
            intermediate_df.index.astype(str)
        )
        self['url'] = (JOSM_URL + self['id'])
        self['user'] = intermediate_df['user_new'].fillna(
            intermediate_df['user_old'])
        self['timestamp'] = pd.to_datetime(
            intermediate_df['timestamp_new'].fillna(
                intermediate_df['timestamp_old'])).dt.strftime('%Y-%m-%d')
        self['version'] = intermediate_df['version_new'].fillna(
            intermediate_df['version_old'])

        # Drop all but these columns
        self = self[['id', 'url', 'user', 'timestamp', 'version']]
        try:
            # Succeeds if both csvs had changeset columns
            self['changeset'] = intermediate_df['changeset_new']
            self['osmcha'] = (
                OSMCHA_URL + self['changeset'])
        except KeyError:
            try:
                # Succeeds if one csv had a changeset column
                self['changeset'] = intermediate_df['changeset']
                self['osmcha'] = (
                    OSMCHA_URL + self['changeset'])
            except KeyError:
                # If neither had one, we just won't include in the output
                pass
        if self.chameleon_mode != 'name':
            self['name'] = intermediate_df['name_new'].fillna(
                intermediate_df['name_old'])
        if self.chameleon_mode != 'highway':
            try:
                # Succeeds if both csvs had highway columns
                self['highway'] = intermediate_df['highway_new'].fillna(
                    intermediate_df['highway_old'])
            except KeyError:
                try:
                    # Succeeds if one csv had a highway column
                    self['highway'] = intermediate_df['highway']
                except KeyError:
                    # If neither had one, we just won't include in the output
                    pass

        # Renaming columns to be consistent with old Chameleon outputs
        if self.chameleon_mode not in SPECIAL_MODES:  # Skips the new and deleted DFs
            self[f"old_{self.chameleon_mode}"] = intermediate_df[f"{self.chameleon_mode}_old"]
            self[f"new_{self.chameleon_mode}"] = intermediate_df[f"{self.chameleon_mode}_new"]

        self['action'] = intermediate_df['action']
        self['notes'] = self['QCer'] = self['QC_notes'] = self['resolution'] = ''
        if self.grouping:
            self = self.group()
        self.dropna(subset=['id'], inplace=True)
        self.fillna('', inplace=True)
        self.sort()
        return self

    def group(self) -> ChameleonDataFrame:
        """
        Groups changes by type of change. (Each combination of old_value, new_value, and action)
        """
        self['count'] = self['id']
        agg_functions = {
            'id': lambda i: JOSM_URL + ','.join(i),
            'count': 'count',
            'user': lambda user: ','.join(user.unique()),
            'timestamp': 'max',
            'version': 'max',
            'changeset': lambda changeset: ','.join(changeset.unique()),
        }
        if self.chameleon_mode != 'name':
            agg_functions.update({
                'name': lambda name: ','.join(str(i) for i in name.unique())
            })
        if self.chameleon_mode != 'highway':
            agg_functions.update({
                'highway': lambda highway: ','.join(str(i) for i in highway.unique())
            })
        # Create the new dataframe
        grouped_df = self.groupby(
            [f"old_{self.chameleon_mode}",
             f"new_{self.chameleon_mode}",
             'action'],
            as_index=False).aggregate(agg_functions)
        # Get the grouped columns out of the index to be more visible
        grouped_df.reset_index(inplace=True)
        # Send those columns to the end of the frame
        new_column_order = (list(agg_functions.keys()) +
                            [f'old_{self.chameleon_mode}',
                             f'new_{self.chameleon_mode}',
                             'action'])
        grouped_df = grouped_df[new_column_order]
        grouped_df.rename(columns={
            'id': 'url',
            'user': 'users',
            'timestamp': 'latest_timestamp',
            'changeset': 'changesets'
        }, inplace=True)
        # Add a blank notes column
        grouped_df['notes'] = ''
        # TODO Once github.com/pandas-dev/pandas/issues/28330 is fixed, change to grouping in place
        self = ChameleonDataFrame(
            df=grouped_df, mode=self.chameleon_mode, grouping=self.grouping)
        return self

    def sort(self) -> ChameleonDataFrame:
        if self.grouping:
            sortable_values = ['action', 'users', 'latest_timestamp']
        else:
            sortable_values = ['action', 'user', 'timestamp']
        try:
            self.sort_values(
                sortable_values, inplace=True)
        except KeyError:
            pass
        return self


class ChameleonDataFrameSet(UserDict):
    # TODO Change this from dict to set, and use each df's .chameleon_mode property in lieu of the dict key
    """
    Specialized dict that holds all dataframes in a run until they are written
    """

    def __init__(self, oldfile: Union[str, Path], newfile: Union[str, Path], use_api=False):
        super().__init__(self)
        self.source_data = None
        self.oldfile = Path(oldfile)
        self.newfile = Path(newfile)
        self.deleted_way_members = {}
        self.overpass_result_attribs = {}

        self.merge_files()

    def merge_files(self) -> ChameleonDataFrameSet:
        """
        Merge two csv inputs into a single combined dataframe
        """
        # dtypes = {
        #     # '@id': int,
        #     # '@version': int
        #     '@timestamp': datetime
        # }
        old_df = pd.read_csv(self.oldfile, sep='\t',
                             index_col='@id', dtype=str)
        new_df = pd.read_csv(self.newfile, sep='\t',
                             index_col='@id', dtype=str)
        # Cast a couple items to more specific types
        # for col, col_type in dtypes.items():
        # old_df[col] = old_df[col].astype(col_type)
        # new_df[col] = new_df[col].astype(col_type)
        # Used to indicate which sheet(s) each row came from post-join
        old_df['present'] = new_df['present'] = True

        self.source_data = old_df.join(new_df, how='outer',
                                       lsuffix='_old', rsuffix='_new')
        self.source_data['present_old'].fillna(False, inplace=True)
        self.source_data['present_new'].fillna(False, inplace=True)

        # Eliminate special chars that mess pandas up
        self.source_data.columns = self.source_data.columns.str.replace(
            '@', '')
        self.source_data.columns = self.source_data.columns.str.replace(
            ':', '_')
        # Strip whitespace
        self.source_data.columns = self.source_data.columns.str.strip()

        try:
            self.source_data.loc[self.source_data.present_old &
                                 self.source_data.present_new, 'action'] = 'modified'
            self.source_data.loc[self.source_data.present_old & ~
                                 self.source_data.present_new, 'action'] = 'deleted'
            self.source_data.loc[~self.source_data.present_old &
                                 self.source_data.present_new, 'action'] = 'new'
        except ValueError:
            # No change for this mode, add a placeholder column
            self.source_data['action'] = ''
        return self

    def separate_special_dfs(self) -> ChameleonDataFrameSet:
        """
        Separate creations and deletions into their own dataframes
        """
        special_dataframes = {
            'new': self.source_data[self.source_data['action'] == 'new'],
            'deleted': self.source_data[self.source_data['action'] == 'deleted']
        }
        # Remove the new/deleted ways from the source_data
        self.source_data = self.source_data[
            ~ self.source_data['action'].isin(SPECIAL_MODES)
        ]
        for mode, df in special_dataframes.items():
            self[mode] = ChameleonDataFrame(df=df, mode=mode).query_cdf()
        return self

    def check_feature_on_api(self, feature_id, app_version: str = '') -> dict:
        """
        Checks whether a way was deleted on the server
        """
        if app_version:
            app_version = f" {app_version}".rstrip()

        # TODO Change from XML to JSON
        if feature_id in self.overpass_result_attribs:
            return self.overpass_result_attribs[feature_id]
        else:
            try:
                response = requests.get(
                    f'https://www.openstreetmap.org/api/0.6/way/{feature_id}/history.json',
                    timeout=2,
                    headers={'user-agent': f'Kaart Chameleon{app_version}'})
                # Raises exceptions for non-successful status codes
                response.raise_for_status()
            except ConnectionError as e:
                # Couldn't contact the server, could be client-side
                logger.exception(e)
                return
            except response.HTTPError:
                if str(response.status_code) == '429':
                    retry_after = response.headers.get('retry-after', '')
                    logger.error(
                        "The OSM server says you've made too many requests."
                        "You can retry after %s seconds.", retry_after)
                    raise RuntimeError
                else:
                    logger.error(
                        'Server replied with a %s error', response.status_code)
                return
            else:
                loaded_response = json.loads(response.text)
                # TODO Generalize for nodes and relations
                latest_version = loaded_response['elements'][-1]
                element_attribs = {
                    'user_new': latest_version['user'],
                    'changeset_new': str(latest_version['changeset']),
                    'version_new': str(latest_version['version']),
                    'timestamp_new': latest_version['timestamp']
                }

                if not latest_version.get('visible', True):
                    # The most recent way version has the way deleted
                    prior_version_num = int(latest_version['version']) - 1
                    prior_version = [i for i in loaded_response['elements']
                                     if int(i['version']) == prior_version_num][0]

                    # Save last members of the deleted way
                    # for later use in detecting splits/merges
                    self.deleted_way_members[feature_id] = prior_version['nodes']
                else:
                    # The way was not deleted, just dropped from the latter dataset
                    element_attribs.update({
                        'action': 'dropped'
                    })
                return element_attribs