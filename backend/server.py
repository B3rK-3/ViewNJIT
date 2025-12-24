from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.utils import embedding_functions

# ----------------------------
# 1) SQLite (structured store)
# ----------------------------

def init_sqlite(db_path: str = "courses.db") -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        course_id TEXT PRIMARY KEY,
        code TEXT NOT NULL,
        title TEXT,
        credits INTEGER,
        desc TEXT,
        prereq_json TEXT,
        coreq_json TEXT,
        restrictions_json TEXT
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS sections (
        term TEXT NOT NULL,
        course_id TEXT NOT NULL,
        crn TEXT NOT NULL,
        days_mask INTEGER,
        start_min INTEGER,
        end_min INTEGER,
        location TEXT,
        status TEXT,
        max INTEGER,
        now INTEGER,
        instructor TEXT,
        delivery_mode TEXT,
        credits INTEGER,
        comments TEXT,
        PRIMARY KEY (term, crn)
    )
    """)
    con.commit()
    return con

def upsert_course(con: sqlite3.Connection, course: Dict[str, Any]) -> None:
    con.execute("""
    INSERT INTO courses(course_id, code, title, credits, desc, prereq_json, coreq_json, restrictions_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(course_id) DO UPDATE SET
        code=excluded.code,
        title=excluded.title,
        credits=excluded.credits,
        desc=excluded.desc,
        prereq_json=excluded.prereq_json,
        coreq_json=excluded.coreq_json,
        restrictions_json=excluded.restrictions_json
    """, (
        course["course_id"],
        course["code"],
        course.get("title"),
        course.get("credits"),
        course.get("desc"),
        json.dumps(course.get("prereq_tree")),
        json.dumps(course.get("coreq_tree")),
        json.dumps(course.get("restrictions", [])),
    ))
    con.commit()

def insert_section(con: sqlite3.Connection, section: Dict[str, Any]) -> None:
    con.execute("""
    INSERT OR REPLACE INTO sections(
        term, course_id, crn, days_mask, start_min, end_min, location,
        status, max, now, instructor, delivery_mode, credits, comments
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        section["term"], section["course_id"], section["crn"],
        section.get("days_mask"), section.get("start_min"), section.get("end_min"),
        section.get("location"), section.get("status"),
        section.get("max"), section.get("now"),
        section.get("instructor"), section.get("delivery_mode"),
        section.get("credits"), section.get("comments", "")
    ))
    con.commit()

def get_sections(con: sqlite3.Connection, term: str, course_id: str, open_only: bool = False) -> List[Dict[str, Any]]:
    q = """
    SELECT term, course_id, crn, days_mask, start_min, end_min, location,
           status, max, now, instructor, delivery_mode, credits, comments
    FROM sections
    WHERE term=? AND course_id=?
    """
    params = [term, course_id]
    if open_only:
        q += " AND status='Open'"
    rows = con.execute(q, params).fetchall()
    cols = [d[0] for d in con.execute("PRAGMA table_info(sections)").fetchall()]  # not ideal; ok for demo
    # better: hardcode column names; keeping demo short
    out = []
    for r in rows:
        out.append({
            "term": r[0], "course_id": r[1], "crn": r[2],
            "days_mask": r[3], "start_min": r[4], "end_min": r[5],
            "location": r[6], "status": r[7], "max": r[8], "now": r[9],
            "instructor": r[10], "delivery_mode": r[11], "credits": r[12],
            "comments": r[13]
        })
    return out

# --------------------------------
# 2) Chroma (semantic course search)
# --------------------------------

def init_chroma(path: str = "./chroma") -> chromadb.Collection:
    client = chromadb.PersistentClient(path=path)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_or_create_collection(
        name="courses",
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

def course_doc(course: Dict[str, Any]) -> str:
    # what you embed
    prereq_text = json.dumps(course.get("prereq_tree"), ensure_ascii=False)
    restr_text = "; ".join(course.get("restrictions", []))
    return (
        f'{course["code"]} — {course.get("title","")}\n'
        f'Credits: {course.get("credits","")}\n'
        f'Description: {course.get("desc","")}\n'
        f'Prereqs: {prereq_text}\n'
        f'Restrictions: {restr_text}\n'
    )

def upsert_course_to_chroma(col: chromadb.Collection, course: Dict[str, Any]) -> None:
    meta = {
        "code": course["code"],
        "subject": course["code"].split()[0],
        "number": course["code"].split()[1],
        "credits": course.get("credits", None),
    }
    col.upsert(
        ids=[course["course_id"]],
        documents=[course_doc(course)],
        metadatas=[meta]
    )

# ----------------------------
# 3) Eligibility evaluation
# ----------------------------

GRADE_ORDER = {
    "A+": 13, "A": 12, "A-": 11,
    "B+": 10, "B": 9,  "B-": 8,
    "C+": 7,  "C": 6,  "C-": 5,
    "D+": 4,  "D": 3,  "D-": 2,
    "F": 0
}

def grade_meets(actual: str, required: str) -> bool:
    return GRADE_ORDER.get(actual, -1) >= GRADE_ORDER.get(required, 999)

def eval_prereq(node: Any, student: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Returns (ok, reasons_if_not_ok)
    Node schema:
      - {"type":"AND","children":[...]}
      - {"type":"OR","children":[...]}
      - {"type":"COURSE","course":"MATH 112","min_grade":"C"(optional)}
      - {"type":"PLACEMENT","name":"NJIT placement"}
      - raw string "MATH 112" (treated as COURSE)
    """
    if node is None:
        return True, []

    # raw string => COURSE
    if isinstance(node, str):
        node = {"type": "COURSE", "course": node}

    t = node.get("type")

    if t == "COURSE":
        course = node["course"]
        req_grade = node.get("min_grade")
        taken = student.get("taken", {})
        if course not in taken:
            return False, [f"Missing {course}"]
        if req_grade and not grade_meets(taken[course], req_grade):
            return False, [f"{course} requires grade {req_grade} or better (you have {taken[course]})"]
        return True, []

    if t == "PLACEMENT":
        name = node.get("name", "placement")
        ok = bool(student.get("placement", {}).get(name, False))
        return (ok, [] if ok else [f"Missing {name}"])

    if t == "AND":
        reasons = []
        for ch in node.get("children", []):
            ok, r = eval_prereq(ch, student)
            if not ok:
                reasons.extend(r)
        return (len(reasons) == 0, reasons)

    if t == "OR":
        all_reasons = []
        for ch in node.get("children", []):
            ok, r = eval_prereq(ch, student)
            if ok:
                return True, []
            all_reasons.append(r)
        # Show smallest explanation set (most helpful)
        smallest = min(all_reasons, key=len) if all_reasons else [["No options satisfied"]]
        return False, smallest

    return False, [f"Unknown prereq node type: {t}"]

def violates_restrictions(restrictions: List[str], student: Dict[str, Any]) -> Tuple[bool, List[str]]:
    reasons = []
    majors = set(m.lower() for m in student.get("majors", []))

    for r in restrictions:
        # Very simple parser for demo: "Not Engineering major"
        if r.lower().startswith("not ") and r.lower().endswith(" major"):
            blocked = r[4:-6].strip().lower()  # "engineering"
            if blocked in majors:
                reasons.append(f"Restriction violated: {r}")
    return (len(reasons) > 0, reasons)

# ----------------------------
# 4) End-to-end query examples
# ----------------------------

def search_and_filter(
    con: sqlite3.Connection,
    col: chromadb.Collection,
    query: str,
    term: str,
    student: Dict[str, Any],
    only_eligible: bool = True,
    k: int = 8
) -> List[Dict[str, Any]]:
    res = col.query(query_texts=[query], n_results=k)
    ids = res["ids"][0]  # course_ids

    out = []
    for cid in ids:
        row = con.execute("SELECT course_id, code, title, credits, desc, prereq_json, restrictions_json FROM courses WHERE course_id=?",
                          (cid,)).fetchone()
        if not row:
            continue

        prereq_tree = json.loads(row[5]) if row[5] else None
        restrictions = json.loads(row[6]) if row[6] else []

        # Must have sections in that term to be relevant for scheduling
        has_sections = con.execute("SELECT 1 FROM sections WHERE term=? AND course_id=? LIMIT 1", (term, cid)).fetchone() is not None
        if not has_sections:
            continue

        ok_pr, pr_reasons = eval_prereq(prereq_tree, student)
        violated, restr_reasons = violates_restrictions(restrictions, student)

        eligible = ok_pr and not violated
        if only_eligible and not eligible:
            continue

        out.append({
            "course_id": cid,
            "code": row[1],
            "title": row[2],
            "credits": row[3],
            "eligible": eligible,
            "why_not": pr_reasons + restr_reasons
        })

    return out

def demo():
    con = init_sqlite("courses.db")
    col = init_chroma("./chroma")

    # --- Insert ONE course: PHYS 234 (example)
    phys234 = {
        "course_id": "NJIT:PHYS:234",
        "code": "PHYS 234",
        "title": "Physics II",
        "credits": 3,
        "desc": "Prerequisites: PHYS 121/PHYS 121A or PHYS 122/PHYS 121A and MATH 112 with a grade of C or better.",
        "prereq_tree": {
            "type": "AND",
            "children": [
                {
                    "type": "OR",
                    "children": [
                        { "type": "AND", "children": [
                            { "type": "COURSE", "course": "PHYS 121" },
                            { "type": "COURSE", "course": "PHYS 121A" }
                        ]},
                        { "type": "AND", "children": [
                            { "type": "COURSE", "course": "PHYS 122" },
                            { "type": "COURSE", "course": "PHYS 121A" }
                        ]}
                    ]
                },
                { "type": "COURSE", "course": "MATH 112", "min_grade": "C" }
            ]
        },
        "restrictions": [],
        "coreq_tree": None
    }

    upsert_course(con, phys234)
    upsert_course_to_chroma(col, phys234)

    # --- Insert a section for PHYS 234 in term 202610
    insert_section(con, {
        "term": "202610",
        "course_id": "NJIT:PHYS:234",
        "crn": "55555",
        "days_mask": 4,       # Wed
        "start_min": 600,     # 10:00
        "end_min": 675,       # 11:15
        "location": "CULM 123",
        "status": "Open",
        "max": 30,
        "now": 22,
        "instructor": "Smith",
        "delivery_mode": "In Person",
        "credits": 3,
        "comments": ""
    })

    # --- Student example
    student = {
        "taken": {"PHYS 121": "B", "PHYS 121A": "A", "MATH 112": "C-"},
        "placement": {"NJIT placement": False},
        "majors": ["Engineering"]
    }

    # 1) Semantic search + eligibility filter
    results = search_and_filter(con, col, query="waves optics physics", term="202610", student=student, only_eligible=False)
    print("\nSearch results (including ineligible):")
    for r in results:
        print(r)

    # 2) Show sections for a course
    secs = get_sections(con, term="202610", course_id="NJIT:PHYS:234", open_only=True)
    print("\nOpen sections for PHYS 234:")
    for s in secs:
        print(s)

if __name__ == "__main__":
    demo()
