# FlowNJIT

A comprehensive course prerequisite visualization and planning tool for New Jersey Institute of Technology (NJIT) students. This application helps students understand course dependencies, plan their academic path, and explore course relationships through an interactive graph visualization.

## Features

- **Interactive Course Graph**: Visualize course prerequisites and dependencies using an interactive flowchart powered by React Flow and ELK (Eclipse Layout Kernel)
- **Course Search**: Search and filter courses by department or keyword
- **Detailed Course Information**: View course descriptions, credits, prerequisites, corequisites, and restrictions
- **Department Navigation**: Browse courses by academic department
- **AI-Powered Prerequisite Parsing**: Uses Gemini AI to intelligently parse and structure prerequisite relationships
- **Vector Search**: Semantic course search using ChromaDB for finding related courses
- **Real-time Section Data**: Access current course section information including schedules, instructors, and availability

## Tech Stack

### Frontend
- **Next.js 16** (React 19) - Server-side rendering and routing
- **TypeScript** - Type-safe development
- **TailwindCSS** - Utility-first styling
- **React Flow** (@xyflow/react) - Interactive graph visualization
- **ELK.js** - Automatic graph layout algorithm

### Backend
- **Python** - Data processing and API server
- **ChromaDB** - Vector database for semantic search
- **SQLite** - Structured course and section data storage
- **BeautifulSoup** - Web scraping NJIT course data
- **Google Gemini API** - AI-powered prerequisite parsing

## Project Structure

```
├── backend/
│   └── server.py              # Python backend API server
├── data/
│   ├── njit_courses.json      # Raw course data
│   ├── course_sections_parsed.json
│   └── ...                    # Other data files
├── scrapers/
│   ├── scrape_course_prereqs.py    # Scrape prerequisite data
│   ├── scrape_course_sections.py   # Scrape section schedules
│   └── scrape_semester_courses.py  # Scrape semester offerings
├── prereq_ai/
│   ├── gemini_graph.py        # Gemini AI graph generation
│   └── chatgpt_graph.py       # Alternative ChatGPT integration
├── website/
│   ├── app/
│   │   ├── components/
│   │   │   ├── CourseGraph.tsx     # Graph visualization component
│   │   │   └── HomeClient.tsx      # Main client component
│   │   ├── courses/            # Course detail pages
│   │   ├── department/         # Department pages
│   │   └── page.tsx            # Home page
│   ├── package.json
│   └── tsconfig.json
├── chroma/                     # ChromaDB vector database
├── graph.json                  # Generated prerequisite graph
└── sections.json              # Course section data
```

## Installation

### Prerequisites
- Node.js 20+
- Python 3.8+
- npm or yarn

### Frontend Setup

1. Navigate to the website directory:
```bash
cd website
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Backend Setup

1. Install Python dependencies:
```bash
pip install chromadb beautifulsoup4 requests google-genai python-dotenv
```

2. Set up environment variables (for AI features):
```bash
# Create a .env file in the root directory
GEMINI_API_KEY=your_api_key_here
```

3. Run the backend server:
```bash
python backend/server.py
```

## Data Collection

### Scraping Course Data

The project includes several scrapers to collect course information from NJIT:

1. **Scrape Course Prerequisites**:
```bash
python scrapers/scrape_course_prereqs.py
```

2. **Scrape Course Sections**:
```bash
python scrapers/scrape_course_sections.py
```

3. **Scrape Semester Courses**:
```bash
python scrapers/scrape_semester_courses.py
```

### Generating Prerequisite Graph

Use AI to parse prerequisites and generate the course dependency graph:

```bash
python prereq_ai/gemini_graph.py
```

This script:
- Reads course data from `data/njit_courses.json`
- Uses Gemini AI to parse prerequisite text into structured format
- Generates `graph.json` with course relationships
- Handles complex prerequisite logic (AND/OR conditions)

## Usage

### Viewing Course Graph

1. Select a course from the sidebar or search for it
2. The graph will display the selected course and its prerequisite chain
3. Click on nodes to navigate to different courses
4. Use the minimap and controls to navigate large graphs

### Searching Courses

- Use the search bar to find courses by code or title
- Filter by department using the dropdown
- Click on any course in the list to view its graph

### Course Details

Click on a course to view:
- Course code and title
- Credit hours
- Full description
- Prerequisites and corequisites
- Enrollment restrictions
- Available sections with schedules

## Development

### Building for Production

```bash
cd website
npm run build
npm start
```

### Linting

```bash
npm run lint
```

## Database Schema

### SQLite - courses.db

**courses table**:
- course_id (PRIMARY KEY)
- code (course code, e.g., "CS 100")
- title
- credits
- desc (description)
- prereq_json (structured prerequisites)
- coreq_json (corequisites)
- restrictions_json

**sections table**:
- term
- course_id
- crn (Course Reference Number)
- days_mask (encoded class days)
- start_min/end_min (class times)
- location, status, max, now (enrollment)
- instructor, delivery_mode, credits, comments

### ChromaDB

Used for semantic search of course descriptions and content, enabling natural language queries to find related courses.

## Graph Visualization

The course graph uses a hierarchical layout algorithm (ELK) to automatically position courses:
- **Top nodes**: Advanced courses
- **Bottom nodes**: Prerequisite courses
- **Edges**: Prerequisite relationships
- **Colors**: Different departments and course levels

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is for educational purposes. Course data belongs to New Jersey Institute of Technology.

## Acknowledgments

- NJIT for providing course catalog data
- React Flow for graph visualization
- Google Gemini for AI-powered parsing
- ChromaDB for vector search capabilities
