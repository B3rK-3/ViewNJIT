import HomeClient from "../../../components/HomeClient";
import { getCourseData } from "../../../constants";

function normalizeParam(value: string) {
    return decodeURIComponent(value).replace(/\+/g, " ").trim();
}

export default async function Page({
    params,
}: {
    params: { dept: string; course: string };
}) {
    const param = await params;
    const dept = normalizeParam(param.dept).toUpperCase();
    const course = normalizeParam(param.course).toUpperCase();
    const data = await getCourseData();
    return (
        <HomeClient
            initialSelectedDept={dept}
            initialSelectedCourse={course}
            initialInfoCourse={course}
            initialSearchQuery={course}
            course_data={data}
        />
    );
}
