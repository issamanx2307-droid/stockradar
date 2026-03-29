/**
 * pages/PrivacyPolicy.tsx
 * นโยบายความเป็นส่วนตัว — เข้าถึงได้ที่ /privacy-policy
 */
export default function PrivacyPolicy() {
  return (
    <div style={{
      fontFamily: "'IBM Plex Sans Thai', sans-serif",
      background: "#080d18", color: "#e2e8f0",
      minHeight: "100vh", padding: "60px 24px",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700;800&display=swap');
        .pp-container { max-width: 800px; margin: 0 auto; }
        .pp-h2 { font-size: 20px; font-weight: 700; color: #00d4ff; margin: 36px 0 12px; }
        .pp-p  { font-size: 15px; color: #a0b4c8; line-height: 1.9; margin: 0 0 14px; }
        .pp-ul { font-size: 15px; color: #a0b4c8; line-height: 1.9; padding-left: 20px; margin: 0 0 14px; }
        .pp-ul li { margin-bottom: 6px; }
      `}</style>

      <div className="pp-container">
        {/* Header */}
        <div style={{ marginBottom: 40 }}>
          <a href="/" style={{ fontSize: 14, color: "#00d4ff", textDecoration: "none" }}>← กลับหน้าหลัก</a>
          <h1 style={{ fontSize: 34, fontWeight: 800, margin: "20px 0 8px" }}>
            นโยบายความเป็นส่วนตัว
          </h1>
          <div style={{ fontSize: 14, color: "#4a5a70" }}>
            Privacy Policy — RadarHoon.com<br />
            อัปเดตล่าสุด: มีนาคม 2026
          </div>
        </div>

        <div style={{
          padding: "16px 20px", borderRadius: 10, marginBottom: 32,
          background: "rgba(0,212,255,.05)", border: "1px solid rgba(0,212,255,.2)",
          fontSize: 14, color: "#7a90a8", lineHeight: 1.8,
        }}>
          RadarHoon.com ให้ความสำคัญกับความเป็นส่วนตัวของผู้ใช้งาน
          นโยบายนี้อธิบายถึงข้อมูลที่เราเก็บรวบรวม วิธีการใช้งาน และการปกป้องข้อมูลของคุณ
        </div>

        <h2 className="pp-h2">1. ข้อมูลที่เราเก็บรวบรวม</h2>
        <p className="pp-p">เมื่อคุณลงทะเบียนหรือเข้าสู่ระบบผ่าน Google เราจะเก็บข้อมูลดังต่อไปนี้:</p>
        <ul className="pp-ul">
          <li>ชื่อและนามสกุลจาก Google Account</li>
          <li>อีเมลที่ใช้ลงทะเบียน</li>
          <li>รูปโปรไฟล์จาก Google Account</li>
          <li>Google ID (ตัวระบุบัญชีที่ไม่ซ้ำกัน)</li>
          <li>ข้อมูลการใช้งาน Watchlist และการตั้งค่าส่วนตัว</li>
        </ul>

        <h2 className="pp-h2">2. วัตถุประสงค์ในการใช้ข้อมูล</h2>
        <p className="pp-p">เราใช้ข้อมูลของคุณเพื่อ:</p>
        <ul className="pp-ul">
          <li>ยืนยันตัวตนและให้บริการแพลตฟอร์ม</li>
          <li>บันทึก Watchlist และการตั้งค่าส่วนตัว</li>
          <li>แสดงข้อมูลบัญชีและระดับสมาชิก</li>
          <li>ปรับปรุงประสิทธิภาพและคุณภาพของบริการ</li>
        </ul>

        <h2 className="pp-h2">3. การเปิดเผยข้อมูลต่อบุคคลที่สาม</h2>
        <p className="pp-p">
          เราไม่ขาย ไม่แลกเปลี่ยน หรือถ่ายโอนข้อมูลส่วนตัวของคุณให้กับบุคคลภายนอก
          ยกเว้นกรณีที่จำเป็นต้องปฏิบัติตามกฎหมายหรือคำสั่งของหน่วยงานที่มีอำนาจ
        </p>

        <h2 className="pp-h2">4. การรักษาความปลอดภัยของข้อมูล</h2>
        <ul className="pp-ul">
          <li>การสื่อสารทั้งหมดเข้ารหัสด้วย HTTPS (TLS)</li>
          <li>ไม่เก็บรหัสผ่านใดๆ — ใช้ Google OAuth เท่านั้น</li>
          <li>Token สำหรับการยืนยันตัวตนจัดเก็บอย่างปลอดภัยบนเซิร์ฟเวอร์</li>
        </ul>

        <h2 className="pp-h2">5. คำเตือนเกี่ยวกับการลงทุน</h2>
        <div style={{
          padding: "16px 20px", borderRadius: 10,
          background: "rgba(255,183,0,.06)", border: "1px solid rgba(255,183,0,.3)",
          fontSize: 14, color: "#ffd54f", lineHeight: 1.9, marginBottom: 14,
        }}>
          <strong>⚠️ สำคัญ:</strong> RadarHoon.com เป็นเครื่องมือวิเคราะห์ข้อมูลเชิงสถิติตามหลักการที่เป็นที่ทราบกันโดยทั่วไป
          ไม่ถือเป็นคำแนะนำการลงทุน การซื้อขายหลักทรัพย์มีความเสี่ยง
          ผู้ใช้งานควรศึกษาข้อมูลและตัดสินใจด้วยตนเอง
        </div>

        <h2 className="pp-h2">6. สิทธิ์ของผู้ใช้งาน</h2>
        <p className="pp-p">คุณมีสิทธิ์:</p>
        <ul className="pp-ul">
          <li>ขอดูข้อมูลที่เราเก็บไว้เกี่ยวกับคุณ</li>
          <li>ขอลบข้อมูลส่วนตัวของคุณออกจากระบบ</li>
          <li>ถอนความยินยอมการใช้ข้อมูลได้ตลอดเวลา</li>
        </ul>

        <h2 className="pp-h2">7. การเก็บรักษาข้อมูล</h2>
        <p className="pp-p">
          เราเก็บข้อมูลของคุณตราบเท่าที่บัญชียังคงใช้งานอยู่
          หากคุณต้องการลบบัญชี กรุณาติดต่อเราผ่านหน้า "ติดต่อเรา" ในแพลตฟอร์ม
        </p>

        <h2 className="pp-h2">8. การเปลี่ยนแปลงนโยบาย</h2>
        <p className="pp-p">
          เราอาจอัปเดตนโยบายความเป็นส่วนตัวนี้เป็นครั้งคราว
          การเปลี่ยนแปลงสำคัญจะแจ้งให้ทราบผ่านแพลตฟอร์ม
        </p>

        <h2 className="pp-h2">9. ติดต่อเรา</h2>
        <p className="pp-p">
          หากมีคำถามเกี่ยวกับนโยบายความเป็นส่วนตัวนี้ กรุณาติดต่อผ่านแพลตฟอร์ม RadarHoon.com
          หรือช่องทาง "ติดต่อเรา" ในระบบ
        </p>

        {/* Footer */}
        <div style={{
          marginTop: 48, paddingTop: 24,
          borderTop: "1px solid rgba(255,255,255,.06)",
          fontSize: 13, color: "#2a3a4a", textAlign: "center",
        }}>
          © {new Date().getFullYear()} RadarHoon.com — สงวนลิขสิทธิ์
        </div>
      </div>
    </div>
  )
}
