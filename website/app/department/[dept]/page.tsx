import HomeClient from "../../components/HomeClient";

function normalizeParam(value: string) {
    return decodeURIComponent(value).replace(/\+/g, " ").trim();
}

export default async function Page({ params }: { params: { dept: string } }) {
    const param = await params;
    const dept = normalizeParam(param.dept).toUpperCase();
    return <HomeClient initialSelectedDept={dept} />;
}
