"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import os

from openpilot.common.params import Params
from openpilot.common.test import OpenpilotTestCase
from openpilot.sunnypilot.common.params_compat import get_param_compat, put_param_compat

UNKNOWN_KEY = "ParamsCompatTestKeyNotInParamsKeysH"


class TestParamsCompat(OpenpilotTestCase):
  def setUp(self):
    super().setUp()
    self.params = Params()

  def test_known_key_uses_params(self):
    put_param_compat(self.params, "HyundaiLongitudinalTuning", 2)
    assert self.params.get("HyundaiLongitudinalTuning") == 2
    assert get_param_compat(self.params, "HyundaiLongitudinalTuning") == 2

  def test_known_key_default(self):
    assert get_param_compat(self.params, "HyundaiLongitudinalTuning") == 0

  def test_unknown_key_missing_is_none(self):
    assert get_param_compat(self.params, UNKNOWN_KEY) is None

  def test_unknown_key_roundtrip_via_file(self):
    put_param_compat(self.params, UNKNOWN_KEY, 3)
    path = os.path.join(self.params.get_param_path(), UNKNOWN_KEY)
    assert os.path.isfile(path)
    assert not os.path.exists(path + ".tmp")
    with open(path) as f:
      assert f.read() == "3"
    assert get_param_compat(self.params, UNKNOWN_KEY) == "3"

    # same format the shell workflow uses: echo -n 1 > /data/params/d/<key>
    with open(path, "w") as f:
      f.write("1")
    assert get_param_compat(self.params, UNKNOWN_KEY) == "1"
