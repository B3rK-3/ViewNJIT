import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

links = [
    "https://catalog.njit.edu/graduate/computing-sciences/#coursestext",
    "https://catalog.njit.edu/graduate/architecture-design/#coursestext",
    "https://catalog.njit.edu/graduate/science-liberal-arts/#coursestext",
    "https://catalog.njit.edu/graduate/newark-college-engineering/#coursestext",
    "https://catalog.njit.edu/graduate/management/#coursestext"
]
# [
#     "https://catalog.njit.edu/undergraduate/computing-sciences/#coursestext",
#     "https://catalog.njit.edu/undergraduate/architecture-design/#coursestext",
#     "https://catalog.njit.edu/undergraduate/science-liberal-arts/#coursestext",
#     "https://catalog.njit.edu/undergraduate/newark-college-engineering/#coursestext",
#     "https://catalog.njit.edu/undergraduate/management/#coursestext"
# ]


def scrape_courses(url):
    """Scrape courses from a given URL"""
    try:
        print(f"Scraping: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # print(response.content)
        soup = BeautifulSoup(response.content, 'html.parser')
        courses = []
        
        # Find all course blocks
        course_blocks = soup.find_all('div', class_='courseblock')
        
        for block in course_blocks:
            # Extract title from courseblocktitle
            title_elem = block.find('p', class_='courseblocktitle')
            if title_elem:
                strong = title_elem.find('strong')
                title = strong.get_text(strip=True) if strong else ""
            else:
                title = ""
            
            # Extract description from courseblockdesc
            desc_elem = block.find('p', class_='courseblockdesc')
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            if title and description:
                courses.append({
                    "course": title,
                    "desc": description
                })
        
        print(f"✓ Found {len(courses)} courses")
        return courses
    
    except Exception as e:
        print(f"✗ Error scraping {url}: {e}")
        return []


def main():
    """Scrape all links and save to JSON"""
    all_courses = {}
    
    for url in links:
        # Extract department name from URL
        dept_name = url.split('/')[4].replace('-', ' ').title()
        
        courses = scrape_courses(url)
        if courses:
            all_courses[dept_name] = courses
    
    # Save to JSON
    output_file = r"d:\Projects\NJIT_Course_FLOWCHART\scraped_courses.json"
    with open(output_file, 'w') as f:
        json.dump(all_courses, f, indent=4)
    
    print(f"\n✓ Saved {sum(len(v) for v in all_courses.values())} courses to {output_file}")


if __name__ == "__main__":
    main()
