from pathlib import Path
from typing import Union
from shapely.geometry.base import BaseGeometry
import geopandas as gpd
import pandas as pd


class TuflowParser:

    def __init__(self, file: Union[str, Path]) -> None:

        self._folder = Path(file).parents[0]

        self._contents_dict = {}

        with open(file) as f:

            for line in f:

                line = line.partition("!")[0]

                if line.isspace() or not line:
                    continue

                k, v = line.split("==")

                k = k.strip()
                v = v.strip()

                if k not in self._contents_dict:
                    self._contents_dict[k] = [v]
                else:
                    self._contents_dict[k].append(v)

    def _resolve_path(self, relative_path: Path) -> Path:
        return Path.joinpath(self._folder, relative_path).resolve()

    def _concat_geodataframe_tuple(self, gdb_paths: tuple, case_insensitive: bool) -> gpd.GeoDataFrame:
        gpd_tuple = (gpd.read_file(self._resolve_path(x)) for x in gdb_paths)
        if case_insensitive:
            gpd_tuple = (x.rename(columns=str.lower) for x in gpd_tuple)
        gpd_concat = gpd.GeoDataFrame(pd.concat(gpd_tuple, ignore_index=True))
        return gpd_concat

    def get_value(self, val_name: str, val_type: type = str, index: int = -1) -> object:
        return val_type(self._contents_dict[val_name][index])

    def get_list(self, val_name: str, sep: str, val_type: type = str, index: int = -1) -> list:
        return [val_type(x.strip()) for x in self._contents_dict[val_name][index].split(sep)]

    def get_tuple(self, val_name: str, sep: str, val_type: type = str, index: int = -1) -> tuple:
        return tuple(self.get_list(val_name, sep, val_type, index))

    def get_path(self, val_name: str, index: int = -1) -> Path:
        return self._resolve_path(self._contents_dict[val_name][index])

    def get_geodataframe(self, val_name: str, index: int = -1) -> gpd.GeoDataFrame:
        return gpd.read_file(self.get_path(val_name, index))

    def get_single_geometry(self, val_name: str, shp_index: int = 0, list_index: int = -1) -> BaseGeometry:
        return self.get_geodataframe(val_name, list_index).geometry[shp_index]

    def get_geodataframe_tuple(self, val_name: str, index: int = -1, case_insensitive: bool = False) -> gpd.GeoDataFrame:
        return self._concat_geodataframe_tuple(self.get_tuple(val_name, "|", index=index), case_insensitive)

    def get_all_geodataframes(self, val_name: str, case_insensitive: bool = False) -> gpd.GeoDataFrame:
        gpd_path_list_len = len(self._contents_dict[val_name])
        gpd_list = [
            self._concat_geodataframe_tuple(
                self.get_tuple(val_name, "|", index=i), case_insensitive
            ) for i in range(gpd_path_list_len)
        ]
        gpd_concat = gpd.GeoDataFrame(pd.concat(gpd_list, ignore_index=True))
        return gpd_concat

    def check_names(self, val_name_list: list) -> bool:
        for x in val_name_list:
            if x not in self._contents_dict.keys():
                return False
        return True