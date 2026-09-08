"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.vehicle.brands.base import BrandSettings
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.sunnypilot.common.params_compat import get_param_compat, put_param_compat
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.sunnypilot.widgets.list_view import multiple_button_item_sp
from opendbc.car.hyundai.values import CAR, UNSUPPORTED_LONGITUDINAL_CAR

# experimental KIA_NIRO_PHEV lateral tuning, see opendbc.sunnypilot.car.interfaces
NIRO_PHEV_STEER_MAX_LEVELS = (255, 300, 340, 384)  # index == HyundaiNiroPhevSteerMaxLevel
NIRO_PHEV_MIN_STEER_SPEEDS_MPH = (32, 28, 24, 20, 15)  # HyundaiNiroPhevMinSteerSpeedMph, 32 is stock


class HyundaiSettings(BrandSettings):
  def __init__(self):
    super().__init__()
    self.alpha_long_available = False

    tuning_texts = [tr("Off"), tr("Dynamic"), tr("Predictive")]
    self.longitudinal_tuning_item = multiple_button_item_sp(tr("Custom Longitudinal Tuning"), "", tuning_texts,
                                                            button_width=300, callback=self._on_tuning_selected,
                                                            param="HyundaiLongitudinalTuning", inline=False)
    # KIA_NIRO_PHEV only. These params are not passed to the widgets on purpose: on a prebuilt branch the
    # compiled params table does not know them, so reads and writes go through params_compat instead
    # (stored next to the params directory, where the onroad/offroad sweep does not delete them).
    steer_max_texts = [tr("Stock")] + [str(v) for v in NIRO_PHEV_STEER_MAX_LEVELS[1:]]
    self.niro_steer_max_item = multiple_button_item_sp(tr("Niro PHEV Max Steer Torque"), "", steer_max_texts,
                                                       button_width=250, callback=self._on_niro_steer_max_selected, inline=False)
    min_steer_speed_texts = [tr("Stock")] + [str(v) for v in NIRO_PHEV_MIN_STEER_SPEEDS_MPH[1:]]
    self.niro_min_steer_speed_item = multiple_button_item_sp(tr("Niro PHEV Min Steer Speed (mph)"), "", min_steer_speed_texts,
                                                             button_width=250, callback=self._on_niro_min_steer_speed_selected, inline=False)
    self.items = [self.longitudinal_tuning_item, self.niro_steer_max_item, self.niro_min_steer_speed_item]

  @staticmethod
  def _on_tuning_selected(index):
    ui_state.params.put("HyundaiLongitudinalTuning", index)

  @staticmethod
  def _on_niro_steer_max_selected(index):
    put_param_compat(ui_state.params, "HyundaiNiroPhevSteerMaxLevel", index)

  @staticmethod
  def _on_niro_min_steer_speed_selected(index):
    put_param_compat(ui_state.params, "HyundaiNiroPhevMinSteerSpeedMph", NIRO_PHEV_MIN_STEER_SPEEDS_MPH[index])

  @staticmethod
  def _get_platform():
    bundle = ui_state.params.get("CarPlatformBundle")
    if bundle:
      return bundle.get("platform")
    if ui_state.CP is not None:
      return ui_state.CP.carFingerprint
    return None

  @staticmethod
  def _param_int(key: str, default: int) -> int:
    try:
      return int(get_param_compat(ui_state.params, key) or default)
    except (TypeError, ValueError):
      return default

  def _update_niro_phev_settings(self):
    is_niro_phev = self._get_platform() == CAR.KIA_NIRO_PHEV
    self.niro_steer_max_item.set_visible(is_niro_phev)
    self.niro_min_steer_speed_item.set_visible(is_niro_phev)
    if not is_niro_phev:
      return

    offroad = ui_state.is_offroad()
    onroad_desc = tr("This feature is unavailable while the car is onroad.")

    level = self._param_int("HyundaiNiroPhevSteerMaxLevel", 0)
    if level not in range(len(NIRO_PHEV_STEER_MAX_LEVELS)):
      level = 0
    steer_max_desc = tr("Experimental. Raises the LKAS torque ceiling openpilot may request. Panda safety still enforces 384. " +
                        "Applies at the next ignition on. Current: {} (stock is 255).").format(NIRO_PHEV_STEER_MAX_LEVELS[level])
    self.niro_steer_max_item.action_item.set_enabled(offroad)
    self.niro_steer_max_item.set_description(steer_max_desc if offroad else onroad_desc)
    self.niro_steer_max_item.show_description(True)
    self.niro_steer_max_item.action_item.set_selected_button(level)

    speed = self._param_int("HyundaiNiroPhevMinSteerSpeedMph", NIRO_PHEV_MIN_STEER_SPEEDS_MPH[0])
    speed_index = NIRO_PHEV_MIN_STEER_SPEEDS_MPH.index(speed) if speed in NIRO_PHEV_MIN_STEER_SPEEDS_MPH else 0
    min_speed_desc = tr("Experimental. Lowers the speed at which sunnypilot starts steering, to test whether the stock MDPS accepts torque " +
                        "below 32 mph. Applies at the next ignition on. Current: {} mph (stock is 32).").format(NIRO_PHEV_MIN_STEER_SPEEDS_MPH[speed_index])
    self.niro_min_steer_speed_item.action_item.set_enabled(offroad)
    self.niro_min_steer_speed_item.set_description(min_speed_desc if offroad else onroad_desc)
    self.niro_min_steer_speed_item.show_description(True)
    self.niro_min_steer_speed_item.action_item.set_selected_button(speed_index)

  def update_settings(self):
    self._update_niro_phev_settings()

    self.alpha_long_available = False
    bundle = ui_state.params.get("CarPlatformBundle")
    if bundle:
      platform = bundle.get("platform")
      self.alpha_long_available = CAR[platform] not in set().union(*UNSUPPORTED_LONGITUDINAL_CAR.values())
    elif ui_state.CP is not None:
      self.alpha_long_available = ui_state.CP.alphaLongitudinalAvailable

    tuning_param = int(ui_state.params.get("HyundaiLongitudinalTuning") or "0")
    long_enabled = ui_state.has_longitudinal_control

    long_tuning_descs = [
      tr("Your vehicle will use the Default longitudinal tuning."),
      tr("Your vehicle will use the Dynamic longitudinal tuning."),
      tr("Your vehicle will use the Predictive longitudinal tuning."),
    ]
    long_tuning_desc = long_tuning_descs[tuning_param] if tuning_param < len(long_tuning_descs) else long_tuning_descs[0]

    longitudinal_tuning_disabled = not ui_state.is_offroad() or not long_enabled
    if longitudinal_tuning_disabled:
      if not ui_state.is_offroad():
        long_tuning_desc = tr("This feature is unavailable while the car is onroad.")
      elif not long_enabled:
        long_tuning_desc = tr("This feature is unavailable because sunnypilot Longitudinal Control (Alpha) is not enabled.")

    self.longitudinal_tuning_item.action_item.set_enabled(not longitudinal_tuning_disabled)
    self.longitudinal_tuning_item.set_description(long_tuning_desc)
    self.longitudinal_tuning_item.show_description(True)
    self.longitudinal_tuning_item.action_item.set_selected_button(tuning_param)
    self.longitudinal_tuning_item.set_visible(self.alpha_long_available)
