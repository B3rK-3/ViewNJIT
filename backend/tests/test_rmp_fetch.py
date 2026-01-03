import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.scrapers.rmp import sync_lecturer_rating
import json
from backend.constants import LECTURERS_FILE


def test_sync():
    test_lecturer = "Calvin, James"
    print(f"Testing sync for {test_lecturer}...")

    # Run sync
    print(sync_lecturer_rating(test_lecturer))

    # Verify lecturers.json
    if os.path.exists(LECTURERS_FILE):
        with open(LECTURERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if test_lecturer in data:
                print(f"✓ Found rating for {test_lecturer}:")
                print(json.dumps(data[test_lecturer], indent=4))
            else:
                print(f"✗ Rating for {test_lecturer} not found in {LECTURERS_FILE}")
    else:
        print(f"✗ {LECTURERS_FILE} does not exist")


if __name__ == "__main__":
    test_sync()
