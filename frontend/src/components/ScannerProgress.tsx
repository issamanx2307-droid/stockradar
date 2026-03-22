export function ScannerProgress({ progress, done }: { progress: any; done: any }) {
  if (!progress && !done) return null
  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 1000,
      background: "var(--bg-elevated)", borderBottom: "1px solid var(--border)",
      padding: "8px 20px", display: "flex", alignItems: "center", gap: 14,
    }}>
      {progress && (
        <>
          <span style={{ fontSize: 12, color: "var(--accent)", whiteSpace: "nowrap" }}>
            ⚡ สแกน {progress.current}/{progress.total} หุ้น
          </span>
          <div style={{ flex: 1, height: 4, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{
              height: "100%", borderRadius: 2,
              background: "linear-gradient(90deg, var(--accent), var(--green))",
              width: `${progress.pct}%`, transition: "width 0.3s ease",
            }} />
          </div>
          <span style={{ fontSize: 11, color: "var(--green)", whiteSpace: "nowrap" }}>
            พบ {progress.found} สัญญาณ
          </span>
        </>
      )}
      {done && (
        <span style={{ fontSize: 12, color: "var(--green)" }}>
          ✅ สแกนเสร็จ — พบ {done.signals} สัญญาณ | {done.elapsed?.toFixed(2)}s
        </span>
      )}
    </div>
  )
}
