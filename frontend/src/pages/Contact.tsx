import { useState, useEffect } from "react"
import { api } from "../api/client"
import { BusinessProfileInfo } from "../api/types"

export default function Contact() {
  const [profile, setProfile] = useState<BusinessProfileInfo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getBusinessProfile()
      .then(setProfile)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-center">กำลังโหลดข้อมูลติดต่อ...</div>
  if (!profile) return (
    <div className="p-8 text-center text-red-500">
      ยังไม่มีข้อมูลโพรไฟล์ธุรกิจ กรุณาเพิ่มข้อมูลในหน้า Admin
    </div>
  )

  return (
    <div className="contact-page p-8 max-w-4xl mx-auto">
      <header className="page-header mb-12 text-center">
        <h1 className="text-3xl font-bold mb-2">ติดต่อเรา</h1>
        <p className="text-secondary">{profile.company_name}</p>
      </header>

      <div className="grid-2-col">
        {/* รายละเอียดธุรกิจ */}
        <section className="card p-8">
          <h2 className="text-xl font-bold mb-6">เกี่ยวกับเรา</h2>
          <p className="whitespace-pre-line text-primary leading-relaxed">
            {profile.description || "ไม่มีรายละเอียดธุรกิจ"}
          </p>
          
          <div className="mt-8 pt-8 border-t border">
            <h3 className="text-sm font-bold text-secondary uppercase tracking-wider mb-4">
              ข้อความจากเรา
            </h3>
            <p className="italic text-accent">
              "{profile.footer_text || "ยินดีให้บริการครับ"}"
            </p>
          </div>
        </section>

        {/* ช่องทางติดต่อ */}
        <section className="card p-8">
          <h2 className="text-xl font-bold mb-6">ช่องทางการติดต่อ</h2>
          
          <div className="space-y-6">
            {profile.address && (
              <div className="flex gap-4">
                <span className="text-2xl">📍</span>
                <div>
                  <label className="text-xs text-secondary uppercase block mb-1">ที่อยู่</label>
                  <p className="text-sm">{profile.address}</p>
                </div>
              </div>
            )}

            {profile.phone && (
              <div className="flex gap-4">
                <span className="text-2xl">📞</span>
                <div>
                  <label className="text-xs text-secondary uppercase block mb-1">เบอร์โทรศัพท์</label>
                  <p className="text-sm">{profile.phone}</p>
                </div>
              </div>
            )}

            {profile.email && (
              <div className="flex gap-4">
                <span className="text-2xl">✉️</span>
                <div>
                  <label className="text-xs text-secondary uppercase block mb-1">อีเมล</label>
                  <p className="text-sm">{profile.email}</p>
                </div>
              </div>
            )}

            {profile.line_id && (
              <div className="flex gap-4">
                <span className="text-2xl">💬</span>
                <div>
                  <label className="text-xs text-secondary uppercase block mb-1">Line ID</label>
                  <p className="text-sm">@{profile.line_id}</p>
                </div>
              </div>
            )}

            <div className="pt-6 mt-6 border-t border flex gap-4">
              {profile.facebook_url && (
                <a href={profile.facebook_url} target="_blank" rel="noreferrer" className="btn btn-secondary p-3">
                  Facebook
                </a>
              )}
              {profile.website_url && (
                <a href={profile.website_url} target="_blank" rel="noreferrer" className="btn btn-primary p-3">
                  เข้าชมเว็บไซต์
                </a>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
