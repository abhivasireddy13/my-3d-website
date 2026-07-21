import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://backend:8000";

/**
 * GET /api/analytics/embed-token?dashboard_id={id}
 *
 * Proxy to backend GET /api/v1/analytics/embed-token.
 * Reads the httpOnly access_token cookie and forwards it as a Bearer token
 * so the Superset admin credentials never reach the browser.
 */
export async function GET(req: NextRequest) {
  const token = cookies().get("access_token")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const dashboardId = req.nextUrl.searchParams.get("dashboard_id");
  if (!dashboardId) {
    return NextResponse.json({ detail: "dashboard_id is required" }, { status: 400 });
  }

  try {
    const upstream = await fetch(
      `${BACKEND}/api/v1/analytics/embed-token?dashboard_id=${encodeURIComponent(dashboardId)}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }
    );

    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch (err) {
    console.error("[analytics/embed-token] Backend request failed:", err);
    return NextResponse.json(
      { detail: "Analytics service unavailable" },
      { status: 503 }
    );
  }
}
