"""
Tests for the experimental KIA_NIRO_PHEV LKAS torque ceiling (HyundaiNiroPhevSteerMaxLevel) and
minSteerSpeed override (HyundaiNiroPhevMinSteerSpeedMph).
"""
import unittest

from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC, CarControllerParams, HyundaiFlags
from opendbc.sunnypilot.car.hyundai.values import HyundaiFlagsSP
from opendbc.sunnypilot.car.interfaces import setup_interfaces

STEER_MAX_FLAGS = (HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_300, HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_340, HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_384)
ALL_STEER_MAX_FLAGS = HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_300 | HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_340 | HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_384


def make_params(platform, params_list=None):
  CP = CarInterface.get_non_essential_params(platform)
  CP_SP = CarInterface.get_non_essential_params_sp(CP, platform)
  setup_interfaces(CarInterface, CP, CP_SP, params_list)
  return CP, CP_SP


class TestNiroPhevSteerMax(unittest.TestCase):
  def test_flag_bits_are_unique(self):
    for flag in STEER_MAX_FLAGS:
      others = [f for f in HyundaiFlagsSP if f != flag]
      self.assertFalse(any(f.value & flag.value for f in others), f"{flag.name} collides with another HyundaiFlagsSP bit")

  def test_level_sets_expected_flag(self):
    expected = {
      0: 0,
      1: HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_300.value,
      2: HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_340.value,
      3: HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_384.value,
    }
    for level, flag in expected.items():
      with self.subTest(level=level):
        _, CP_SP = make_params(CAR.KIA_NIRO_PHEV, [{"HyundaiNiroPhevSteerMaxLevel": level}])
        self.assertEqual(CP_SP.flags & ALL_STEER_MAX_FLAGS, flag)

  def test_level_value_types_and_garbage(self):
    # Params INT keys may be decoded as int, str or bytes; anything unparseable or out of range means stock
    for value, flag in (("3", HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_384.value), (b"2", HyundaiFlagsSP.NIRO_PHEV_STEER_MAX_340.value),
                        ("", 0), (None, 0), ("abc", 0), (4, 0), (-1, 0), (255, 0)):
      with self.subTest(value=value):
        _, CP_SP = make_params(CAR.KIA_NIRO_PHEV, [{"HyundaiNiroPhevSteerMaxLevel": value}])
        self.assertEqual(CP_SP.flags & ALL_STEER_MAX_FLAGS, flag)

  def test_param_unset_is_stock(self):
    CP, CP_SP = make_params(CAR.KIA_NIRO_PHEV)
    self.assertEqual(CP_SP.flags & ALL_STEER_MAX_FLAGS, 0)
    self.assertEqual(CarController(DBC[CAR.KIA_NIRO_PHEV], CP, CP_SP).params.STEER_MAX, 255)

  def test_carcontroller_steer_max_per_level(self):
    for level, steer_max in ((0, 255), (1, 300), (2, 340), (3, 384)):
      with self.subTest(level=level):
        CP, CP_SP = make_params(CAR.KIA_NIRO_PHEV, [{"HyundaiNiroPhevSteerMaxLevel": level}])
        CC = CarController(DBC[CAR.KIA_NIRO_PHEV], CP, CP_SP)
        self.assertEqual(CC.params.STEER_MAX, steer_max)
        # never above what panda safety enforces for Hyundai
        self.assertLessEqual(CC.params.STEER_MAX, 384)
        # rate limits and driver allowance are untouched
        self.assertEqual(CC.params.STEER_DELTA_UP, 3)
        self.assertEqual(CC.params.STEER_DELTA_DOWN, 7)
        self.assertEqual(CC.params.STEER_DRIVER_ALLOWANCE, 50)
        # carstate keeps the stock copy for driver override detection
        CS = CarState(CP, CP_SP)
        self.assertEqual(CS.params.STEER_MAX, 255)
        self.assertEqual(CS.params.STEER_THRESHOLD, 150)

  def test_highest_flag_wins(self):
    CP, CP_SP = make_params(CAR.KIA_NIRO_PHEV)
    CP_SP.flags |= ALL_STEER_MAX_FLAGS
    self.assertEqual(CarController(DBC[CAR.KIA_NIRO_PHEV], CP, CP_SP).params.STEER_MAX, 384)

  def test_other_platforms_unaffected(self):
    # the param must not set flags on any other platform, and the flags must not change STEER_MAX on any other platform
    for platform in (CAR.KIA_NIRO_EV, CAR.KIA_NIRO_PHEV_2022, CAR.HYUNDAI_SONATA, CAR.HYUNDAI_SONATA_LF):
      with self.subTest(platform=platform):
        CP, CP_SP = make_params(platform, [{"HyundaiNiroPhevSteerMaxLevel": 3}])
        self.assertEqual(CP_SP.flags & ALL_STEER_MAX_FLAGS, 0)
        CP_SP.flags |= ALL_STEER_MAX_FLAGS
        self.assertEqual(CarController(DBC[platform], CP, CP_SP).params.STEER_MAX, CarControllerParams(CP).STEER_MAX)


class TestNiroPhevMinSteerSpeed(unittest.TestCase):
  STOCK = 32 * CV.MPH_TO_MS

  def test_default_is_stock(self):
    for params_list in (None, [{"HyundaiNiroPhevMinSteerSpeedMph": 32}], [{"HyundaiNiroPhevMinSteerSpeedMph": "32"}],
                        [{"HyundaiNiroPhevMinSteerSpeedMph": 40}], [{"HyundaiNiroPhevMinSteerSpeedMph": ""}], [{"HyundaiNiroPhevMinSteerSpeedMph": "abc"}]):
      with self.subTest(params_list=params_list):
        CP, _ = make_params(CAR.KIA_NIRO_PHEV, params_list)
        self.assertAlmostEqual(CP.minSteerSpeed, self.STOCK, places=3)
        self.assertTrue(CP.flags & HyundaiFlags.MIN_STEER_32_MPH)

  def test_override_lowers_min_steer_speed(self):
    for mph in (31, 25, 15):
      with self.subTest(mph=mph):
        CP, _ = make_params(CAR.KIA_NIRO_PHEV, [{"HyundaiNiroPhevMinSteerSpeedMph": mph}])
        self.assertAlmostEqual(CP.minSteerSpeed, mph * CV.MPH_TO_MS, places=3)
        self.assertFalse(CP.flags & HyundaiFlags.MIN_STEER_32_MPH)

  def test_override_is_clamped_to_floor(self):
    for mph in (14, 5, 0, -10):
      with self.subTest(mph=mph):
        CP, _ = make_params(CAR.KIA_NIRO_PHEV, [{"HyundaiNiroPhevMinSteerSpeedMph": mph}])
        self.assertAlmostEqual(CP.minSteerSpeed, 15 * CV.MPH_TO_MS, places=3)
        self.assertGreater(CP.minSteerSpeed, 0.0)

  def test_never_raises_existing_floor(self):
    # e.g. smartMDPS detection already set minSteerSpeed to 0
    CP = CarInterface.get_non_essential_params(CAR.KIA_NIRO_PHEV)
    CP_SP = CarInterface.get_non_essential_params_sp(CP, CAR.KIA_NIRO_PHEV)
    CP.minSteerSpeed = 0.0
    CP.flags &= ~HyundaiFlags.MIN_STEER_32_MPH.value
    setup_interfaces(CarInterface, CP, CP_SP, [{"HyundaiNiroPhevMinSteerSpeedMph": 20}])
    self.assertEqual(CP.minSteerSpeed, 0.0)

  def test_other_platforms_unaffected(self):
    for platform in (CAR.KIA_NIRO_EV, CAR.KIA_NIRO_PHEV_2022, CAR.HYUNDAI_SONATA_LF):
      with self.subTest(platform=platform):
        stock_CP, _ = make_params(platform)
        CP, _ = make_params(platform, [{"HyundaiNiroPhevMinSteerSpeedMph": 20}])
        self.assertEqual(CP.minSteerSpeed, stock_CP.minSteerSpeed)
        self.assertEqual(CP.flags, stock_CP.flags)


if __name__ == "__main__":
  unittest.main()
