import HomeClient from "../../components/HomeClient";
import { getCourseData } from "../../constants";

function normalizeParam(value: string) {
    return decodeURIComponent(value).replace(/\+/g, " ").trim();
}

export default async function Page({
    params,
    searchParams,
}: {
    params: { dept: string };
    searchParams?: { search?: string };
}) {
    const [param, searchParam] = await Promise.all([params, searchParams]);
    let dept = normalizeParam(param.dept).toUpperCase();
    const search = searchParam?.search
        ? normalizeParam(searchParam.search)
        : "";
    const data = await getCourseData();
    return (
        <HomeClient
            initialSelectedDept={dept}
            initialSearchQuery={search}
            course_data={data}
        />
    );
}
