import json
import requests
from bs4 import BeautifulSoup
import random
import time
import argparse
import dotenv
from google import genai
from google.genai import types
import os
import base64
from typing import Dict, List, Optional, Any, Union
from backend.scrapers.rmp import sync_lecturer_rating
from backend.scrapers.constants import (
    DESCRIPTION_PROCESS_PROMPT_FILE,
    logger,
    COURSE_DATA,
    set_redis_course_data,
    CourseStructureModel,
)
from backend.constants import COURSE_DATA_FILE

dotenv.load_dotenv()


links = [
    "https://catalog.njit.edu/graduate/computing-sciences/#coursestext",
    "https://catalog.njit.edu/graduate/architecture-design/#coursestext",
    "https://catalog.njit.edu/graduate/science-liberal-arts/#coursestext",
    "https://catalog.njit.edu/graduate/newark-college-engineering/#coursestext",
    "https://catalog.njit.edu/graduate/management/#coursestext",
    "https://catalog.njit.edu/undergraduate/computing-sciences/#coursestext",
    "https://catalog.njit.edu/undergraduate/architecture-design/#coursestext",
    "https://catalog.njit.edu/undergraduate/science-liberal-arts/#coursestext",
    "https://catalog.njit.edu/undergraduate/newark-college-engineering/#coursestext",
    "https://catalog.njit.edu/undergraduate/management/#coursestext",
]
semesters = {"10": "Spring", "95": "Winter", "90": "Fall", "50": "Summer"}


def get_individual_course(course_code: str) -> Dict[str, Any]:
    url = f"https://catalog.njit.edu/search/?P={course_code}"
    course_obj = {"desc": "No Description", "title": "Unkown"}
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            target_header = soup.find("div", class_="search-courseresult")
            title_ele = target_header.find("h2").get_text(strip=True)
            title = title_ele.split(".")[1].strip()
            course_obj["title"] = title

            # Find a <p> field with 'Prerequisites:'
            target_p = soup.find("p", class_="courseblockdesc")
            if target_p:
                full_text = target_p.get_text().strip()
                course_obj["desc"] = full_text
            else:
                course_obj["desc"] = "No Description"
            return course_obj
    except Exception as e:
        # Fail silently or log if needed, but keep the course object
        return course_obj


def process_single_description(description: str) -> Union[Dict[str, Any], None, dict]:
    """
    Takes a single course description, queries the Gemini model using the prompt template,
    and returns the parsed JSON output.
    """

    if description.lower() in ("", "no description"):
        return {
            "prereq_tree": None,
            "coreq_tree": None,
            "restrictions": [],
        }

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is not set.")
        return None

    client = genai.Client(api_key=api_key)

    with open(DESCRIPTION_PROCESS_PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    final_prompt = prompt_template + "\n INPUT: " + description

    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=final_prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )

        # Parse JSON response
        try:
            # Handle potential 'undefined' values from model output
            clean_text = response.text.replace("undefined", "null")
            parsed_json = json.loads(clean_text)
            return parsed_json
        except json.JSONDecodeError:
            logger.error(f"Error parsing JSON. Raw output: {response.text}")
            return {
                "error": "JSON Parse Error",
                "raw_response": response.text,
            }

    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return {}


# ===== SECTION SCRAPER FUNCTIONS =====
def pb_encode(s: str) -> str:
    """
    Encodes a string using the Ellucian Page Builder obfuscation:
    Base64(Random_Integer_String) + Base64(Target_String)
    """
    # 1. Generate a random salt (usually a 2-digit number)
    salt = str(random.randint(10, 99))

    # 2. Base64 encode the salt and the actual string
    salt_b64 = base64.b64encode(salt.encode("utf-8")).decode("utf-8")
    val_b64 = base64.b64encode(s.encode("utf-8")).decode("utf-8")

    # 3. Concatenate them
    return salt_b64 + val_b64


def fetch_courses(
    subject: str, term: str, max_results: str = "9999", offset: str = "0"
) -> Optional[Dict[str, Any]]:
    url = "https://generalssb-prod.ec.njit.edu/BannerExtensibility/internalPb/virtualDomains.stuRegCrseSchedSections"

    # Define the raw parameters we want to send
    raw_params = {
        "term": term,
        "subject": subject,
        "max": max_results,
        "offset": offset,
        "attr": "",  # Attribute is usually empty based on your logs
    }

    # obfuscate keys AND values
    encoded_params = {}
    for key, value in raw_params.items():
        enc_key = pb_encode(key)
        enc_val = pb_encode(value)
        encoded_params[enc_key] = enc_val

    # The 'encoded' flag must be true (sent as plain text)
    encoded_params["encoded"] = "true"

    # Headers - mimicking a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://generalssb-prod.ec.njit.edu/BannerExtensibility/customPage/page/stuRegCrseSched",
    }

    # COOKIES: You must update this with a fresh JSESSIONID from your browser
    # The session often expires quickly.
    cookies = {
        "JSESSIONID": "4216B7AFB3D9E1094A2F45F8210AC0D4"  # <--- REPLACE THIS
    }

    try:
        response = requests.get(url, params=encoded_params, headers=headers)
        response.raise_for_status()
        # Parse JSON if successful
        return response.json()

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: {e}")
        logger.debug(f"Response Body: {response.text}")
        return None


def fetch_subj_list(
    term: str, max_results: str = "9999", offset: str = "0"
) -> Optional[List[Dict[str, Any]]]:
    url = "https://generalssb-prod.ec.njit.edu/BannerExtensibility/internalPb/virtualDomains.stuRegCrseSchedSubjList"

    # Define the raw parameters we want to send
    raw_params = {
        "term": term,
        "max": max_results,
        "offset": offset,
        "attr": "",  # Attribute is usually empty based on your logs
    }

    # obfuscate keys AND values
    encoded_params = {}
    for key, value in raw_params.items():
        enc_key = pb_encode(key)
        enc_val = pb_encode(value)
        encoded_params[enc_key] = enc_val

    # The 'encoded' flag must be true (sent as plain text)
    encoded_params["encoded"] = "true"

    # Headers - mimicking a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://generalssb-prod.ec.njit.edu/BannerExtensibility/customPage/page/stuRegCrseSched",
    }

    # COOKIES: You must update this with a fresh JSESSIONID from your browser
    # The session often expires quickly.
    cookies = {
        "JSESSIONID": "4216B7AFB3D9E1094A2F45F8210AC0D4"  # <--- REPLACE THIS
    }

    try:
        response = requests.get(url, params=encoded_params, headers=headers)
        response.raise_for_status()
        # Parse JSON if successful
        return response.json()

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: {e}")
        logger.debug(f"Response Body: {response.text}")
        return None


def run_section_scraper(term: str) -> Dict[str, Any]:
    """Run the section scraper to fetch course data from the API and return as dict"""
    logger.info("STEP 1: Running Section Scraper")

    # Load subjects
    # fetch list of subjects from api
    subjects_list = fetch_subj_list(term)
    final_data = {}

    for item in subjects_list:
        subj = item.get("SUBJECT")
        if subj:
            logger.info(f"Fetching courses for {subj}...")
            # fetch courses for specific subject
            response_data = fetch_courses(subj, term, max_results="500")

            final_data[subj] = response_data

            time.sleep(0.2)

    logger.info(f"Section scraper complete. Fetched {len(final_data)} subjects")
    return final_data


# ===== MAIN PARSER FUNCTIONS =====


def extract_sections_from_html(html_content: str, term: str) -> None:
    """Extract all course sections from HTML content by finding h4 elements and their following tables"""
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all h4 elements (each represents a course)
        h4_elements = soup.find_all("h4")

        for h4 in h4_elements:
            # Extract id from h4
            course_id = h4.get("id")
            if not course_id:
                continue

            honors_sections = False

            header: str = h4.get_text(strip=True)
            if header.lower().endswith("honors"):
                honors_sections = True
                right_dash = header.rfind("-")
                left_dash = header.find("-")

                header = header[left_dash + 1 : right_dash].strip()
            else:
                left_dash = header.find("-")
                header = header[left_dash + 1 :].strip()

            current = h4.next_sibling
            table = None
            num_credits = 0

            while current:
                if hasattr(current, "name"):
                    if current.name == "table":
                        table = current
                        break
                current = current.next_sibling

            if table:
                # Extract sections from this table
                rows = table.find_all("tr")
                sections = {}

                # loop each section Skip the first row (header)
                for row in rows[1:]:
                    tds = row.find_all("td")

                    # Extract section cloumn info
                    td_values = []
                    for i, td in enumerate(tds):
                        text = ""
                        # For links, extract the text content
                        if td.find("a"):
                            text = td.find("a").get_text(strip=True)
                        else:
                            text = td.get_text(strip=True)
                            # Special handling for rooms column (4th index, 0-based)
                        if (i == 4 or i == 3) and td.find("br"):
                            text = td.get_text(separator=", ", strip=True)

                        td_values.append(text)
                    section_key = td_values[0]
                    sections[section_key] = td_values

                    # Check for lecturer change or new section
                    new_lecturer = td_values[8]
                    if new_lecturer:
                        # Get existing lecturer for this section if it exists
                        existing_sections = (
                            COURSE_DATA.get(course_id, {})
                            .get("sections", {})
                            .get(term, {})
                        )
                        existing_lecturer = None
                        if section_key in existing_sections:
                            existing_lecturer = existing_sections[section_key][8]

                        # if existing_lecturer != new_lecturer:
                        #     sync_lecturer_rating(new_lecturer)

                    try:
                        num_credits = float(td_values[-3])
                    except Exception as e:
                        num_credits = None

                course_id = course_id.replace("\u00a0", " ")
                if course_id not in COURSE_DATA.keys():
                    logger.info(f"New Course Found: {course_id}")
                    # fetch individual course details
                    course_obj = get_individual_course(course_id)

                    # process description with ai model
                    course_returns = process_single_description(course_obj["desc"])
                    course_obj.update(course_returns)

                    if course_obj["title"] in ("Unkown", ""):
                        course_obj["title"] = header
                    course_obj["sections"] = {}
                    course_obj["sections"][term] = sections
                    COURSE_DATA[course_id] = course_obj
                elif "sections" not in COURSE_DATA[course_id].keys():
                    COURSE_DATA[course_id]["sections"] = {}

                if (
                    honors_sections
                    and term in COURSE_DATA[course_id]["sections"].keys()
                ):
                    COURSE_DATA[course_id]["sections"][term].update(sections)
                else:
                    COURSE_DATA[course_id]["sections"][term] = sections

                if COURSE_DATA[course_id]["title"] in ("Unkown", ""):
                    COURSE_DATA[course_id]["title"] = header

                COURSE_DATA[course_id]["credits"] = num_credits

                if not COURSE_DATA[course_id]["sections"]:
                    logger.warning(f"{course_id} has no sections")

    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return None


def run_parser(scraped_data: Dict[str, Any], term: str) -> None:
    """Run the parser to extract sections from scraped data dict"""
    logger.info("STEP 2: Running Section Parser")
    logger.info(f"Extracting sections from {len(scraped_data)} subjects...")

    for course_name, course_data in scraped_data.items():
        logger.debug(f"Processing {course_name}...")
        course_data = course_data[0]

        # If it's already a dict, look for HTML content in values
        for key, value in course_data.items():
            if isinstance(value, str) and ("<h4" in value):
                # extract sections from html content
                extract_sections_from_html(value, term)


# == SECTION END==


def scrape_undergrad_grad_catalog(url: str) -> None:
    """Scrape courses from a given URL"""
    try:
        logger.info(f"Scraping: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # print(response.content)
        soup = BeautifulSoup(response.content, "html.parser")
        courses = {}

        # Find all course blocks
        course_blocks = soup.find_all("div", class_="courseblock")

        for block in course_blocks:
            # Extract title from courseblocktitle
            title_elem = block.find("p", class_="courseblocktitle")
            title = title_elem.get_text(strip=True).replace("\u00a0", " ").split(".")

            # Extract description from courseblockdesc
            desc_elem = block.find("p", class_="courseblockdesc")
            description = (
                desc_elem.get_text(strip=True).replace("\u00a0", " ")
                if desc_elem
                else ""
            )

            course_code = title[0].strip()
            title = title[1].strip()

            if course_code in COURSE_DATA:
                course_obj = COURSE_DATA[course_code]
                if course_obj["title"] != title:
                    logger.info(
                        f"Title changed: {course_code} | Old: {course_obj['title']} | New: {title}"
                    )
                    course_obj["title"] = title
                elif course_obj["desc"] != description:
                    logger.info(f"Description changed for {course_code}")
                    course_obj["desc"] = description
                    # update existing course with ai data
                    course_returns = process_single_description(course_obj["desc"])
                    course_obj.update(course_returns)
            else:
                course_obj = {"title": title, "desc": description}
                # process new course description with ai
                course_returns = process_single_description(description)
                course_obj.update(course_returns)
            if "sections" not in course_obj.keys():
                course_obj["sections"] = {}
            COURSE_DATA[course_code] = course_obj

        logger.info(f"Found {len(COURSE_DATA)} courses")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")


def scrape_courses(
    term: str = "202610",
    output_file: str = None,
    catalog: bool = False,
    sections: bool = False,
):
    """
    Main logic for scraping NJIT course catalog and section information.
    """
    if not COURSE_DATA:
        logger.error("COURSE_DATA NOT LOADED!")
        return

    # If no flags are specified, run both scrapers.
    # If both flags are specified, run both.
    # Otherwise, run the specified scraper.
    run_catalog = not sections or catalog
    run_sections = not catalog or sections

    if sections and not catalog:
        run_catalog = False
    elif catalog and not sections:
        run_sections = False

    semester = semesters[term[-2:]]
    term_text = term[:-2] + " " + semester

    if run_catalog:
        logger.info("RUNNING CATALOG SCRAPER")
        for url in links:
            # scrape catalog page from url
            scrape_undergrad_grad_catalog(url)
        logger.info("Catalog scraping complete.")

    if run_sections:
        if not term:
            logger.error("Term is required when scraping sections.")
            return

        logger.info(f"RUNNING SECTIONS SCRAPER FOR TERM: {term_text}")
        # run scraper for course sections
        scraped_data = run_section_scraper(term)
        # parse scraped section data
        run_parser(scraped_data, term)
        logger.info("Section scraping and parsing complete.")

    # Save to JSON and Redis
    if run_catalog or run_sections:
        if output_file:
            with open(output_file, "w") as f:
                json.dump(COURSE_DATA, f, indent=4)
        else:
            set_redis_course_data(COURSE_DATA)
            # for now update the file too
            with open(COURSE_DATA_FILE, "w") as f:
                json.dump(CourseStructureModel(COURSE_DATA).model_dump(), f, indent=4)
    else:
        logger.warning(
            "No action performed. Use catalog=True, sections=True, or both=False to run."
        )


def main():
    """Scrape all links and save to JSON"""
    parser = argparse.ArgumentParser(
        description="Scrape NJIT course catalog and section information.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--term",
        type=str,
        default="202610",
        help="Term code to scrape sections for year(10 spring, 95 winter, 90 fall, 50 summer).\n"
        "Examples:\n"
        "  - 202610: Spring 2026\n"
        "  - 202590: Fall 2025\n"
        "  - 202550: Summer 2025",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=COURSE_DATA_FILE,
        help="Path to the output JSON file.",
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Only scrape the course catalog (descriptions, titles).",
    )
    parser.add_argument(
        "--sections",
        action="store_true",
        help="Only scrape course sections for the given term.",
    )

    args = parser.parse_args()

    scrape_courses(
        term=args.term,
        output_file=args.output,
        catalog=args.catalog,
        sections=args.sections,
    )


if __name__ == "__main__":
    if not COURSE_DATA:
        logger.error("COURSE_DATA NOT LOADED!")
        raise Exception("COURSE_DATA NOT LOADED!")
    main()
