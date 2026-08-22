const TIMEZONE = "Europe/Athens";
const START_HOUR = 17;
const END_HOUR = 19;
const DISPATCH_URL =
  "https://api.github.com/repos/xtzaferis/trading-signals/actions/" +
  "workflows/advisory-pages.yml/dispatches";

export function isTradingSession(timestamp) {
  const hour = Number(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: TIMEZONE,
      hour: "2-digit",
      hourCycle: "h23",
    }).format(new Date(timestamp)),
  );
  return hour >= START_HOUR && hour < END_HOUR;
}

export async function dispatchWorkflow(token, fetchImplementation = fetch) {
  if (!token) {
    throw new Error("GITHUB_TOKEN Cloudflare secret is not configured");
  }
  const response = await fetchImplementation(DISPATCH_URL, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2026-03-10",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`GitHub workflow dispatch failed (${response.status}): ${detail}`);
  }
  return response.status;
}

export default {
  async scheduled(controller, env, context) {
    if (!isTradingSession(controller.scheduledTime)) {
      console.log("Outside 17:00-19:00 Europe/Athens; dispatch skipped");
      return;
    }
    context.waitUntil(
      dispatchWorkflow(env.GITHUB_TOKEN).then((status) => {
        console.log(`Advisory workflow dispatched successfully (${status})`);
      }),
    );
  },

  async fetch() {
    return Response.json({
      status: "ok",
      purpose: "read-only advisory workflow scheduler",
      timezone: TIMEZONE,
      session: `${START_HOUR}:00-${END_HOUR}:00`,
    });
  },
};
