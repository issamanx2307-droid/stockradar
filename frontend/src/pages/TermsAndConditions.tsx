/**
 * pages/TermsAndConditions.tsx
 * ข้อกำหนดและเงื่อนไขการใช้บริการ — เข้าถึงได้ที่ /terms-and-conditions
 */
export default function TermsAndConditions() {
  return (
    <div style={{
      fontFamily: "'IBM Plex Sans Thai', sans-serif",
      background: "#080d18", color: "#e2e8f0",
      minHeight: "100vh", padding: "60px 24px",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700;800&display=swap');
        .tc-container { max-width: 800px; margin: 0 auto; }
        .tc-h2 { font-size: 20px; font-weight: 700; color: #00d4ff; margin: 36px 0 12px; }
        .tc-p  { font-size: 15px; color: #a0b4c8; line-height: 1.9; margin: 0 0 14px; }
        .tc-ul { font-size: 15px; color: #a0b4c8; line-height: 1.9; padding-left: 20px; margin: 0 0 14px; }
        .tc-ul li { margin-bottom: 6px; }
      `}</style>

      <div className="tc-container">
        {/* Header */}
        <div style={{ marginBottom: 40 }}>
          <a href="/" style={{ fontSize: 14, color: "#00d4ff", textDecoration: "none" }}>← กลับหน้าหลัก</a>
          <h1 style={{ fontSize: 34, fontWeight: 800, margin: "20px 0 8px" }}>
            ข้อกำหนดและเงื่อนไขการใช้บริการ
          </h1>
          <div style={{ fontSize: 14, color: "#4a5a70" }}>
            Terms and Conditions — RadarHoon.com<br />
            อัปเดตล่าสุด: มีนาคม 2026
          </div>
        </div>

        <div style={{
          padding: "16px 20px", borderRadius: 10, marginBottom: 32,
          background: "rgba(255,183,0,.06)", border: "1px solid rgba(255,183,0,.3)",
          fontSize: 14, color: "#ffd54f", lineHeight: 1.9,
        }}>
          <strong>⚠️ คำเตือนสำคัญ:</strong> RadarHoon.com เป็นเครื่องมือวิเคราะห์ข้อมูลเชิงสถิติตามหลักการที่เป็นที่ทราบกันโดยทั่วไป
          ไม่ถือเป็นคำแนะนำการลงทุน การซื้อขายหลักทรัพย์มีความเสี่ยง
          ผู้ใช้งานควรศึกษาข้อมูลและตัดสินใจด้วยตนเอง
        </div>

        <h2 className="tc-h2">1. การยอมรับข้อกำหนด</h2>
        <p className="tc-p">
          การเข้าใช้งาน RadarHoon.com ถือว่าคุณยอมรับข้อกำหนดและเงื่อนไขฉบับนี้ทุกประการ
          หากคุณไม่ยอมรับ กรุณาหยุดใช้งานแพลตฟอร์ม
        </p>

        <h2 className="tc-h2">2. ลักษณะของบริการ</h2>
        <p className="tc-p">
          RadarHoon.com เป็นแพลตฟอร์มที่รวบรวมเครื่องมือวิเคราะห์ข้อมูลหุ้นเชิงสถิติ (Indicator)
          ตามหลักการที่เป็นที่ทราบกันโดยทั่วไปในหมู่นักลงทุน เช่น EMA, RSI, MACD, Bollinger Bands, ADX
          เพื่อให้ผู้ใช้งานนำไปประกอบการตัดสินใจด้วยตนเอง
        </p>
        <ul className="tc-ul">
          <li>ข้อมูลทั้งหมดในแพลตฟอร์มมีวัตถุประสงค์เพื่อการศึกษาและวิเคราะห์เท่านั้น</li>
          <li>ไม่ถือเป็นคำแนะนำ คำปรึกษา หรือการชักชวนให้ซื้อขายหลักทรัพย์ใดๆ</li>
          <li>ผลการวิเคราะห์ในอดีตไม่ได้รับประกันผลลัพธ์ในอนาคต</li>
        </ul>

        <h2 className="tc-h2">3. ข้อจำกัดความรับผิดชอบ</h2>
        <p className="tc-p">
          RadarHoon.com และผู้พัฒนาไม่รับผิดชอบต่อความสูญเสียหรือความเสียหายใดๆ
          ที่เกิดจากการนำข้อมูลในแพลตฟอร์มไปใช้ตัดสินใจลงทุน ผู้ใช้งานรับทราบและยอมรับว่า:
        </p>
        <ul className="tc-ul">
          <li>การลงทุนในหลักทรัพย์มีความเสี่ยง อาจสูญเสียเงินลงทุนทั้งหมดหรือบางส่วน</li>
          <li>ผู้ใช้งานต้องศึกษาข้อมูลเพิ่มเติมและตัดสินใจด้วยตนเอง</li>
          <li>ควรปรึกษาที่ปรึกษาทางการเงินที่ได้รับใบอนุญาตก่อนตัดสินใจลงทุน</li>
        </ul>

        <h2 className="tc-h2">4. บัญชีผู้ใช้งาน</h2>
        <ul className="tc-ul">
          <li>การลงทะเบียนทำผ่าน Google Account เท่านั้น</li>
          <li>คุณรับผิดชอบต่อกิจกรรมทั้งหมดที่เกิดขึ้นภายใต้บัญชีของคุณ</li>
          <li>ห้ามแบ่งปันหรือโอนบัญชีให้ผู้อื่น</li>
          <li>เราสงวนสิทธิ์ระงับหรือยกเลิกบัญชีที่ละเมิดข้อกำหนด</li>
        </ul>

        <h2 className="tc-h2">5. ข้อมูลและความแม่นยำ</h2>
        <p className="tc-p">
          แม้เราพยายามอย่างสุดความสามารถในการนำเสนอข้อมูลที่ถูกต้อง แต่เราไม่รับประกัน
          ความสมบูรณ์ ความถูกต้อง หรือความทันสมัยของข้อมูลทุกรายการ
          ข้อมูลราคาหุ้นอาจมีความล่าช้าตามเงื่อนไขของแหล่งข้อมูล
        </p>

        <h2 className="tc-h2">6. ทรัพย์สินทางปัญญา</h2>
        <p className="tc-p">
          เนื้อหา การออกแบบ โค้ด และข้อมูลทั้งหมดบน RadarHoon.com เป็นทรัพย์สินของผู้พัฒนา
          ห้ามคัดลอก ดัดแปลง หรือนำไปใช้เชิงพาณิชย์โดยไม่ได้รับอนุญาตเป็นลายลักษณ์อักษร
        </p>

        <h2 className="tc-h2">7. การเปลี่ยนแปลงข้อกำหนด</h2>
        <p className="tc-p">
          เราสงวนสิทธิ์แก้ไขข้อกำหนดนี้ได้ตลอดเวลา การใช้งานต่อเนื่องหลังจากการเปลี่ยนแปลง
          ถือว่าคุณยอมรับข้อกำหนดที่อัปเดตแล้ว
        </p>

        <h2 className="tc-h2">8. กฎหมายที่ใช้บังคับ</h2>
        <p className="tc-p">
          ข้อกำหนดนี้อยู่ภายใต้กฎหมายแห่งราชอาณาจักรไทย
          ข้อพิพาทใดๆ ให้อยู่ในเขตอำนาจของศาลไทย
        </p>

        <h2 className="tc-h2">9. ติดต่อเรา</h2>
        <p className="tc-p">
          หากมีคำถามเกี่ยวกับข้อกำหนดนี้ กรุณาติดต่อผ่านช่องทาง "ติดต่อเรา" ในแพลตฟอร์ม RadarHoon.com
        </p>

        {/* Footer */}
        <div style={{
          marginTop: 48, paddingTop: 24,
          borderTop: "1px solid rgba(255,255,255,.06)",
          fontSize: 13, color: "#2a3a4a", textAlign: "center",
        }}>
          © {new Date().getFullYear()} RadarHoon.com — สงวนลิขสิทธิ์ &nbsp;|&nbsp;
          <a href="/privacy-policy" style={{ color: "#3a5a70", textDecoration: "none" }}>นโยบายความเป็นส่วนตัว</a>
        </div>
      </div>
    </div>
  )
}
