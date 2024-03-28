import os
import json
from pathlib import Path

import pytest

from floodmodeller_api import DAT, IED, IEF, XML2D
from floodmodeller_api.util import read_file
from floodmodeller_api.to_from_json import is_jsonable


def create_expected_json_files():
    """Helper function to recreate all the expected JSON files if needed at any point due to updates
    to the to_json code"""

    test_workspace = Path(os.path.dirname(__file__), "test_data")
    for file in [
        "network.dat",
        "network.ied",
        "EX3.DAT",
        "EX6.DAT",
        "EX18.DAT",
        "EX3.IEF",
        "Domain1_Q.xml",
        "Linked1D2D.xml",
    ]:  
        file = Path(test_workspace, file)
        obj = read_file(file)
        with open(file.with_name(f"{file.name.replace('.', '_')}_expected").with_suffix(".json"), "w") as json_file:
            json_file.write(obj.to_json())


@pytest.fixture
def dat_obj(test_workspace):
    """JSON:  To create the dat object for the tests"""
    return DAT(Path(test_workspace, "EX18.DAT"))


@pytest.fixture
def json_expected(test_workspace):
    """JSON:  expected after passing to_json method"""
    return Path(test_workspace, "EX18_DAT_expected.json")


def test_dat_json(dat_obj):
    """JSON:  To test if to_json runs without failing"""
    assert dat_obj.to_json()


@pytest.fixture
def parameterised_objs_and_expected(test_workspace):
    """JSON:  expected after passing to_json method"""
    return [
        (DAT(Path(test_workspace, "EX18.DAT")), Path(test_workspace, "EX18_DAT_expected.json")),
        (DAT(Path(test_workspace, "network.dat")), Path(test_workspace, "network_dat_expected.json")),
        (IED(Path(test_workspace, "network.ied")), Path(test_workspace, "network_ied_expected.json")),
        (DAT(Path(test_workspace, "EX3.DAT")), Path(test_workspace, "EX3_DAT_expected.json")),
        (DAT(Path(test_workspace, "EX6.DAT")), Path(test_workspace, "EX6_DAT_expected.json")),
        (IEF(Path(test_workspace, "EX3.IEF")), Path(test_workspace, "EX3_IEF_expected.json")),
        (XML2D(Path(test_workspace, "Domain1_Q.xml")), Path(test_workspace, "Domain1_Q_xml_expected.json")),
        (XML2D(Path(test_workspace, "Linked1D2D.xml")), Path(test_workspace, "Linked1D2D_xml_expected.json")),
    ]


def test_to_json_matches_expected(parameterised_objs_and_expected):
    """JSON:  To test if the json object produced in to_json is identical to the expected json file"""
    for obj, json_expected in parameterised_objs_and_expected:
        # First, to create and handle the json (str) object
        # loads is to convert a json string document into a python dictionary
        json_dict_from_obj = json.loads(obj.to_json())["Object Attributes"]

        # Second, to handle the json file EX18_expected.json which must be the same as the object created above.
        json_dict_from_file = json.load(open(json_expected))["Object Attributes"]  # noqa: SIM115

        # keys with paths and timing that must be removed to avoid issues when testing.
        keys_to_remove = ["_filepath", "file"]

        for key in keys_to_remove:
            del json_dict_from_obj[key]
            del json_dict_from_file[key]

        assert json_dict_from_obj == json_dict_from_file


def test_dat_reproduces_from_json_for_all_test_dat_files(test_workspace):
    """JSON:  To test the from_json function,  It should produce the same dat file from a json file"""
    for datfile in Path(test_workspace).glob("*.dat"):
        assert DAT(datfile) == DAT.from_json(DAT(datfile).to_json())


def test_is_jsonable_with_jsonable_object():
    assert is_jsonable({"a": 1, "b": 2})


def test_is_jsonable_with_non_jsonable_object():
    class NonJsonable:
        def __init__(self):
            pass

    assert not is_jsonable(NonJsonable())
