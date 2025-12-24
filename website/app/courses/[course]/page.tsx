import HomeClient from "../../components/HomeClient";

function normalizeParam(value: string) {
    return decodeURIComponent(value).replace(/\+/g, " ").trim();
}

export default async function Page({ params }: { params: { course: string } }) {
    const param = await params;
    const course = normalizeParam(param.course).toUpperCase();
    return (
        <HomeClient
            initialSelectedCourse={course}
            initialInfoCourse={course}
            initialSearchQuery={course}
        />
    );
}
