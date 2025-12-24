import requests
import base64
import random
import json
import time

def pb_encode(s):
    """
    Encodes a string using the Ellucian Page Builder obfuscation:
    Base64(Random_Integer_String) + Base64(Target_String)
    """
    # 1. Generate a random salt (usually a 2-digit number)
    salt = str(random.randint(10, 99))
    
    # 2. Base64 encode the salt and the actual string
    salt_b64 = base64.b64encode(salt.encode('utf-8')).decode('utf-8')
    val_b64 = base64.b64encode(s.encode('utf-8')).decode('utf-8')
    
    # 3. Concatenate them
    return salt_b64 + val_b64

def fetch_courses(subject, term="202610", max_results="100", offset="0"):
    url = "https://generalssb-prod.ec.njit.edu/BannerExtensibility/internalPb/virtualDomains.stuRegCrseSchedCourseNumbs"

    # Define the raw parameters we want to send
    raw_params = {
        "term": term,
        "subject": subject,
        "max": max_results,
        "offset": offset,
        "attr": ""  # Attribute is usually empty based on your logs
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
        "Referer": "https://generalssb-prod.ec.njit.edu/BannerExtensibility/customPage/page/stuRegCrseSched"
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

# --- Usage ---
if __name__ == "__main__":
    # Load subjects
    input_file = r"d:\Projects\NJIT_Course_FLOWCHART\NJITCourse4LetterAbbr.json"
    with open(input_file, 'r') as f:
        subjects_list = json.load(f)

    final_data = {}

    for item in subjects_list:
        subj = item.get("SUBJECT")
        if subj:
            print(f"Fetching courses for {subj}...")
            # Fetch courses, increasing max results to capture all
            response_data = fetch_courses(subj, max_results="500")
            
            if isinstance(response_data, list):
                # Extract the COURSE field
                courses = [row.get("COURSE") for row in response_data if "COURSE" in row]
                final_data[subj] = courses
            
            time.sleep(0.2)

    # Dump to JSON
    output_file = "njit_courses_output.json"
    with open(output_file, 'w') as f:
        json.dump(final_data, f, indent=4)
    
    print(f"Process complete. Data saved to {output_file}")