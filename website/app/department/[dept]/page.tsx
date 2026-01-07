import HomeClient from "../../components/HomeClient";
import { getCourseData } from "../../constants";

function normalizeParam(value: string) {
    return decodeURIComponent(value).replace(/\+/g, " ").trim();
}

export default async function Page({ params }: { params: { dept: string } }) {
    const param = await params;
    const dept = normalizeParam(param.dept).toUpperCase();
    const data = await getCourseData();
    return <HomeClient initialSelectedDept={dept} course_data={data} />;
}
