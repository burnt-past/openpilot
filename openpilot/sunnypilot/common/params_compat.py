"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import os

from openpilot.common.params import Params, UnknownKeyName

# Prebuilt branches ship a compiled key table in libparams_c.so, so a key that is only declared in
# params_keys.h stays unknown to Params until the next scons build. These helpers use Params when the
# key is known and fall back to the raw file in the params directory otherwise, so a param-driven
# feature added on top of a prebuilt release can be read and written without a rebuild.


def _param_file(params: Params, key: str) -> str:
  return os.path.join(params.get_param_path(), key)


def get_param_compat(params: Params, key: str):
  try:
    return params.get(key, return_default=True)
  except UnknownKeyName:
    try:
      with open(_param_file(params, key), "rb") as f:
        return f.read().decode("utf-8", errors="ignore").strip()
    except OSError:
      return None


def put_param_compat(params: Params, key: str, value) -> None:
  try:
    params.put(key, value)
  except UnknownKeyName:
    path = _param_file(params, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
      f.write(str(value))
      f.flush()
      os.fsync(f.fileno())
    os.replace(tmp_path, path)
