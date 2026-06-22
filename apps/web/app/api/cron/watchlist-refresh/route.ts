export async function GET(request: Request) {
  const authHeader = request.headers.get("authorization");
  const cronSecret = process.env.CRON_SECRET;
  if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
    return new Response("Unauthorized", { status: 401 });
  }

  const targetBase = process.env.API_CRON_TARGET_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!targetBase) {
    return Response.json(
      { ok: false, message: "Missing API_CRON_TARGET_BASE_URL or NEXT_PUBLIC_API_BASE_URL" },
      { status: 500 },
    );
  }

  const response = await fetch(`${targetBase}/api/v1/watchlist/refresh`, {
    method: "POST",
    cache: "no-store",
  });
  const body = await response.text();
  if (!response.ok) {
    return Response.json(
      { ok: false, status: response.status, body },
      { status: 502 },
    );
  }
  let parsed: unknown = body;
  try {
    parsed = body ? JSON.parse(body) : null;
  } catch {
    // keep raw body for observability
  }
  return Response.json({ ok: true, upstream: parsed });
}
