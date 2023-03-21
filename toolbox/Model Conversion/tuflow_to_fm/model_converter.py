from floodmodeller_api import XML2D
from tuflow_parser import TuflowParser
from component_converter import DomainConverter2D

from pathlib import Path
from typing import Union
from shapely.geometry.base import BaseGeometry

import geopandas as gpd


def _get_first_geometry(shp_path: Union[str, Path]) -> BaseGeometry:
    return gpd.read_file(shp_path).geometry[0]


class ModelConverter:
    def __init__(self) -> None:
        self._component_converters = {}

    def convert(self):
        for k, v in self._component_converters.items():
            print(f"Converting {k}...")
            v.convert()


class ModelConverter2D(ModelConverter):
    def __init__(self, xml_path: Union[str, Path]) -> None:
        super().__init__()
        self._xml = XML2D()
        self._xml.save(xml_path)


class TuflowModelConverter2D(ModelConverter2D):

    TCF_FILE_NAMES = {
        "tgc": "Geometry Control File",
        "tbc": "BC Control File",
        "ecf": "ESTRY Control File",
    }

    def __init__(self, tcf_path: Union[str, Path], xml_path: Union[str, Path]) -> None:
        super().__init__(xml_path)

        self._tcf = TuflowParser(tcf_path)

        for k, v in self.TCF_FILE_NAMES.items():
            path = self._tcf.get_full_path(v)
            setattr(self, f"_{k}", TuflowParser(path))

        self._init_domain()

    def _init_domain(self):
        domain_name = "Domain 1"
        loc_line_path = self._tgc.get_full_path("Read GIS Location")
        loc_line = _get_first_geometry(loc_line_path)
        dx = float(self._tgc.get_raw_value("Cell Size"))
        nx = int(self._tgc.get_raw_value("Grid Size (X,Y)").split(",")[0])
        ny = int(self._tgc.get_raw_value("Grid Size (X,Y)").split(",")[1])

        self._component_converters["domain"] = DomainConverter2D.from_loc_line(
            xml=self._xml,
            domain_name=domain_name,
            loc_line=loc_line,
            dx=dx,
            nx=nx,
            ny=ny,
        )
