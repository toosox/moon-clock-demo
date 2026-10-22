from datetime import datetime, timedelta, timezone
import unittest
from zoneinfo import ZoneInfo

from moon_phase import _phase_event, calculate_moon_data


class MoonPhaseTests(unittest.TestCase):
    def test_reference_new_moon(self):
        data = calculate_moon_data(datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc))
        self.assertEqual(data.phase_name, "New Moon")
        self.assertLess(data.age_days, 0.1)
        self.assertLess(data.illumination_percent, 0.1)

    def test_2026_nasa_reference_phase_times(self):
        references = ((322.0, datetime(2026, 1, 18, 19, 52, tzinfo=timezone.utc)), (322.5, datetime(2026, 2, 1, 22, 9, tzinfo=timezone.utc)), (323.0, datetime(2026, 2, 17, 12, 1, tzinfo=timezone.utc)), (323.75, datetime(2026, 3, 11, 9, 39, tzinfo=timezone.utc)))
        for lunation, expected in references:
            self.assertLessEqual(abs(_phase_event(lunation) - expected), timedelta(minutes=5))

    def test_phase_boundary_uses_the_calculated_event(self):
        event = _phase_event(322.5)
        self.assertEqual(calculate_moon_data(event - timedelta(minutes=1)).next_phase_name, "Full Moon")
        self.assertEqual(calculate_moon_data(event + timedelta(minutes=1)).next_phase_name, "Last Quarter")

    def test_leap_day_and_daylight_saving_aware_datetimes(self):
        leap_day = datetime(2024, 2, 29, 12, 0, tzinfo=timezone.utc)
        daylight_saving = datetime(2024, 3, 10, 3, 0, tzinfo=ZoneInfo("America/Chicago"))
        self.assertGreaterEqual(calculate_moon_data(leap_day).age_days, 0)
        self.assertGreaterEqual(calculate_moon_data(daylight_saving).age_days, 0)


if __name__ == "__main__":
    unittest.main()
