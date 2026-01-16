from typing import List, Dict, Union, Optional, Literal, Tuple, Any, Annotated
from pydantic import BaseModel, RootModel, ConfigDict, Field

TERMS = Literal["202610", "202595", "202590", "202550", "202510"]


#### ---- COURSE DATA SCHEMA - BEGIN ------ ####
PermittedGrades = Literal["A", "B+", "B", "C+", "C", "C-", "F"]
StandingsLiteral = Literal["FRESHMAN", "SOPHOMORE", "JUNIOR", "SENIOR", "GRAD"]
# SectionsEntries = [Section,CRN,Days [Monday-M, Tuesday-T, Wednesday-W, Thursday-R, Friday-F]+,Times,Location,Status,	Max,Now,Instructor,Delivery Mode,Credits,Info,Comments]

SectionEntries = Tuple[str, str, str, str, str, str, str, str, str, str, str, str, str]
SectionInfo = Dict[str, SectionEntries]


PlacementKind = Literal[
    "PLACEMENT_INTO_COURSE",
    "PLACEMENT_ABOVE_COURSE",
    "PLACEMENT_TEST_REQUIRED",
    "SCORE_THRESHOLD",
    "DIAGNOSTIC",
    "UNKNOWN",
]

PermissionKind = Literal[
    "INSTRUCTOR_APPROVAL",
    "ADVISOR_APPROVAL",
    "DEPARTMENT_APPROVAL",
    "SCHOOL_APPROVAL",
    "PROGRAM_APPROVAL",
    "ADMIN_OVERRIDE",
    "UNKNOWN",
]

PermissionAuthority = Literal[
    "INSTRUCTOR",
    "FACULTY_SUPERVISOR",
    "DEPARTMENT",
    "SCHOOL",
    "PROGRAM",
    "ADVISOR",
    "REGISTRAR",
    "UNKNOWN",
]

PermissionAction = Literal[
    "APPROVAL_REQUIRED",
    "SIGNATURE_REQUIRED",
    "PROPOSAL_APPROVAL",
    "APPLICATION_REQUIRED",
    "OVERRIDE_REQUIRED",
    "UNKNOWN",
]

RestrictionKind = Literal[
    "MAJOR_ONLY",
    "PROGRAM_ONLY",
    "CLASS_STANDING_ONLY",
    "CAMPUS_ONLY",
    "COLLEGE_ONLY",
    "INSTRUCTOR_PERMISSION",
    "DEPARTMENT_PERMISSION",
    "ADVISOR_PERMISSION",
    "NOT_FOR_MAJOR",
    "NOT_FOR_PROGRAM",
    "NO_CREDIT_IF_TAKEN",
    "REPEAT_LIMIT",
    "CROSS_LISTED",
    "TIME_CONFLICT_RULE",
    "PRIOR_CREDIT_EXCLUSION",
    "PROGRAM_APPROVAL",
    "OTHER",
]


class AndOrNodeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["AND", "OR"]
    children: List["NodesModel"]


class CourseNodeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["COURSE"]
    course: str
    min_grade: Optional[PermittedGrades] = None


class PlacementNodeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["PLACEMENT"]
    name: str
    placement_kind: Optional[PlacementKind] = None
    subject: Optional[str] = None
    exam: Optional[str] = None
    min_course: Optional[str] = None
    level: Optional[str] = None
    min_score: Optional[Union[float, str]] = None


class PermissionNodeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["PERMISSION"]
    raw: str
    permission_kind: Optional[PermissionKind] = None
    authority: Optional[PermissionAuthority] = None
    action: Optional[PermissionAction] = None
    artifact: Optional[List[str]] = None


class StandingNodeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["STANDING"]
    standing: str
    normalized: StandingsLiteral
    semesters_left: Optional[int] = None


class SkillNodeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["SKILL"]
    name: str


class EquivalentNodeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["EQUIVALENT"]
    courses: List[str]


NodesModel = Annotated[
    Union[
        AndOrNodeModel,
        CourseNodeModel,
        PlacementNodeModel,
        PermissionNodeModel,
        StandingNodeModel,
        SkillNodeModel,
        EquivalentNodeModel,
    ],
    Field(discriminator="type"),  # <--- Critical for Gemini to pick the right one
]
AndOrNodeModel.model_rebuild()


class RestrictionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw: str
    kinds: Optional[List[RestrictionKind]] = None
    entities: Optional[List[str]] = None


class CourseInfoModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # fixed: added defaults for all trees and optional data
    prereq_tree: Optional[AndOrNodeModel]
    coreq_tree: Optional[AndOrNodeModel]
    restrictions: List[RestrictionModel]
    desc: str
    title: str
    credits: Optional[Union[float, None]] = None
    sections: Dict[str, SectionInfo]


CourseDataType = Dict[str, CourseInfoModel]


class CourseStructureModel(RootModel[CourseDataType]):
    pass


#### ---- COURSE DATA SCHEMA - END ------ ####


#### ---- TYPES - BEGIN ---- ####
class LecturerRating(BaseModel):
    model_config = ConfigDict(extra="allow")
    avgRating: str
    wouldTakeAgainPercent: str
    avgDifficulty: str
    link: str
    numRatings: str
    legacyId: int


LecturerRatingType = Dict[str, LecturerRating]


class LecturerStructureModel(RootModel[LecturerRatingType]):
    pass


class CourseQueryFormat(BaseModel):
    model_config = {"extra": "forbid"}

    query: str = Field(
        description="Natural language description of the course(s) the user is searching for."
    )

    top_n: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of courses to return, ordered by relevance.",
    )

    only_prereqs_fulfilled: bool = Field(
        default=True,
        description=(
            "If true, returns only courses for which the user satisfies all prerequisites. "
            "If false, returns all relevant courses regardless of prerequisites."
        ),
    )

    only_current_semester: bool = Field(
        default=True,
        description=(
            "If true, only looks at courses offered in current semester."
            "If false, looks at all courses."
        ),
    )


class UserCourseInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        description="Name of the course. If course is not valid, will return an error.",
    )
    grade: PermittedGrades = Field(
        default="C",
        description="Grade recieved in course. A pass is a 'C'. Example: 'I passed a class', then grade = 'C'.",
    )


class UserFulfilled(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_user: bool = True
    courses: Dict[str, UserCourseInfo] = {}
    equivalents: List[str] = []
    standing: Optional[StandingsLiteral] = None
    semesters_left: Optional[int] = None
    honors: bool = False


class RemoveFromUserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    courses: List[str] = Field(
        default_factory=list,
        description="List of courses to remove.",
    )
    equivalents: List[str] = Field(
        default_factory=list,
        description="List of courses equivalents to remove.",
    )
    standing: Optional[bool] = Field(
        default=False,
        description="Whether to remove standing from profile.",
    )
    semesters_left: Optional[bool] = Field(
        default=False, description="Whether to remove semesters_left from profile."
    )


class UpdateUserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    courses: List[UserCourseInfo] = Field(
        default_factory=list,
        description="List of completed or in-progress courses the user has taken.",
    )
    equivalents: List[str] = Field(
        default_factory=list,
        description="List of courses that the user has equivalents for. Example: Example: I have equivalent for CS 350 -> equivalents = [CS 350].",
    )
    standing: Optional[StandingsLiteral] = Field(
        default=None,
        description="User's academic standing (FRESHMAN, SOPHOMORE, JUNIOR, SENIOR, GRAD).",
    )
    semesters_left: Optional[int] = Field(
        default=None, description="Number of semesters remaining until graduation."
    )
    honors: bool = Field(
        default=False,
        description="True if student is honors false if not. excludes honors courses",
    )
    to_remove: Optional[RemoveFromUserProfile] = Field(
        default=None,
        description="Removes stuff from profile.",  # TODO: change stuff
    )


class CourseSearchFormat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_name: str


class MakeScheduleFormat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    courses: List[str] = Field(
        description="List of course names to include in the schedule."
    )
    max_days: int = Field(
        ge=1,
        le=5,
        default=5,
        description="Maximum number of days per week the user wants to attend classes (1-5).",
    )
    locked_in_sections: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Dictionary where keys are course names and values are lists of section numbers (strings) to lock in. Only these sections will be considered for the respective courses.",
    )
    min_rmp_rating: Optional[float] = Field(
        default=0,
        description="Minimum RateMyProfessors rating (0.0 - 5.0) required for instructors. Sections with instructors below this rating will be excluded.",
    )
    days: Optional[List[str]] = Field(
        default=None,
        description="List of specific days (e.g., ['Monday', 'Wednesday']) the user wants to attend classes. Only sections meeting on these days will be included.",
    )
    honors: bool = Field(
        default=False,
        description="True if student is honors false if not. excludes honors courses",
    )


class CourseMetadata(BaseModel):
    title: str
    description: str
    hash: str


#### ---- TYPES - END ---- ####


#### ---- BACKEND REQUEST & RESPONSE SCHEMAS - BEGIN ----- #####


# - REQUESTS - #
class ChatRequest(BaseModel):
    sessionID: str
    query: str
    term: TERMS
    attachments: Optional[List[str]] = None


class ProfsRequest(BaseModel):
    profs: list[str]


# - RESPONSES - #


class ChatResponse(BaseModel):
    response: str


class StreamChunk(BaseModel):
    type: Literal["text", "schedule"]
    content: Any


ProfsResponse = Dict[str, Union[LecturerRating, None]]

#### ---- BACKEND REQUEST & RESPONSE SCHEMAS - END ----- #####
