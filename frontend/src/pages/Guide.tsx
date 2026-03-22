import { useState } from "react"
import { GUIDE_DATA, GuideItem } from "../data/guideData"

export default function Guide() {
  const [selected, setSelected] = useState<GuideItem>(GUIDE_DATA[0])

  return (
    <div className="guide-page p-8 max-w-5xl mx-auto">
      <header className="page-header mb-8">
        <h1 className="text-3xl font-bold mb-2">💡 เมนูคำแนะนำ</h1>
        <p className="text-secondary">คำอธิบายสูตรการคำนวณและค่าที่เหมาะสมสำหรับ Indicator ต่างๆ</p>
      </header>

      <div className="grid-2-col" style={{ gridTemplateColumns: "300px 1fr" }}>
        {/* เมนูรายการ */}
        <aside className="card p-4 h-fit">
          <h2 className="text-sm font-bold text-secondary uppercase tracking-widest mb-4 px-2">รายชื่อเครื่องมือ</h2>
          <div className="space-y-1">
            {GUIDE_DATA.map(item => (
              <button
                key={item.id}
                className={`nav-btn w-full text-left ${selected.id === item.id ? "active" : ""}`}
                onClick={() => setSelected(item)}
              >
                <span className="flex flex-col">
                  <span className="font-bold">{item.id.toUpperCase()}</span>
                  <small className="text-xs opacity-60">{item.category}</small>
                </span>
              </button>
            ))}
          </div>
        </aside>

        {/* รายละเอียด */}
        <main className="space-y-6">
          <section className="card p-8">
            <div className="flex justify-between items-start mb-6">
              <div>
                <span className="badge-category mb-2">{selected.category}</span>
                <h2 className="text-2xl font-bold text-accent">{selected.name}</h2>
              </div>
            </div>

            <div className="space-y-8">
              <div>
                <h3 className="text-sm font-bold text-secondary uppercase mb-3">คำอธิบาย</h3>
                <p className="text-primary leading-relaxed text-lg">
                  {selected.description}
                </p>
              </div>

              <div className="grid-2-col">
                <div className="p-6 bg-elevated rounded-lg border border-border">
                  <h3 className="text-sm font-bold text-secondary uppercase mb-3">สูตรการคำนวณ</h3>
                  <code className="text-accent font-mono text-sm">{selected.formula}</code>
                </div>
                <div className="p-6 bg-elevated rounded-lg border border-border">
                  <h3 className="text-sm font-bold text-secondary uppercase mb-3">ค่าที่แนะนำ</h3>
                  <p className="text-yellow font-bold">{selected.recommended_value}</p>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-sm font-bold text-secondary uppercase mb-1">ความหมายของสัญญาณ</h3>
                <div className="grid-2-col">
                  <div className="p-5 border-l-4 border-green bg-green-dim rounded-r-lg">
                    <h4 className="text-green font-bold mb-2">🟢 Bullish (ขาขึ้น)</h4>
                    <p className="text-sm text-primary opacity-90">{selected.signal_meaning.bullish}</p>
                  </div>
                  <div className="p-5 border-l-4 border-red bg-red-dim rounded-r-lg">
                    <h4 className="text-red font-bold mb-2">🔴 Bearish (ขาลง)</h4>
                    <p className="text-sm text-primary opacity-90">{selected.signal_meaning.bearish}</p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}
