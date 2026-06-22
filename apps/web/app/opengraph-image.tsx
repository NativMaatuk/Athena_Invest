import { ImageResponse } from "next/og";

export const alt = "Athena Invest";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "56px 64px",
          background:
            "linear-gradient(145deg, rgb(15, 23, 42) 0%, rgb(15, 118, 110) 55%, rgb(14, 165, 233) 100%)",
          color: "white",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "14px",
            fontSize: "30px",
            fontWeight: 700,
            opacity: 0.95,
          }}
        >
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(255,255,255,0.16)",
              border: "1px solid rgba(255,255,255,0.35)",
              fontSize: "22px",
            }}
          >
            A
          </div>
          Athena Invest
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={{ fontSize: "66px", fontWeight: 800, lineHeight: 1.05 }}>
            Smart Stock Analysis
          </div>
          <div style={{ fontSize: "34px", fontWeight: 500, opacity: 0.92 }}>
            Fast insights, watchlists, and market signals
          </div>
        </div>
      </div>
    ),
    size
  );
}
