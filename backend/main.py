from functions import gemini_call
from functions import initialize_database, course_query
import json


def main() -> None:
    
    print("Starting ChromaDB initialization...")
    initialize_database()
    print("Initialization complete.\n")
    gemini_call()



if __name__ == "__main__":
    main()
