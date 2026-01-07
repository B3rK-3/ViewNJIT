from backend.constants import COURSE_DATA
import backend.scrapers.constants
from backend.types import MakeScheduleFormat, CourseInfoModel, MakeScheduleFormat
from backend.functions import get_tools, UserFulfilled, set_local_data

set_local_data()

args = MakeScheduleFormat.model_validate(
    {
        "courses": ["math 337", "cs341", "cs350", "cs288", "com312", "ywcc 207"],
        "max_days": 2,
        "locked_in_sections": None,
        "min_rmp_rating": 4,
        "days": ["Monday", "Tuesday", "Thursday"],
    }
)
print(COURSE_DATA["CS 101"])
tools = get_tools(UserFulfilled(), "202610")
make_schedule = tools[4]
result = make_schedule(args)
print(result)

if result["schedules"]:
    first_schedule = result["schedules"][0]
    if "parsed_times" in first_schedule["sections"][0]:
        print("SUCCESS: parsed_times found in output")
    else:
        print("FAILURE: parsed_times NOT found in output")
