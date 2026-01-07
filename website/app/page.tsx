import HomeClient from "./components/HomeClient";
import { _COURSE_DATA, getCourseData } from "./constants";

export default async function Page() {
    const data = await getCourseData()
    return <HomeClient course_data={data} />;
}