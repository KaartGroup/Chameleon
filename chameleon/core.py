from pathlib import Path
from typing import Union

import pandas as pd
import requests
from lxml import etree


class ChameleonDataFrame(pd.DataFrame):
    JOSM_URL = "http://localhost:8111/load_object?new_layer=true&objects="
    OSMCHA_URL = "https://osmcha.mapbox.com/changesets/"

    def __init__(self, df: pd.DataFrame, dtype=None):
        # dtypes = {
        #     # '@id': int,
        #     # '@version': int
        #     '@timestamp': datetime
        # }
        super().__init__(data=df, index=None, dtype=dtype, copy=False)

    def query_df(self, mode: str, grouping: bool = False):
        if mode in self.modes:
            intermediate_df = self.loc[(self[f"{mode}_old"].fillna(
                '') != self[f"{mode}_new"].fillna(''))]
        else:
            # New and deleted frames
            intermediate_df = self
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
        if mode != 'name':
            self['name'] = intermediate_df['name_new'].fillna(
                intermediate_df['name_old'].fillna(''))
        if mode != 'highway':
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
        if mode in self.modes:  # Skips the new and deleted DFs
            self[f"old_{mode}"] = intermediate_df[f"{mode}_old"]
            self[f"new_{mode}"] = intermediate_df[f"{mode}_new"]
        self['action'] = intermediate_df['action']
        self['notes'] = ''

        def group_df(self, mode: str):
            self['count'] = self['id']
            agg_functions = {
                'id': lambda id: self.JOSM_URL + ','.join(id),
                'count': 'count',
                'user': lambda user: ','.join(user.unique()),
                'timestamp': 'max',
                'version': 'max',
                'changeset': lambda changeset: ','.join(changeset.unique()),
            }
            if mode != 'name':
                agg_functions.update({
                    'name': lambda name: ','.join(str(id) for id in name.unique())
                })
            if mode != 'highway':
                agg_functions.update({
                    'highway': lambda highway: ','.join(str(id) for id in highway.unique())
                })
            # Create the new dataframe
            self = self.groupby(
                [f"old_{mode}", f"new_{mode}", 'action'], as_index=False).aggregate(agg_functions)
            # Get the grouped columns out of the index to be more visible
            self.reset_index(inplace=True)
            # Send those columns to the end of the frame
            new_column_order = (list(agg_functions.keys()) +
                                [f'old_{mode}', f'new_{mode}', 'action'])
            self = self[new_column_order]
            self.rename(columns={
                'id': 'url',
                'user': 'users',
                'timestamp': 'latest_timestamp',
                'changeset': 'changesets'
            }, inplace=True)
            # Add a blank notes column
            self['notes'] = ''


class ChameleonDataFrameSet:
    def __init__(self, oldfile: Union[str, Path], newfile: Union[str, Path]):
        self.merge_files(oldfile, newfile)
        self.dataframes = {}

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

    def to_csv(self, prefix: Path):
        pass
