with open("D:/stockradar/radar/views.py", "r", encoding="utf-8") as f:
    content = f.read()

OLD_MARKER = "# ─── Watchlist API ────────────────────────────────────────────────────────────\n\ndef _get_session"
NEW_MARKER = "# ─── Watchlist API ────────────────────────────────────────────────────────────\n\ndef _get_or_create_watchlist"

idx_old = content.find(OLD_MARKER)
idx_new = content.find(NEW_MARKER)

print(f"New (correct) block at char: {idx_new}")
print(f"Old (broken) block at char:  {idx_old}")

# ชุดเก่า override ชุดใหม่ → ลบชุดเก่าออก
# ชุดเก่าอยู่ท้ายไฟล์ ตัดตั้งแต่ idx_old เป็นต้นไปก็ได้ แต่ต้องเก็บ
# Fundamental + portfolio_history views ที่อยู่ท้ายสุดไว้ด้วย

# หา Fundamental section ที่อยู่หลัง old watchlist
FUND_MARKER = "# ─── Fundamental Data API"
PORTFOLIO_MARKER = "# ─── Portfolio History"

idx_fund = content.find(FUND_MARKER, idx_old)
print(f"Fundamental block at char: {idx_fund}")

# ลบเฉพาะ old watchlist block (จาก idx_old ถึง idx_fund)
if idx_fund > idx_old:
    new_content = content[:idx_old] + content[idx_fund:]
    with open("D:/stockradar/radar/views.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Removed old block: {idx_fund - idx_old} chars")
    print(f"New file size: {len(new_content)} chars")
    c1 = new_content.count("def watchlist_list")
    c2 = new_content.count("user_session")
    print(f"watchlist_list definitions: {c1} (should be 1)")
    print(f"user_session occurrences: {c2} (should be 0)")
else:
    # ถ้าไม่มี Fundamental section หลัง old block
    # ลบตั้งแต่ idx_old ไปสิ้นสุดและแนบส่วนท้ายที่สำคัญ
    print("No Fundamental section found after old block, removing to end")
    new_content = content[:idx_old]
    with open("D:/stockradar/radar/views.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"New file size: {len(new_content)} chars")
