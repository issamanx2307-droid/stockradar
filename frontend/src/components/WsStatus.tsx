export function WsStatus({ connected }: { connected: boolean }) {
  return (
    <div style={{
      position: "fixed", bottom: 8, left: 8, zIndex: 999,
      display: "flex", alignItems: "center", gap: 5,
      background: "var(--bg-elevated)", border: "1px solid var(--border)",
      borderRadius: 20, padding: "3px 10px", fontSize: 10,
      color: connected ? "var(--green)" : "var(--text-muted)",
    }}>
      <div style={{
        width: 6, height: 6, borderRadius: "50%",
        background: connected ? "var(--green)" : "var(--text-muted)",
        boxShadow: connected ? "0 0 6px var(--green)" : "none",
      }} />
      {connected ? "Live" : "Offline"}
    </div>
  )
}
