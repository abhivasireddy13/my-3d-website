import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://backend:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: { jobId: string } }
) {
  const token = cookies().get("access_token")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  try {
    const upstream = await fetch(
      `${BACKEND}/api/v1/admin/trace/${params.jobId}`,
      { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" }
    );
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Admin service unavailable" }, { status: 503 });
  }
}
