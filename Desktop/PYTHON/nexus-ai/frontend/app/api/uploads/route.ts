import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://backend:8000";

/** Proxy POST /api/uploads → backend multipart upload */
export async function POST(req: NextRequest) {
  const token = cookies().get("access_token")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const formData = await req.formData();

  const upstream = await fetch(`${BACKEND}/api/v1/uploads/`, {
    method: "POST",
    // Do NOT set Content-Type — fetch sets the correct multipart boundary automatically.
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}

/** Proxy GET /api/uploads?page=N → backend paginated list */
export async function GET(req: NextRequest) {
  const token = cookies().get("access_token")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const page = searchParams.get("page") ?? "1";
  const perPage = searchParams.get("per_page") ?? "20";

  const upstream = await fetch(
    `${BACKEND}/api/v1/uploads?page=${page}&per_page=${perPage}`,
    { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" }
  );

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
