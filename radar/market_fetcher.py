"""
market_fetcher.py
ดึงรายชื่อหุ้นจากตลาดจริงทั้งหมด
- SET    : yfinance fallback (Wikipedia มักบล็อก)
- S&P500 : Wikipedia ด้วย requests + headers
- NASDAQ100: Wikipedia ด้วย requests + headers
- NYSE   : Wikipedia Dow Jones + Fortune 500
"""

import logging
import time
import io

logger = logging.getLogger(__name__)

# Header ป้องกันถูกบล็อก
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _read_wiki(url: str):
    """ดึง HTML จาก Wikipedia แล้วแปลงเป็น DataFrame list"""
    import requests
    import pandas as pd
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return pd.read_html(io.StringIO(resp.text))


# ─── S&P 500 ─────────────────────────────────────────────────────────────────

def fetch_sp500() -> list[dict]:
    try:
        print("   📡 ดึง S&P 500 จาก Wikipedia...")
        tables = _read_wiki("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        df = tables[0]
        out = []
        for _, row in df.iterrows():
            sym = str(row["Symbol"]).strip().replace(".", "-")
            if not sym or sym.upper() == "NAN":
                continue
            out.append({
                "symbol":   sym,
                "name":     str(row.get("Security", sym)),
                "exchange": "NYSE",
                "sector":   str(row.get("GICS Sector", "อื่นๆ")),
            })
        print(f"   ✅ S&P 500: {len(out)} ตัว")
        return out
    except Exception as e:
        logger.error("fetch_sp500 ล้มเหลว: %s", e)
        return []


# ─── NASDAQ 100 ──────────────────────────────────────────────────────────────

def fetch_nasdaq100() -> list[dict]:
    try:
        print("   📡 ดึง NASDAQ 100 จาก Wikipedia...")
        tables = _read_wiki("https://en.wikipedia.org/wiki/Nasdaq-100")
        df = None
        for t in tables:
            cols = [str(c).lower() for c in t.columns]
            if any("ticker" in c or "symbol" in c for c in cols):
                df = t
                break
        if df is None:
            return []

        sym_col  = next(c for c in df.columns if "ticker" in str(c).lower() or "symbol" in str(c).lower())
        name_col = next((c for c in df.columns if "company" in str(c).lower()), sym_col)
        sec_col  = next((c for c in df.columns if "sector" in str(c).lower()), None)

        out = []
        for _, row in df.iterrows():
            sym = str(row[sym_col]).strip().replace(".", "-")
            if not sym or sym.upper() == "NAN":
                continue
            out.append({
                "symbol":   sym,
                "name":     str(row[name_col]),
                "exchange": "NASDAQ",
                "sector":   str(row[sec_col]) if sec_col else "เทคโนโลยี",
            })
        print(f"   ✅ NASDAQ 100: {len(out)} ตัว")
        return out
    except Exception as e:
        logger.error("fetch_nasdaq100 ล้มเหลว: %s", e)
        return []


# ─── NYSE top (Dow Jones + Fortune 500) ──────────────────────────────────────

def fetch_nyse_top() -> list[dict]:
    try:
        print("   📡 ดึง NYSE top stocks จาก Wikipedia...")
        out = []
        seen = set()

        urls = [
            "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
            "https://en.wikipedia.org/wiki/List_of_largest_companies_in_the_United_States_by_revenue",
        ]

        for url in urls:
            try:
                tables = _read_wiki(url)
                for t in tables:
                    sym_col = next(
                        (c for c in t.columns if any(
                            k in str(c).lower() for k in ["ticker", "symbol"]
                        )), None
                    )
                    if not sym_col:
                        continue
                    name_col = next(
                        (c for c in t.columns if any(
                            k in str(c).lower() for k in ["company", "name"]
                        )), sym_col
                    )
                    for _, row in t.iterrows():
                        sym = str(row[sym_col]).strip().replace(".", "-")
                        if sym and sym.upper() != "NAN" and sym not in seen and len(sym) <= 6:
                            seen.add(sym)
                            out.append({
                                "symbol":   sym,
                                "name":     str(row[name_col]),
                                "exchange": "NYSE",
                                "sector":   "อื่นๆ",
                            })
                time.sleep(1)
            except Exception as e:
                logger.warning("NYSE url ล้มเหลว %s: %s", url, e)
                continue

        print(f"   ✅ NYSE top: {len(out)} ตัว")
        return out
    except Exception as e:
        logger.error("fetch_nyse ล้มเหลว: %s", e)
        return []


# ─── SET ─────────────────────────────────────────────────────────────────────

def fetch_set_symbols() -> list[dict]:
    """ดึงหุ้น SET — Wikipedia + fallback SET100"""
    try:
        print("   📡 ดึงหุ้น SET จาก Wikipedia...")
        out = []
        seen = set()

        urls = [
            "https://en.wikipedia.org/wiki/List_of_companies_listed_on_the_Stock_Exchange_of_Thailand",
            "https://en.wikipedia.org/wiki/SET_Index",
        ]
        for url in urls:
            try:
                tables = _read_wiki(url)
                for t in tables:
                    sym_col = next(
                        (c for c in t.columns if any(
                            k in str(c).lower() for k in ["ticker","symbol","หุ้น","รหัส"]
                        )), None
                    )
                    if not sym_col:
                        continue
                    name_col = next(
                        (c for c in t.columns if any(
                            k in str(c).lower() for k in ["company","name","ชื่อ","บริษัท"]
                        )), sym_col
                    )
                    sec_col = next(
                        (c for c in t.columns if any(
                            k in str(c).lower() for k in ["sector","industry","หมวด"]
                        )), None
                    )
                    for _, row in t.iterrows():
                        sym = str(row[sym_col]).strip().upper()
                        if not sym or sym == "NAN" or sym in seen:
                            continue
                        if len(sym) > 8 or not sym.replace("-","").replace(".","").isalnum():
                            continue
                        seen.add(sym)
                        out.append({
                            "symbol":   sym,
                            "name":     str(row[name_col]),
                            "exchange": "SET",
                            "sector":   str(row[sec_col]) if sec_col else "อื่นๆ",
                        })
                time.sleep(1)
            except Exception as e:
                logger.warning("SET url ล้มเหลว: %s", e)
                continue

        if len(out) < 50:
            print("   ⚠️  Wikipedia SET ได้น้อย ใช้ SET100 fallback...")
            return _set_fallback()

        print(f"   ✅ SET: {len(out)} ตัว")
        return out
    except Exception as e:
        logger.error("fetch_set ล้มเหลว: %s", e)
        return _set_fallback()


def _read_set_xls(filepath: str) -> list[dict]:
    """อ่านหุ้น SET จากไฟล์ XLS ที่ดาวน์โหลดจาก SET website"""
    try:
        import pandas as pd
        import io
        with open(filepath, 'rb') as f:
            content = f.read().decode('tis-620', errors='replace')
        df = pd.read_html(io.StringIO(content))[0]
        df = df.iloc[2:].reset_index(drop=True)
        df.columns = ['symbol','name','exchange','industry','sector',
                      'address','zipcode','tel','fax','website']
        df = df[df['exchange'].isin(['SET', 'mai'])].copy()
        df['symbol'] = df['symbol'].astype(str).str.strip().str.upper()
        df = df[df['symbol'].str.len() <= 8]
        df = df[df['symbol'] != 'NAN']
        df = df[df['symbol'].str.match(r'^[A-Z0-9-]+$')]
        result = []
        for _, row in df.iterrows():
            result.append({
                "symbol":   str(row['symbol']).strip(),
                "name":     str(row['symbol']).strip(),  # ใช้ symbol แทนชั่วคราว
                "exchange": "SET",
                "sector":   "อื่นๆ",
            })
        print(f"   ✅ SET จากไฟล์: {len(result)} ตัว")
        return result
    except Exception as e:
        logger.error("อ่านไฟล์ SET ล้มเหลว: %s", e)
        return _set_fallback()


def _set_fallback() -> list[dict]:
    rows = [
        ("PTT","ปตท.","พลังงาน"),("PTTEP","ปตท.สำรวจ","พลังงาน"),
        ("GULF","กัลฟ์","พลังงาน"),("GPSC","โกลบอลเพาเวอร์","พลังงาน"),
        ("BGRIM","บีกริม","พลังงาน"),("RATCH","ราชกรุ๊ป","พลังงาน"),
        ("EGCO","ผลิตไฟฟ้า","พลังงาน"),("BANPU","บ้านปู","พลังงาน"),
        ("TOP","ไทยออยล์","พลังงาน"),("IRPC","ไออาร์พีซี","พลังงาน"),
        ("BCP","บางจาก","พลังงาน"),("OR","ปตท.น้ำมัน","พลังงาน"),
        ("EA","พลังงานบริสุทธิ์","พลังงาน"),("GUNKUL","กันกุล","พลังงาน"),
        ("WHA","ดับบลิวเอชเอ","พลังงาน"),("SUPER","ซุปเปอร์","พลังงาน"),
        ("KBANK","ธ.กสิกร","การเงิน"),("SCB","ธ.ไทยพาณิชย์","การเงิน"),
        ("BBL","ธ.กรุงเทพ","การเงิน"),("KTB","ธ.กรุงไทย","การเงิน"),
        ("BAY","ธ.กรุงศรี","การเงิน"),("TISCO","ทิสโก้","การเงิน"),
        ("KKP","เกียรตินาคิน","การเงิน"),("SAWAD","ศรีสวัสดิ์","การเงิน"),
        ("TIDLOR","ไทยเดินรถ","การเงิน"),("MTC","เมืองไทยแคปปิตอล","การเงิน"),
        ("AEONTS","อิออน","การเงิน"),("GL","กรุ๊ปลีส","การเงิน"),
        ("ADVANC","แอดวานซ์","เทคโนโลยี"),("TRUE","ทรู","เทคโนโลยี"),
        ("INTUCH","อินทัช","เทคโนโลยี"),("JMART","เจมาร์ท","เทคโนโลยี"),
        ("COM7","คอมเซเว่น","เทคโนโลยี"),("MFEC","เอ็มเฟค","เทคโนโลยี"),
        ("NETBAY","เน็ตเบย์","เทคโนโลยี"),("BE8","บียอนด์","เทคโนโลยี"),
        ("CPALL","ซีพีออลล์","การค้าปลีก"),("CRC","เซ็นทรัลรีเทล","การค้าปลีก"),
        ("HMPRO","โฮมโปร","การค้าปลีก"),("MAKRO","แม็คโคร","การค้าปลีก"),
        ("BJC","เบอร์ลี่ยุคเกอร์","การค้าปลีก"),("OSP","โอสถสภา","การค้าปลีก"),
        ("BEAUTY","บิวตี้","การค้าปลีก"),("SAPPE","ซัปเป้","การค้าปลีก"),
        ("CPF","เจริญโภคภัณฑ์","อาหาร"),("TU","ไทยยูเนี่ยน","อาหาร"),
        ("GFPT","จีเอฟพีที","อาหาร"),("CBG","คาราบาว","อาหาร"),
        ("OISHI","โออิชิ","อาหาร"),("M","เอ็มเค","อาหาร"),
        ("ZEN","เซ็น","อาหาร"),("ICHI","อิชิตัน","อาหาร"),
        ("TIPCO","ทิปโก้","อาหาร"),("TFG","ไทยฟู้ดส์","อาหาร"),
        ("BDMS","กรุงเทพดุสิต","สุขภาพ"),("BH","บำรุงราษฎร์","สุขภาพ"),
        ("BCH","บางกอกเชน","สุขภาพ"),("CHG","จุฬารัตน์","สุขภาพ"),
        ("RAM","รามคำแหง","สุขภาพ"),("NHP","นวเวช","สุขภาพ"),
        ("PRINC","พระรามเก้า","สุขภาพ"),("THONBURI","ธนบุรี","สุขภาพ"),
        ("SKR","สมิติเวช","สุขภาพ"),("RJH","ราษฎร์ยินดี","สุขภาพ"),
        ("AOT","ท่าอากาศยาน","การขนส่ง"),("AAV","เอเชียเอวิเอชั่น","การขนส่ง"),
        ("BA","การบินกรุงเทพ","การขนส่ง"),("THAI","การบินไทย","การขนส่ง"),
        ("MINT","ไมเนอร์","ท่องเที่ยว"),("ERW","เดอะเออร์เวิน","ท่องเที่ยว"),
        ("CENTEL","โรงแรมเซ็นทรัล","ท่องเที่ยว"),("AWC","แอสเสทเวิรด์","ท่องเที่ยว"),
        ("CPN","เซ็นทรัลพัฒนา","อสังหาริมทรัพย์"),("LH","แลนด์แอนด์เฮ้าส์","อสังหาริมทรัพย์"),
        ("SPALI","ศุภาลัย","อสังหาริมทรัพย์"),("QH","ควอลิตี้เฮ้าส์","อสังหาริมทรัพย์"),
        ("AP","เอพี","อสังหาริมทรัพย์"),("SIRI","แสนสิริ","อสังหาริมทรัพย์"),
        ("PS","พฤกษา","อสังหาริมทรัพย์"),("ORI","ออริจิ้น","อสังหาริมทรัพย์"),
        ("SCC","ปูนซิเมนต์ไทย","วัสดุก่อสร้าง"),("SCCC","ปูนนครหลวง","วัสดุก่อสร้าง"),
        ("IVL","อินโดรามา","ปิโตรเคมี"),("PTTGC","พีทีทีโกลบอล","ปิโตรเคมี"),
        ("VGI","วีจีไอ","สื่อโฆษณา"),("TVO","น้ำมันพืชไทย","เกษตร"),
        ("KSL","ขอนแก่นน้ำตาล","เกษตร"),("TPIPL","ทีพีไอ","วัสดุก่อสร้าง"),
        ("NOBLE","โนเบิล","อสังหาริมทรัพย์"),("SC","เอสซีแอสเสท","อสังหาริมทรัพย์"),
    ]
    seen = set()
    result = []
    for sym, name, sector in rows:
        if sym not in seen:
            seen.add(sym)
            result.append({"symbol": sym, "name": name, "exchange": "SET", "sector": sector})
    return result


# ─── รวมทุกตลาด ──────────────────────────────────────────────────────────────

def fetch_all_markets() -> list[dict]:
    all_symbols = []
    seen = set()

    for fetcher in [fetch_set_symbols, fetch_sp500, fetch_nasdaq100, fetch_nyse_top]:
        try:
            symbols = fetcher()
            for s in symbols:
                sym = s["symbol"].strip().upper()
                if sym and sym not in seen and len(sym) <= 10:
                    seen.add(sym)
                    s["symbol"] = sym
                    all_symbols.append(s)
        except Exception as e:
            logger.error("fetcher ล้มเหลว: %s", e)
        time.sleep(1)

    print(f"\n   📊 รวมทั้งหมด: {len(all_symbols)} หุ้น")
    return all_symbols
