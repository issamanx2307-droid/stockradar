"""
โหลดรายชื่อหุ้นครบทั้งหมด — SET + NASDAQ + NYSE
ใช้ yfinance ดึงรายชื่อจริงจาก Yahoo Finance
"""

import time
import logging
from django.core.management.base import BaseCommand
from radar.models import Symbol

logger = logging.getLogger(__name__)

# ── หุ้น SET หลัก (SET100 + MAI) ──────────────────────────────────────────────
SET_SYMBOLS = [
    # (symbol, ชื่อบริษัท, sector)
    # พลังงาน
    ("PTT","ปตท.","พลังงาน"), ("PTTEP","ปตท.สำรวจ","พลังงาน"),
    ("GULF","กัลฟ์","พลังงาน"), ("GPSC","โกลบอลเพาเวอร์","พลังงาน"),
    ("BGRIM","บีกริม","พลังงาน"), ("RATCH","ราชกรุ๊ป","พลังงาน"),
    ("EGCO","ผลิตไฟฟ้า","พลังงาน"), ("BANPU","บ้านปู","พลังงาน"),
    ("TOP","ไทยออยล์","พลังงาน"), ("IRPC","ไออาร์พีซี","พลังงาน"),
    ("BCP","บางจาก","พลังงาน"), ("OR","ปตท.น้ำมัน","พลังงาน"),
    ("EA","พลังงานบริสุทธิ์","พลังงาน"), ("GUNKUL","กันกุล","พลังงาน"),
    ("SUPER","ซุปเปอร์เอนเนอร์ยี","พลังงาน"), ("ESSO","เอสโซ่","พลังงาน"),
    # การเงิน
    ("KBANK","ธ.กสิกรไทย","การเงิน"), ("SCB","ธ.ไทยพาณิชย์","การเงิน"),
    ("BBL","ธ.กรุงเทพ","การเงิน"), ("KTB","ธ.กรุงไทย","การเงิน"),
    ("BAY","ธ.กรุงศรี","การเงิน"), ("TISCO","ทิสโก้","การเงิน"),
    ("KKP","เกียรตินาคิน","การเงิน"), ("TCAP","ทุนธนชาต","การเงิน"),
    ("MBK","เอ็มบีเค","การเงิน"), ("SAWAD","ศรีสวัสดิ์","การเงิน"),
    ("TIDLOR","ไทยเดินรถ","การเงิน"), ("MTC","เมืองไทย แคปปิตอล","การเงิน"),
    ("AEONTS","อิออน ไทยแลนด์","การเงิน"), ("ASK","เอเซียเสริมกิจลีสซิ่ง","การเงิน"),
    ("THANI","ราษฎร์","การเงิน"), ("GL","กรุ๊ปลีส","การเงิน"),
    # เทคโนโลยี/สื่อสาร
    ("ADVANC","แอดวานซ์","เทคโนโลยี"), ("TRUE","ทรู","เทคโนโลยี"), ("VGI","วีจีไอ","เทคโนโลยี"),
    ("DTAC","ดีแทค","เทคโนโลยี"), ("INTUCH","อินทัช","เทคโนโลยี"),
    ("JMART","เจมาร์ท","เทคโนโลยี"), ("JD","เจดี เซ็นทรัล","เทคโนโลยี"),
    ("COM7","คอม เซเว่น","เทคโนโลยี"), ("SYMC","ซิมโฟนี่","เทคโนโลยี"),
    ("BE8","บียอนด์","เทคโนโลยี"), ("KBTG","กสิกร บิสซิเนส","เทคโนโลยี"),
    ("MFEC","เอ็มเฟค","เทคโนโลยี"), ("NETBAY","เน็ตเบย์","เทคโนโลยี"),
    # การค้าปลีก/อาหาร
    ("CPALL","ซีพีออลล์","การค้าปลีก"), ("CRC","เซ็นทรัลรีเทล","การค้าปลีก"),
    ("HMPRO","โฮมโปร","การค้าปลีก"), ("ROBINS","โรบินสัน","การค้าปลีก"),
    ("BJC","เบอร์ลี่ ยุคเกอร์","การค้าปลีก"), ("MAKRO","สยามแม็คโคร","การค้าปลีก"),
    ("GLOBAL","สยามโกลบอล","การค้าปลีก"), ("BEAUTY","บิวตี้","การค้าปลีก"),
    ("OSP","โอสถสภา","การค้าปลีก"), ("SAPPE","ซัปเป้","การค้าปลีก"),
    # อาหาร
    ("CPF","เจริญโภคภัณฑ์อาหาร","อาหาร"), ("TU","ไทยยูเนี่ยน","อาหาร"),
    ("GFPT","จีเอฟพีที","อาหาร"), ("NRF","เอ็นอาร์อินสแตนท์","อาหาร"),
    ("TFG","ไทยฟู้ดส์กรุ๊ป","อาหาร"), ("CBG","คาราบาวกรุ๊ป","อาหาร"),
    ("OISHI","โออิชิ","อาหาร"), ("M","เอ็มเค เรสโตรองต์","อาหาร"),
    ("ZEN","เซ็น คอร์ปอเรชั่น","อาหาร"), ("ICHI","อิชิตัน กรุ๊ป","อาหาร"), ("SNP","ส.ขอนแก่น","อาหาร"),
    ("TIPCO","ทิปโก้ฟู้ดส์","อาหาร"), ("KTIS","เกษตรไทย","อาหาร"),
    # สุขภาพ
    ("BDMS","กรุงเทพดุสิตเวชการ","สุขภาพ"), ("BH","บำรุงราษฎร์","สุขภาพ"),
    ("BCH","บางกอก เชน ฮอสปิทอล","สุขภาพ"), ("CHG","โรงพยาบาลจุฬารัตน์","สุขภาพ"),
    ("RJH","โรงพยาบาลราษฎร์ยินดี","สุขภาพ"), ("VIBHA","วิภาวดี","สุขภาพ"),
    ("RAM","โรงพยาบาลรามคำแหง","สุขภาพ"), ("SKR","สมิติเวช","สุขภาพ"),
    ("NHP","โรงพยาบาลนวเวช","สุขภาพ"), ("PRINC","โรงพยาบาลพระรามเก้า","สุขภาพ"),
    ("THONBURI","โรงพยาบาลธนบุรี","สุขภาพ"), ("PR9","โรงพยาบาลพระรามเก้า","สุขภาพ"),
    # ท่องเที่ยว/บริการ
    ("AOT","ท่าอากาศยานไทย","การขนส่ง"), ("AAV","เอเชีย เอวิเอชั่น","การขนส่ง"),
    ("BA","การบินกรุงเทพ","การขนส่ง"), ("THAI","การบินไทย","การขนส่ง"),
    ("MINT","ไมเนอร์","ท่องเที่ยว"), ("ERW","เดอะเออร์เวิน","ท่องเที่ยว"),
    ("CENTEL","โรงแรมเซ็นทรัล","ท่องเที่ยว"), ("DELTA","เดลต้า","ท่องเที่ยว"),
    ("SHREIT","เชียงใหม่ รีท","ท่องเที่ยว"), ("AWC","แอสเสท เวิรด์","ท่องเที่ยว"),
    # อสังหาริมทรัพย์
    ("CPN","เซ็นทรัลพัฒนา","อสังหาริมทรัพย์"), ("LH","แลนด์แอนด์เฮ้าส์","อสังหาริมทรัพย์"),
    ("SPALI","ศุภาลัย","อสังหาริมทรัพย์"), ("QH","ควอลิตี้เฮ้าส์","อสังหาริมทรัพย์"),
    ("AP","เอพี ไทยแลนด์","อสังหาริมทรัพย์"), ("WHA","ดับบลิวเอชเอ","อสังหาริมทรัพย์"),
    ("SIRI","แสนสิริ","อสังหาริมทรัพย์"),
    ("PS","พฤกษา","อสังหาริมทรัพย์"), ("SC","เอสซี แอสเสท","อสังหาริมทรัพย์"),
    ("ORI","ออริจิ้น","อสังหาริมทรัพย์"), ("NOBLE","โนเบิล","อสังหาริมทรัพย์"),
    ("KPN","เค.พี.เอ็น.แลนด์","อสังหาริมทรัพย์"), ("PRUKSA","พฤกษา","อสังหาริมทรัพย์"),
    # วัสดุก่อสร้าง/ปิโตรเคมี
    ("SCC","ปูนซิเมนต์ไทย","วัสดุก่อสร้าง"), ("SCCC","ปูนซิเมนต์นครหลวง","วัสดุก่อสร้าง"),
    ("TPIPL","ทีพีไอ โพลีน","วัสดุก่อสร้าง"), ("DCC","ไดนาสตี้เซรามิค","วัสดุก่อสร้าง"),
    ("IVL","อินโดรามา","ปิโตรเคมี"), ("PTTGC","พีทีที โกลบอล","ปิโตรเคมี"),
    ("INDORAMA","อินโดรามา","ปิโตรเคมี"), ("HMC","เอชเอ็มซี","ปิโตรเคมี"),
    # การเกษตร
    ("KSL","ขอนแก่นน้ำตาล","เกษตร"), ("KTIS","เกษตรไทย","เกษตร"),
    ("TVO","น้ำมันพืชไทย","เกษตร"), ("UPOIC","ยูนิวานิชน้ำมันปาล์ม","เกษตร"),
]

# ── หุ้น US — S&P500 + NASDAQ100 รายใหญ่ ──────────────────────────────────────
US_SYMBOLS = [
    # (symbol, ชื่อบริษัท, exchange, sector)
    # เทคโนโลยีขนาดใหญ่
    ("AAPL","Apple","NASDAQ","เทคโนโลยี"), ("MSFT","Microsoft","NASDAQ","เทคโนโลยี"),
    ("GOOGL","Alphabet","NASDAQ","เทคโนโลยี"), ("AMZN","Amazon","NASDAQ","อีคอมเมิร์ซ"),
    ("NVDA","NVIDIA","NASDAQ","เซมิคอนดักเตอร์"), ("META","Meta","NASDAQ","โซเชียลมีเดีย"),
    ("TSLA","Tesla","NASDAQ","ยานยนต์"), ("AVGO","Broadcom","NASDAQ","เซมิคอนดักเตอร์"),
    ("ORCL","Oracle","NYSE","เทคโนโลยี"), ("CRM","Salesforce","NYSE","ซอฟต์แวร์"),
    ("ADBE","Adobe","NASDAQ","ซอฟต์แวร์"), ("AMD","AMD","NASDAQ","เซมิคอนดักเตอร์"),
    ("INTC","Intel","NASDAQ","เซมิคอนดักเตอร์"), ("QCOM","Qualcomm","NASDAQ","เซมิคอนดักเตอร์"),
    ("TXN","Texas Instruments","NASDAQ","เซมิคอนดักเตอร์"), ("MU","Micron","NASDAQ","เซมิคอนดักเตอร์"),
    ("AMAT","Applied Materials","NASDAQ","เซมิคอนดักเตอร์"), ("LRCX","Lam Research","NASDAQ","เซมิคอนดักเตอร์"),
    ("KLAC","KLA Corp","NASDAQ","เซมิคอนดักเตอร์"), ("MRVL","Marvell","NASDAQ","เซมิคอนดักเตอร์"),
    ("NFLX","Netflix","NASDAQ","บันเทิง"), ("DIS","Disney","NYSE","บันเทิง"),
    ("SPOT","Spotify","NYSE","บันเทิง"), ("SNAP","Snap","NYSE","โซเชียลมีเดีย"),
    ("UBER","Uber","NYSE","การขนส่ง"), ("LYFT","Lyft","NASDAQ","การขนส่ง"),
    ("ABNB","Airbnb","NASDAQ","ท่องเที่ยว"), ("BKNG","Booking Holdings","NASDAQ","ท่องเที่ยว"),
    ("EXPE","Expedia","NASDAQ","ท่องเที่ยว"),
    # การเงิน
    ("JPM","JPMorgan","NYSE","การเงิน"), ("BAC","Bank of America","NYSE","การเงิน"),
    ("WFC","Wells Fargo","NYSE","การเงิน"), ("GS","Goldman Sachs","NYSE","การเงิน"),
    ("MS","Morgan Stanley","NYSE","การเงิน"), ("C","Citigroup","NYSE","การเงิน"),
    ("BLK","BlackRock","NYSE","การเงิน"), ("SCHW","Charles Schwab","NYSE","การเงิน"),
    ("AXP","American Express","NYSE","การเงิน"), ("V","Visa","NYSE","การเงิน"),
    ("MA","Mastercard","NYSE","การเงิน"), ("PYPL","PayPal","NASDAQ","การเงิน"),
    ("COF","Capital One","NYSE","การเงิน"), ("USB","US Bancorp","NYSE","การเงิน"),
    ("PNC","PNC Financial","NYSE","การเงิน"), ("TFC","Truist Financial","NYSE","การเงิน"),
    # สุขภาพ/เภสัชกรรม
    ("JNJ","J&J","NYSE","สุขภาพ"), ("LLY","Eli Lilly","NYSE","เภสัชกรรม"),
    ("UNH","UnitedHealth","NYSE","สุขภาพ"), ("ABBV","AbbVie","NYSE","เภสัชกรรม"),
    ("MRK","Merck","NYSE","เภสัชกรรม"), ("PFE","Pfizer","NYSE","เภสัชกรรม"),
    ("TMO","Thermo Fisher","NYSE","สุขภาพ"), ("ABT","Abbott","NYSE","สุขภาพ"),
    ("DHR","Danaher","NYSE","สุขภาพ"), ("BMY","Bristol-Myers","NYSE","เภสัชกรรม"),
    ("AMGN","Amgen","NASDAQ","เภสัชกรรม"), ("GILD","Gilead","NASDAQ","เภสัชกรรม"),
    ("BIIB","Biogen","NASDAQ","เภสัชกรรม"), ("REGN","Regeneron","NASDAQ","เภสัชกรรม"),
    ("MRNA","Moderna","NASDAQ","เภสัชกรรม"), ("CVS","CVS Health","NYSE","สุขภาพ"),
    ("CI","Cigna","NYSE","สุขภาพ"), ("HUM","Humana","NYSE","สุขภาพ"),
    ("ISRG","Intuitive Surgical","NASDAQ","สุขภาพ"), ("SYK","Stryker","NYSE","สุขภาพ"),
    # พลังงาน
    ("XOM","Exxon Mobil","NYSE","พลังงาน"), ("CVX","Chevron","NYSE","พลังงาน"),
    ("COP","ConocoPhillips","NYSE","พลังงาน"), ("EOG","EOG Resources","NYSE","พลังงาน"),
    ("SLB","SLB","NYSE","พลังงาน"), ("MPC","Marathon Petroleum","NYSE","พลังงาน"),
    ("VLO","Valero","NYSE","พลังงาน"), ("PSX","Phillips 66","NYSE","พลังงาน"),
    ("OXY","Occidental","NYSE","พลังงาน"), ("HAL","Halliburton","NYSE","พลังงาน"),
    ("NEE","NextEra Energy","NYSE","พลังงานสะอาด"), ("ENPH","Enphase","NASDAQ","พลังงานสะอาด"),
    # การค้าปลีก/อุปโภค
    ("WMT","Walmart","NYSE","การค้าปลีก"), ("COST","Costco","NASDAQ","การค้าปลีก"),
    ("TGT","Target","NYSE","การค้าปลีก"), ("HD","Home Depot","NYSE","การค้าปลีก"),
    ("LOW","Lowe's","NYSE","การค้าปลีก"), ("NKE","Nike","NYSE","สินค้าผู้บริโภค"),
    ("SBUX","Starbucks","NASDAQ","อาหาร"), ("MCD","McDonald's","NYSE","อาหาร"),
    ("YUM","Yum Brands","NYSE","อาหาร"), ("CMG","Chipotle","NYSE","อาหาร"),
    ("PG","Procter & Gamble","NYSE","สินค้าอุปโภค"), ("KO","Coca-Cola","NYSE","เครื่องดื่ม"),
    ("PEP","PepsiCo","NASDAQ","เครื่องดื่ม"), ("PM","Philip Morris","NYSE","ยาสูบ"),
    ("MO","Altria","NYSE","ยาสูบ"), ("CL","Colgate","NYSE","สินค้าอุปโภค"),
    ("KHC","Kraft Heinz","NASDAQ","อาหาร"), ("GIS","General Mills","NYSE","อาหาร"),
    ("K","Kellogg","NYSE","อาหาร"), ("CAG","ConAgra","NYSE","อาหาร"),
    # อุตสาหกรรม
    ("CAT","Caterpillar","NYSE","อุตสาหกรรม"), ("DE","John Deere","NYSE","อุตสาหกรรม"),
    ("BA","Boeing","NYSE","อากาศยาน"), ("RTX","RTX","NYSE","อากาศยาน"),
    ("LMT","Lockheed Martin","NYSE","อากาศยาน"), ("NOC","Northrop Grumman","NYSE","อากาศยาน"),
    ("GD","General Dynamics","NYSE","อากาศยาน"), ("GE","GE Aerospace","NYSE","อุตสาหกรรม"),
    ("HON","Honeywell","NASDAQ","อุตสาหกรรม"), ("MMM","3M","NYSE","อุตสาหกรรม"),
    ("EMR","Emerson Electric","NYSE","อุตสาหกรรม"), ("ETN","Eaton","NYSE","อุตสาหกรรม"),
    ("ITW","Illinois Tool","NYSE","อุตสาหกรรม"), ("PH","Parker Hannifin","NYSE","อุตสาหกรรม"),
    ("UPS","UPS","NYSE","การขนส่ง"), ("FDX","FedEx","NYSE","การขนส่ง"),
    ("CSX","CSX","NASDAQ","การขนส่ง"), ("UNP","Union Pacific","NYSE","การขนส่ง"),
    # อสังหาริมทรัพย์ REIT
    ("AMT","American Tower","NYSE","REIT"), ("PLD","Prologis","NYSE","REIT"),
    ("EQIX","Equinix","NASDAQ","REIT"), ("CCI","Crown Castle","NYSE","REIT"),
    ("SPG","Simon Property","NYSE","REIT"), ("O","Realty Income","NYSE","REIT"),
    # อื่นๆ
    ("BRK.B","Berkshire Hathaway","NYSE","การเงิน"), ("SPGI","S&P Global","NYSE","การเงิน"),
    ("MCO","Moody's","NYSE","การเงิน"), ("ICE","ICE","NYSE","การเงิน"),
    ("CME","CME Group","NASDAQ","การเงิน"),
]


class Command(BaseCommand):
    help = "โหลดรายชื่อหุ้นครบทั้งหมด SET + US"

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true", help="อัปเดตข้อมูลที่มีอยู่แล้ว")

    def handle(self, *args, **options):
        do_update = options["update"]
        created = updated = skipped = 0

        self.stdout.write(self.style.MIGRATE_HEADING("=== โหลดรายชื่อหุ้นครบทั้งหมด ==="))

        # ── SET ──
        self.stdout.write(f"\n🇹🇭 SET ({len(SET_SYMBOLS)} ตัว)")
        for sym, name, sector in SET_SYMBOLS:
            obj, was_created = Symbol.objects.get_or_create(
                symbol=sym,
                defaults={"name": name, "exchange": "SET", "sector": sector},
            )
            if was_created:
                created += 1
            elif do_update:
                obj.name = name; obj.sector = sector; obj.save()
                updated += 1
            else:
                skipped += 1

        # ── US ──
        self.stdout.write(f"🇺🇸 US ({len(US_SYMBOLS)} ตัว)")
        for sym, name, exchange, sector in US_SYMBOLS:
            obj, was_created = Symbol.objects.get_or_create(
                symbol=sym,
                defaults={"name": name, "exchange": exchange, "sector": sector},
            )
            if was_created:
                created += 1
            elif do_update:
                obj.name = name; obj.exchange = exchange; obj.sector = sector; obj.save()
                updated += 1
            else:
                skipped += 1

        total = len(SET_SYMBOLS) + len(US_SYMBOLS)
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ รวม {total} หุ้น | เพิ่มใหม่: {created} | อัปเดต: {updated} | ข้าม: {skipped}"
        ))
