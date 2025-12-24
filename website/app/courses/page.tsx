import HomeClient from "../components/HomeClient";

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
    return <HomeClient initialSearchQuery={search} />;
}
