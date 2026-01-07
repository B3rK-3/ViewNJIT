import HomeClient from "../components/HomeClient";
import { getCourseData } from "../constants";

function normalizeParam(value: string) {
    return decodeURIComponent(value).replace(/\+/g, " ").trim();
}

export default async function Page({
    searchParams,
}: {
    searchParams?: { search?: string };
}) {
    const searchParam = await searchParams;
    const search = searchParam?.search
        ? normalizeParam(searchParam.search)
        : "";
    const data = await getCourseData();
    return <HomeClient initialSearchQuery={search} course_data={data} />;
}
