"""
UI-independent classes for processing data
"""
from __future__ import annotations

from collections import UserDict
from pathlib import Path
from typing import Union

import pandas as pd

SPECIAL_MODES = {'new', 'deleted'}
JOSM_URL = "http://localhost:8111/load_object?new_layer=true&objects="
OSMCHA_URL = "https://osmcha.mapbox.com/changesets/"


class ChameleonDataFrame(pd.DataFrame):
    """
    Dataframe with some relevant attributes and preset queries as methods
    """
    # pandas will maintain these instance attributes across manipulations
    _metadata = ['chameleon_mode', 'grouping']

    def __init__(self, df: pd.DataFrame = None, mode: str = None, grouping=False, dtype=None):
        # dtypes = {
        #     # '@id': int,
        #     # '@version': int
        #     '@timestamp': datetime
        # }
        # Initialize as an "empty" dataframe, with the source data in an attribute
        self.chameleon_mode = mode
        self.grouping = grouping
        super().__init__(data=df, index=None, dtype=dtype, copy=False)

    # Required for subclassing pandas classes, otherwise manipulation return vanilla pandas
    # classes instead of our subclass
    @property
    def _constructor(self):
        return ChameleonDataFrame

    def query(self) -> ChameleonDataFrame:
        """
        Takes a dataframe that has already been merged from two input files and queries it
        for changes in the given tag
        """
        if self.chameleon_mode not in SPECIAL_MODES:
            intermediate_df = self.loc[(self[f"{self.chameleon_mode}_old"].fillna(
                '') != self[f"{self.chameleon_mode}_new"].fillna(''))]
        else:
            # New and deleted frames
            intermediate_df = self
        # self = ChameleonDataFrame(
        #     mode=self.chameleon_mode, grouping=self.grouping)
        self['id'] = (intermediate_df['type_old'].fillna(intermediate_df['type_new']).str[0] +
                      intermediate_df.index.astype(str))
        self['url'] = (JOSM_URL + self['id'])
        self['user'] = intermediate_df['user_new'].fillna(
            intermediate_df['user_old'])
        self['timestamp'] = pd.to_datetime(intermediate_df['timestamp_new'].fillna(
            intermediate_df['timestamp_old'])).dt.strftime('%Y-%m-%d')
        self['version'] = intermediate_df['version_new'].fillna(
            intermediate_df['version_old'])
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
                intermediate_df['name_old'].fillna(''))
        if self.chameleon_mode != 'highway':
            try:
                # Succeeds if both csvs had highway columns
                self['highway'] = intermediate_df['highway_new'].fillna(
                    intermediate_df['highway_old'].fillna(''))
            except KeyError:
                try:
                    # Succeeds if one csv had a highway column
                    self['highway'] = intermediate_df['highway'].fillna(
                        '')
                except KeyError:
                    # If neither had one, we just won't include in the output
                    pass
        if self.chameleon_mode not in SPECIAL_MODES:  # Skips the new and deleted DFs
            self[f"old_{self.chameleon_mode}"] = intermediate_df[f"{self.chameleon_mode}_old"]
            self[f"new_{self.chameleon_mode}"] = intermediate_df[f"{self.chameleon_mode}_new"]
        self['action'] = intermediate_df['action']
        self['notes'] = ''
        if self.grouping:
            self = self.group()
        self.sort()
        return self

    def group(self) -> ChameleonDataFrame:
        """
        Groups changes by type of change. (Each combination of old_value, new_value, and action)
        """
        self['count'] = self['id']
        agg_functions = {
            'id': lambda id: JOSM_URL + ','.join(id),
            'count': 'count',
            'user': lambda user: ','.join(user.unique()),
            'timestamp': 'max',
            'version': 'max',
            'changeset': lambda changeset: ','.join(changeset.unique()),
        }
        if self.chameleon_mode != 'name':
            agg_functions.update({
                'name': lambda name: ','.join(str(id) for id in name.unique())
            })
        if self.chameleon_mode != 'highway':
            agg_functions.update({
                'highway': lambda highway: ','.join(str(id) for id in highway.unique())
            })
        # Create the new dataframe
        grouped_df = self.groupby(
            [f"old_{self.chameleon_mode}",
                f"new_{self.chameleon_mode}", 'action'],
            as_index=False).aggregate(agg_functions)
        # Get the grouped columns out of the index to be more visible
        grouped_df.reset_index(inplace=True)
        # Send those columns to the end of the frame
        new_column_order = (list(agg_functions.keys()) +
                            [f'old_{self.chameleon_mode}', f'new_{self.chameleon_mode}', 'action'])
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
    """
    Specialized dict that holds all dataframes in a run until they are written
    """

    def __init__(self, oldfile: Union[str, Path], newfile: Union[str, Path], use_api=False):
        super().__init__(self)
        self.source_data = None
        self.merge_files(oldfile, newfile)
        if not use_api:
            self.separate_special_dfs()

    def merge_files(self,
                    oldfile: Union[str, Path], newfile: Union[str, Path]) -> ChameleonDataFrame:
        """
        Merge two csv inputs into a single combined dataframe
        """
        # dtypes = {
        #     # '@id': int,
        #     # '@version': int
        #     '@timestamp': datetime
        # }
        old_df = pd.read_csv(oldfile, sep='\t',
                             index_col='@id', dtype=str)
        new_df = pd.read_csv(newfile, sep='\t',
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

    def separate_special_dfs(self) -> ChameleonDataFrame:
        """
        Separate creations and deletions into their own dataframes
        """
        special_dataframes = {'new': self.source_data[self.source_data['action'] == 'new'],
                              'deleted': self.source_data[self.source_data['action'] == 'deleted']}
        # Remove the new/deleted ways from the source_data
        self.source_data = self.source_data[~self.source_data['action'].isin(
            SPECIAL_MODES)]
        for mode, df in special_dataframes.items():
            self[mode] = ChameleonDataFrame(df=df, mode=mode).query()
        return self
