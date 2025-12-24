import json
import os
import requests
import base64
import random
import time
from bs4 import BeautifulSoup


# ===== SECTION SCRAPER FUNCTIONS =====


def pb_encode(s):
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


def fetch_courses(subject, term="202610", max_results="100", offset="0"):
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
        print(f"HTTP Error: {e}")
        print(f"Response Body: {response.text}")
        return None


def run_section_scraper():
    """Run the section scraper to fetch course data from the API and return as dict"""
    print("=" * 60)
    print("STEP 1: Running Section Scraper")
    print("=" * 60)

    # Load subjects
    input_file = r"d:\Projects\NJIT_Course_FLOWCHART\data\NJITCourse4LetterAbbr.json"
    with open(input_file, "r") as f:
        subjects_list = json.load(f)

    final_data = {}

    for item in subjects_list:
        subj = item.get("SUBJECT")
        if subj:
            print(f"Fetching courses for {subj}...")
            # Fetch courses, increasing max results to capture all
            response_data = fetch_courses(subj, max_results="500")

            final_data[subj] = response_data

            time.sleep(0.2)

    print(f"✓ Section scraper complete. Fetched {len(final_data)} subjects\n")
    return final_data


# ===== MAIN PARSER FUNCTIONS =====


def extract_sections_from_html(html_content):
    """Extract all course sections from HTML content by finding h4 elements and their following tables"""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        sections_by_course = {}

        # Find all h4 elements (each represents a course)
        h4_elements = soup.find_all("h4")

        for h4 in h4_elements:
            # Extract id from h4
            course_id = h4.get("id")
            if not course_id:
                continue

            honors_sections = False

            header_split = h4.get_text(strip=True).replace(' - ', '-').replace(' -', '-').replace('- ', '-').split('-')
            header = header_split[1]
            if header_split[-1].lower() == 'honors':
                honors_sections = True

            # Find the next table after this h4
            current = h4.next_sibling
            table = None

            while current:
                if hasattr(current, "name"):
                    if current.name == "table":
                        table = current
                        break                       
                    elif current.name in [
                        "h4",
                        "h3",
                        "h2",
                    ]:  # Stop if we hit another heading
                        break
                current = current.next_sibling

            if table:
                # Extract sections from this table
                rows = table.find_all("tr")
                sections = {}

                # Skip the first row (header)
                for row in rows[1:]:
                    tds = row.find_all("td")

                        # Extract text from each td
                    td_values = []
                    for i, td in enumerate(tds):
                        # For links, extract the text content
                        if td.find("a"):
                            text = td.find("a").get_text(strip=True)
                        else:
                            text = td.get_text(strip=True)
                                                    # Special handling for rooms column (4th index, 0-based)
                        if (i == 4 or i == 3) and td.find("br"):
                            text = td.get_text(separator=", ", strip=True)
                        
                        td_values.append(text)
                        # First column is the section key
                        section_key = td_values[0]
                        sections[section_key] = td_values
                
                # print(header)
                if sections:
                    if honors_sections and course_id in sections_by_course.keys():
                        sections_by_course[course_id][1].update(sections)
                    else:
                        sections_by_course[course_id] = [header, sections]

        return sections_by_course if sections_by_course else None

    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return None


def save_sections(data, output_file):
    """Save sections data to JSON file"""
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)
    print(f"✓ Saved sections to {output_file}")


def run_parser(scraped_data):
    """Run the parser to extract sections from scraped data dict"""
    print("=" * 60)
    print("STEP 2: Running Section Parser")
    print("=" * 60)

    print(f"\nExtracting sections from {len(scraped_data)} subjects...\n")

    # Extract sections from the scraped data
    sections_data = {}

    for course_name, course_data in scraped_data.items():
        print(f"Processing {course_name}...")
        course_data = course_data[0]

        # If it's already a dict, look for HTML content in values
        for key, value in course_data.items():
            if isinstance(value, str) and ("<h4" in value):
                course_sections = extract_sections_from_html(value)
                if course_sections:
                    sections_data.update(course_sections)
                    break

    # Save sections to file
    if sections_data:
        output_file = "sections.json"
        save_sections(sections_data, output_file)
        print(f"\nSummary:")
        print(f"Total courses with sections: {len(sections_data)}")
    else:
        print("No sections tables found in the data.")

    return sections_data


if __name__ == "__main__":
    # Run section scraper first and get data as dict
    try:
        scraped_data = json.load(open('data/course_sections_parsed.json', 'r'))
    except Exception as e:
        scraped_data = run_section_scraper()

    # Then run parser with the scraped data
    final_sections = run_parser(scraped_data)

    print("\n" + "=" * 60)
    print("All processes complete!")
    print("=" * 60)
