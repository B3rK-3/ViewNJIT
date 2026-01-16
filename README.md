# FlowNJIT.com

A comprehensive course prerequisite visualization and planning tool for New Jersey Institute of Technology (NJIT) students. This application helps students understand course dependencies, plan their academic path, and explore course relationships through an interactive graph visualization.

## Features

-   **Interactive Course Graph**: Visualize course prerequisites and dependencies using an interactive flowchart powered by React Flow and ELK.
-   **AI-Powered Prerequisite Parsing**: Uses Gemini AI to intelligently parse and structure complex prerequisite relationships into a searchable graph.
-   **Real-time Section Data**: Access live course section information, schedules, and seat availability synchronized from NJIT's systems.
-   **Professor Ratings Integration**: Direct integration with RateMyProfessors ratings, displayed directly within the section details for informed course selection.
-   **Semantic Course Search**: AI-powered semantic search using ChromaDB and Cross-Encoders to find relevant courses beyond simple keyword matching.
-   **High-Performance Caching**: Redis-backed data layer for instant access to course details and lecturer ratings.
-   **Automated Background Scrapers**: Self-maintaining data pipeline that automatically refreshes section data and professor ratings in the background.

## Tech Stack

### Frontend

-   **Next.js** (React 19) - Performance-optimized server-side rendering
-   **TypeScript** - Robust type-safe development
-   **TailwindCSS** - Modern, responsive styling
-   **React Flow** - Dynamic graph visualization and interaction
-   **ELK.js** - Advanced automated graph layout engine

### Backend

-   **FastAPI / Python** - High-speed asynchronous API server
-   **Redis** - Primary high-performance cache for course and lecturer data
-   **ChromaDB** - Vector database for semantic course search
-   **SQLite** - Local structured data persistence
-   **Google Gemini API** - LLM-powered prerequisite and description parsing
-   **Sentence-Transformers** - Local vector embedding and cross-encoder reranking

## Project Structure

```
├── backend/
│   ├── constants.py           # Centralized project constants, schemas, and paths
│   ├── functions.py           # Core utility functions and database initializers
│   ├── server.py              # FastAPI application and endpoint definitions
│   ├── scrapers/              # Automated data collection pipeline
│   │   ├── courses.py         # Course catalog and section scraper
│   │   ├── rmp.py             # RateMyProfessors data synchronization
│   │   └── constants.py       # Scraper-specific settings and logging config
│   └── data/                  # Local JSON data snapshots
├── website/                   # Next.js frontend application
│   ├── app/
│   │   ├── components/        # React components (Graph, Sidebar, Popovers)
│   │   ├── dept/              # Department-based routing
│   │   │   ├── all/           # Displays all departments/courses
│   │   │   ├── [dept]/        # Department-specific view
│   │   │   └── [dept]/[course]# Course-specific view
│   │   └── page.tsx           # Interactive home page (same as dept/all)
└── chromadb/                  # Local vector search index
```

## Installation

### Prerequisites

-   Node.js 20+
-   Python 3.12+
-   Redis Server (running on localhost:6379)

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

### Backend Setup

1. Install Python dependencies:
    ```bash
    pip install fastapi uvicorn redis chromadb sentence-transformers requests beautifulsoup4 google-genai python-dotenv
    ```
2. Set up your `.env` in the `backend/` directory:
    ```env
    GEMINI_API_KEY=your_key_here
    ```
3. Run the backend server:
    ```bash
    python -m backend
    ```

## Background Operations

### Data Scrapers

The backend automatically starts background scrapers upon initialization:

-   **Course Scraper**: Periodically crawls the NJIT catalog and registration systems, updating the local JSON and Redis cache.
-   **Lectorer Scraper**: Periodically refreshes professor ratings from a proxy API, ensuring current student feedback is always available.
-   **Logging**: All background activities are logged to `backend/logs/scrapers.log` for easy monitoring.

### Manual Scraper Execution

You can also run scrapers manually for specific terms:

```bash
python -m backend.scrapers.courses --term 202610 --catalog --sections
```

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

Educational purpose only. Course data property of NJIT.
