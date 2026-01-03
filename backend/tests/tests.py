from constants import MakeScheduleFormat
from constants import UserFulfilled
from functions import get_tools


result = get_tools(UserFulfilled(), "202610")[-1](
    MakeScheduleFormat(
        courses=["cs350", "cs288", "com312", "ywcc207", "cs341", "math337"], max_days=3
    )
)
result