from __future__ import annotations

from collections import UserDict
from pathlib import Path
from typing import Union

import pandas as pd


class ChameleonDataFrame(pd.DataFrame):
    SPECIAL_MODES = {'new', 'deleted'}
    JOSM_URL = "http://localhost:8111/load_object?new_layer=true&objects="
    OSMCHA_URL = "https://osmcha.mapbox.com/changesets/"

    def __init__(self, df: pd.DataFrame, mode: str, grouping=False, dtype=None):
        # dtypes = {
        #     # '@id': int,
        #     # '@version': int
        #     '@timestamp': datetime
        # }
        # Initialize as an "empty" dataframe, with the source data in an attribute
        super().__init__(data=None, index=None, dtype=dtype, copy=False)
        self.source_data = df
        self.mode = mode
        self.grouping = grouping

    def query(self) -> ChameleonDataFrame:
        if self.mode not in self.SPECIAL_MODES:
            intermediate_df = self.source_data.loc[(self.source_data[f"{self.mode}_old"].fillna(
                '') != self.source_data[f"{self.mode}_new"].fillna(''))]
        else:
            # New and deleted frames
            intermediate_df = self.source_data
        # Free up memory
        self.source_data = None
        self['id'] = (intermediate_df['type_old'].fillna(intermediate_df['type_new']).str[0] +
                      intermediate_df.index.astype(str))
        # if not self.group_output:
        self['url'] = (self.JOSM_URL + self['id'])
        self['user'] = intermediate_df['user_new'].fillna(
            intermediate_df['user_old'])
        self['timestamp'] = pd.to_datetime(intermediate_df['timestamp_new'].fillna(
            intermediate_df['timestamp_old'])).dt.strftime('%Y-%m-%d')
        self['version'] = intermediate_df['version_new'].fillna(
            intermediate_df['version_old'])
        try:
            # Succeeds if both csvs had changeset columns
            self['changeset'] = intermediate_df['changeset_new']
            self['osmcha'] = (
                self.OSMCHA_URL + self['changeset'])
        except KeyError:
            try:
                # Succeeds if one csv had a changeset column
                self['changeset'] = intermediate_df['changeset']
                self['osmcha'] = (
                    self.OSMCHA_URL + self['changeset'])
            except KeyError:
                # If neither had one, we just won't include in the output
                pass
        if self.mode != 'name':
            self['name'] = intermediate_df['name_new'].fillna(
                intermediate_df['name_old'].fillna(''))
        if self.mode != 'highway':
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
        if self.mode not in self.SPECIAL_MODES:  # Skips the new and deleted DFs
            self[f"old_{self.mode}"] = intermediate_df[f"{self.mode}_old"]
            self[f"new_{self.mode}"] = intermediate_df[f"{self.mode}_new"]
        self['action'] = intermediate_df['action']
        self['notes'] = ''
        if self.grouping:
            self.group()
        return self

        def group(self):
            self['count'] = self['id']
            agg_functions = {
                'id': lambda id: self.JOSM_URL + ','.join(id),
                'count': 'count',
                'user': lambda user: ','.join(user.unique()),
                'timestamp': 'max',
                'version': 'max',
                'changeset': lambda changeset: ','.join(changeset.unique()),
            }
            if self.mode != 'name':
                agg_functions.update({
                    'name': lambda name: ','.join(str(id) for id in name.unique())
                })
            if self.mode != 'highway':
                agg_functions.update({
                    'highway': lambda highway: ','.join(str(id) for id in highway.unique())
                })
            # Create the new dataframe
            self = self.groupby(
                [f"old_{self.mode}", f"new_{self.mode}", 'action'],
                as_index=False).aggregate(agg_functions)
            # Get the grouped columns out of the index to be more visible
            self.reset_index(inplace=True)
            # Send those columns to the end of the frame
            new_column_order = (list(agg_functions.keys()) +
                                [f'old_{self.mode}', f'new_{self.mode}', 'action'])
            self = self[new_column_order]
            self.rename(columns={
                'id': 'url',
                'user': 'users',
                'timestamp': 'latest_timestamp',
                'changeset': 'changesets'
            }, inplace=True)
            # Add a blank notes column
            self['notes'] = ''

    def sort(self):
        if self.grouping:
            sortable_values = ['action', 'users', 'latest_timestamp']
        else:
            sortable_values = ['action', 'user', 'timestamp']
        try:
            self.sort_values(
                sortable_values, inplace=True)
        except KeyError:
            pass


class ChameleonDataFrameSet(UserDict):
    SPECIAL_MODES = {'new', 'deleted'}

    def __init__(self, oldfile: Union[str, Path], newfile: Union[str, Path], use_api=False):
        super().__init__(self)
        self.source_data = None
        self.merge_files(oldfile, newfile)
        if not use_api:
            self.separate_special_dfs()

    def merge_files(self, oldfile: Union[str, Path], newfile: Union[str, Path]):
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

    def separate_special_dfs(self):
        # Create special dataframes for creations and deletions
        special_dataframes = {'new': self.source_data[self.source_data['action'] == 'new'],
                              'deleted': self.source_data[self.source_data['action'] == 'deleted']}
        # Remove the new/deleted ways from the source_data
        self.source_data = self.source_data[~self.source_data['action'].isin(
            self.SPECIAL_MODES)]
        for mode, df in special_dataframes.items():
            self[mode] = ChameleonDataFrame(df, mode).query()
