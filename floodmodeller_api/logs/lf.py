"""
Flood Modeller Python API
Copyright (C) 2022 Jacobs U.K. Limited

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details. 

You should have received a copy of the GNU General Public License along with this program.  If not, see https://www.gnu.org/licenses/.

If you have any query about this program or this License, please contact us at support@floodmodeller.com or write to the following 
address: Jacobs UK Limited, Flood Modeller, Cottons Centre, Cottons Lane, London, SE1 2QG, United Kingdom.
"""

from pathlib import Path
from typing import Optional, Union
from abc import abstractmethod

import pandas as pd

from .._base import FMFile
from .lf_params import lf1_unsteady_data_to_extract, lf1_steady_data_to_extract, lf2_data_to_extract
from .lf_helpers import TimeFloatMult


class LF(FMFile):
    def __init__(self, lf_filepath: Optional[Union[str, Path]]):
        try:
            self._filepath = lf_filepath
            FMFile.__init__(self)
            self._init_counters()
            self._init_params_and_progress()
            self._init_line_types()
            self._read()

        except Exception as e:
            self._handle_exception(e, when="read")

    def _read(self, force_reread: bool = False, suppress_final_steps: bool = False):
        # Read LF file
        with open(self._filepath, "r") as lf1_file:
            self._raw_data = [line.rstrip("\n") for line in lf1_file.readlines()]

        # Force rereading from start of file
        if force_reread == True:
            self._del_attributes()
            self._del_dataframe()
            self._init_counters()
            self._init_line_types()

        # Process file
        self._update_line_types()

        if not suppress_final_steps:
            self._final_sync_cols()
            self._set_attributes()
            self._create_dataframe()

    def read(self, force_reread: bool = False, suppress_final_steps: bool = False):
        """Reads LF file, starting from where it stopped reading last time"""

        self._read(force_reread, suppress_final_steps)

    def _init_counters(self):
        """Initialises counters that keep track of file during simulation"""

        self._no_lines = 0  # number of lines that have been read so far
        self._no_iters = 0  # number of iterations so far

    def _init_line_types(self):
        """Creates dictionary of LineType object for each entry in data_to_extract"""

        self._extracted_data = {}

        for key in self._data_to_extract:
            subdictionary = self._data_to_extract[key]
            subdictionary_class = subdictionary["class"]
            subdictionary_no_class = {
                k: v for k, v in subdictionary.items() if k != "class"
            }

            self._extracted_data[key] = subdictionary_class(**subdictionary_no_class)

    def _update_line_types(self):
        """Updates value of each LineType object based on raw data"""

        # self._print_no_lines()

        # loop through lines that haven't already been read
        raw_lines = self._raw_data[self._no_lines :]
        for raw_line in raw_lines:

            # loop through line types
            for key in self._data_to_extract:

                line_type = self._extracted_data[key]

                # lines which start with prefix
                if raw_line.startswith(line_type.prefix):

                    # store everything after prefix
                    end_of_line = raw_line.split(line_type.prefix)[1].lstrip()
                    processed_line = line_type.process_line_wrapper(end_of_line)
                    line_type.update_value_wrapper(processed_line)

                    # "elapsed" lines mark the end of an iteration
                    if line_type.index == True:
                        self._sync_cols()
                        self._no_iters += 1

            # update counter
            self._no_lines += 1

        # self._print_no_lines()

    def _set_attributes(self):
        """Makes each LineType value a direct attribute of LF"""

        # TODO: for values that don't change do a dictionary called info

        for key in self._data_to_extract:
            setattr(self, key, self._extracted_data[key].value)

    def _del_attributes(self):
        """Deletes each LineType value direct attribute of LF"""

        for key in self._data_to_extract:
            delattr(self, key)

    def _create_dataframe(self):
        """Collects LineType values (of type "many") into pandas dataframe"""

        # TODO: should be a LineType class method
        # that creates dataframe for each LineType
        # then this method combines them all together
        # Also:
        # - Replace by to_dataframe (returning df like ZZN, with filters)
        # - Indexed by simulated (and remove nan rows)
        # - Remove duplicates at start and end
        # - LF2 is not in sync

        # (1) create dictionary
        run = {}

        # loop through line types
        for key in self._data_to_extract:

            subdictionary = self._data_to_extract[key]
            type = subdictionary["type"]

            # only want "many" line types in data frame
            if type == "many":

                line_type = subdictionary["class"]
                value = self._extracted_data[key].value

                # line types with multiple entries per line
                if line_type == TimeFloatMult:

                    names = subdictionary["names"]
                    no_names = len(names)

                    # give each entry a column
                    for i in range(no_names):
                        new_key = names[i]
                        new_value = [item[i] for item in value]
                        run[new_key] = new_value

                # otherwise, one entry per line type
                else:
                    run[key] = value

        # (2) turn dictionary into dataframe
        self.df = pd.DataFrame(run)

    def _del_dataframe(self):
        """Deletes df attribute"""

        delattr(self, "df")

    def _sync_cols(self):
        """Ensures LineType values (of type "many") have an entry each iteration"""

        # loop through line types
        for key in self._data_to_extract:

            line_type = self._extracted_data[key]

            # sync line types that are not "elapsed"
            if line_type.index == False:

                # if their number of values is not in sync
                if line_type.type == "many" and line_type.no_values < (
                    self._no_iters + int(line_type.before_index)
                ):
                    # append nan to the list
                    line_type.update_value_wrapper(line_type._nan)

    def _final_sync_cols(self):
        """Makes LineType values (of type "many") the same length"""

        # find length of longest list
        max_length = 0

        for key in self._data_to_extract:

            line_type = self._extracted_data[key]

            if line_type.type == "many":
                length = len(line_type.value)
                max_length = max(max_length, length)

        # make other lists same size by adding nan, if necessary
        for key in self._data_to_extract:

            line_type = self._extracted_data[key]

            if line_type.type == "many":
                length = len(line_type.value)

                # before "elapsed" but stops just before "elapsed"
                if length == (max_length - 1):
                    line_type.update_value_wrapper(line_type._nan)

                # after "elapsed" but stops just before "elapsed"
                elif length == (max_length - 2):
                    line_type.update_value_wrapper(line_type._nan)
                    line_type.update_value_wrapper(line_type._nan)

        # TODO: What if you restart after this point?
        # Will end up with two partial rows of nans
        # But only if you don't have suppress_final_steps

    def _print_no_lines(self):
        """Prints number of lines that have been read so far"""

        print("Last line read: " + str(self._no_lines))

    def _report_progress(self) -> float:
        """Returns last progress percentage"""

        progress = self._extracted_data["progress"].value

        if progress is None:
            return 0

        return progress

    def _no_report_progress(self):
        raise NotImplementedError 

    @abstractmethod
    def _init_params_and_progress(self):
        pass


class LF1(LF):
    """Reads and processes Flood Modeller 1D log file '.lf1'

    Args:
        lf1_filepath (str): Full filepath to model lf1 file

    Output:
        Initiates 'LF1' class object
    """

    _filetype: str = "LF1"
    _suffix: str = ".lf1"

    def __init__(self, lf_filepath: Optional[Union[str, Path]], steady: bool = False):
        self._steady = steady
        super().__init__(lf_filepath)

    def _init_params_and_progress(self):
        """Uses dictionary from lf1_params.py to define data to extract"""
        if self._steady:
            self._data_to_extract = lf1_steady_data_to_extract
            self.report_progress = self._no_report_progress
        else:
            self._data_to_extract = lf1_unsteady_data_to_extract
            self.report_progress = self._report_progress


class LF2(LF):
    """Reads and processes Flood Modeller 1D log file '.lf2'

    Args:
        lf2_filepath (str): Full filepath to model lf2 file

    Output:
        Initiates 'LF2' class object
    """

    _filetype: str = "LF2"
    _suffix: str = ".lf2"

    def _init_params_and_progress(self):
        """Uses dictionary from lf2_params.py to define data to extract"""
        self._data_to_extract = lf2_data_to_extract
        self.report_progress = self._report_progress


def lf_factory(filepath: str, suffix: str, steady: bool) -> LF:
    if suffix == "lf1" and not steady:
        return LF1(filepath)
    elif suffix == "lf1" and steady:
        return LF1(filepath, steady = True)
    elif suffix == "lf2" and steady:
        return LF2(filepath)
    else:
        flow_type = "steady" if steady else "unsteady"
        raise ValueError(f"Unexpected log file type {suffix} for {flow_type} flow")
