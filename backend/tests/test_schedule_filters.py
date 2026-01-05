import sys
import os
import unittest
import json
from unittest.mock import MagicMock, patch

# Add parent directory to path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.constants import MakeScheduleFormat, CourseInfoModel, MakeScheduleFormat
from backend.functions import get_tools, UserFulfilled


class TestScheduleFilters(unittest.TestCase):
    def setUp(self):
        # Mock Course Data
        # We need to construct objects that look like CourseInfoModel or are dicts compatible with how it's used.
        # functions.py accesses COURSE_DATA[name].sections

        # Let's use a dict that behaves like the object for the attributes accessed
        self.mock_course_data = {
            "CS 101": MagicMock(
                sections={
                    "202610": {
                        "001": [
                            "CS 101",
                            "12345",
                            "MW",
                            "10:00 AM - 11:20 AM",
                            "Room 1",
                            "Open",
                            "30",
                            "10",
                            "Prof Good",
                            "Face",
                            "3",
                            "Info",
                            "Notes",
                        ],
                        "002": [
                            "CS 101",
                            "12346",
                            "TR",
                            "10:00 AM - 11:20 AM",
                            "Room 2",
                            "Open",
                            "30",
                            "10",
                            "Prof Bad",
                            "Face",
                            "3",
                            "Info",
                            "Notes",
                        ],
                        "003": [
                            "CS 101",
                            "12347",
                            "F",
                            "10:00 AM - 01:00 PM",
                            "Room 3",
                            "Open",
                            "30",
                            "10",
                            "Prof OK",
                            "Face",
                            "3",
                            "Info",
                            "Notes",
                        ],
                    }
                }
            )
        }

        # Mock Redis for RMP
        self.mock_redis = MagicMock()

        def redis_hget(key, field):
            ratings = {
                "Prof Good": '{"avgRating": "4.5"}',
                "Prof Bad": '{"avgRating": "2.0"}',
                "Prof OK": '{"avgRating": "3.5"}',
            }
            return ratings.get(field)

        self.mock_redis.hget.side_effect = redis_hget

    @patch("backend.functions.COURSE_DATA", new_callable=dict)
    @patch("backend.functions.x")
    @patch("backend.functions.normalize_course")
    def test_make_schedule_filters(
        self, mock_normalize, mock_redis_obj, mock_course_data_obj
    ):
        # Setup mocks
        mock_course_data_obj.update(self.mock_course_data)
        mock_redis_obj.hget.side_effect = self.mock_redis.hget.side_effect
        mock_normalize.side_effect = lambda x: x  # Identity for valid names

        # Get the make_schedule function
        tools = get_tools(UserFulfilled(), "202610")
        make_schedule = tools[4]  # Index 4 is make_schedule based on return list

        # Test 1: Locked-in Sections
        print("\nTesting Locked-in Sections...")
        args = MakeScheduleFormat(
            courses=["CS 101"],
            max_days=5,
            locked_in_sections={"CS 101": [1]},  # Should match "001"
        )
        result = make_schedule(args)
        schedules = result.get("schedules", [])
        self.assertTrue(len(schedules) > 0, "Should have found schedules")
        for sched in schedules:
            self.assertEqual(sched["sections"][0]["section_id"], "001")
        print("Locked-in sections check passed.")

        # Test 2: RMP Rating (Min 4.0) -> Should only get Prof Good (001)
        print("\nTesting RMP Rating...")
        args = MakeScheduleFormat(courses=["CS 101"], max_days=5, min_rmp_rating=4.0)
        result = make_schedule(args)
        schedules = result.get("schedules", [])
        self.assertTrue(len(schedules) > 0, "Should find high rated prof")
        for sched in schedules:
            self.assertEqual(sched["sections"][0]["instructor"], "Prof Good")
        print("RMP Rating check passed.")

        # Test 3: Specific Days (TR) -> Should only get 002
        print("\nTesting Specific Days...")
        args = MakeScheduleFormat(
            courses=["CS 101"], max_days=5, days=["Tuesday", "Thursday"]
        )
        result = make_schedule(args)
        schedules = result.get("schedules", [])
        self.assertTrue(len(schedules) > 0, "Should find course on TR")
        for sched in schedules:
            self.assertEqual(sched["sections"][0]["section_id"], "002")
        print("Days filtering check passed.")

        print("\nAll tests passed!")


if __name__ == "__main__":
    unittest.main()
