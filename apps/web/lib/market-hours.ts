const ET_TIMEZONE = "America/New_York";
const MARKET_OPEN_MINUTES = 9 * 60 + 30;
const MARKET_CLOSE_MINUTES = 16 * 60;

type EtParts = {
  weekday: string;
  hour: number;
  minute: number;
};

function getEtParts(date: Date): EtParts {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: ET_TIMEZONE,
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = formatter.formatToParts(date);
  const lookup = (type: string) => parts.find((item) => item.type === type)?.value;
  return {
    weekday: lookup("weekday") ?? "",
    hour: Number.parseInt(lookup("hour") ?? "0", 10),
    minute: Number.parseInt(lookup("minute") ?? "0", 10),
  };
}

export function isUsMarketHours(date: Date = new Date()): boolean {
  const { weekday, hour, minute } = getEtParts(date);
  if (weekday === "Sat" || weekday === "Sun") {
    return false;
  }
  const totalMinutes = hour * 60 + minute;
  return totalMinutes >= MARKET_OPEN_MINUTES && totalMinutes < MARKET_CLOSE_MINUTES;
}

export function marketRefreshIntervalMs(date: Date = new Date()): number {
  return isUsMarketHours(date) ? 2 * 60 * 1000 : 15 * 60 * 1000;
}
