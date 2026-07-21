import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://backend:8000";

/**
 * GET /api/predictions?upload_job_id=...&limit=...
 *
 * Proxy to GET /api/v1/predictions/ on the backend.
 * Forwards the httpOnly access_token cookie as a Bearer token.
 */
export async function GET(req: NextRequest) {
  const token = cookies().get("access_token")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const search = req.nextUrl.search; // preserve ?upload_job_id=...&limit=... as-is
  try {
    const upstream = await fetch(
      `${BACKEND}/api/v1/predictions/${search}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }
    );
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch (err) {
    console.error("[api/predictions] Backend request failed:", err);
    return NextResponse.json(
      { detail: "Predictions service unavailable" },
      { status: 503 }
    );
  }
}
