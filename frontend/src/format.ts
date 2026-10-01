function fold(value: string): string {
  return value.trim().toLowerCase();
}

export function readableSourceTitle(title: string): string {
  if (title.trim().toLowerCase() === "anythingllm textresponse") {
    return "Çalışan bilgi yanıtı";
  }
  const file = title.split(/[/\\]/).pop() ?? title;
  const stem = file.replace(/\.[a-z0-9]{2,5}$/i, "");
  const words = stem
    .replace(/^\d+[_-]/, "")
    .replace(/^estetik\s*ai[_-]/i, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return words || title;
}

export function splitVerified(item: string): { source: string; text: string } {
  const separator = item.indexOf(": ");
  if (separator === -1) {
    return { source: "Kurumsal bilgi", text: cleanExcerpt(item) };
  }
  const source = item.slice(0, separator).trim() || "Kurumsal bilgi";
  return { source, text: cleanExcerpt(item.slice(separator + 2)) };
}

export function cleanExcerpt(text: string): string {
  return text
    .replace(/<document_metadata>[\s\S]*?<\/document_metadata>/gi, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function priorityTone(priority: string): "low" | "medium" | "high" {
  const folded = fold(priority);
  if (folded === "high" || folded === "yüksek") return "high";
  if (folded === "low" || folded === "düşük") return "low";
  if (folded === "medium" || folded === "orta") return "medium";
  return "medium";
}

export function priorityLabel(priority: string): string {
  const folded = fold(priority);
  if (folded === "high" || folded === "yüksek") return "Yüksek";
  if (folded === "low" || folded === "düşük") return "Düşük";
  if (folded === "medium" || folded === "orta") return "Orta";
  return priority;
}

export function documentTitle(title: string): string {
  const readable = readableSourceTitle(title);
  const known = DOCUMENT_TITLES[fold(readable)];
  return known ?? readable;
}

const DOCUMENT_TITLES: Record<string, string> = {
  "internal operations handbook": "İç Operasyon El Kitabı",
  "lead and request management": "Talep ve Müşteri Kaydı",
  "international operations playbook": "Uluslararası Operasyon Rehberi",
  "escalation and ownership matrix": "Eskalasyon ve Sorumluluk Matrisi",
  "employee ai usage and quality policy": "Çalışan Yapay Zeka Kullanım ve Kalite Politikası",
  "public service knowledge": "Klinik Hizmet Bilgisi",
  "hair transplant public guide": "Saç Ekimi Rehberi",
  "public ai policy and faq": "Danışan Bilgilendirme ve Sık Sorular",
  "international visitor guide v2": "Yurt Dışı Ziyaretçi Rehberi",
  "international visitor guide": "Yurt Dışı Ziyaretçi Rehberi",
};

const FIELD_LABELS: Record<string, string> = {
  "visitor inquiry": "Ziyaretçi talebi",
  "lead follow-up": "Müşteri takibi",
  "internal operations": "İç operasyon",
  "international operations": "Uluslararası operasyon",
  escalation: "Eskalasyon",
  "policy question": "Politika sorusu",
  unknown: "Bilinmiyor",
  "hair transplant": "Saç ekimi",
  "general information": "Genel bilgi",
  greeting: "Selam",
  dental: "Diş",
  "plastic surgery": "Plastik cerrahi",
  consultation: "Danışma",
  "lead management": "Talep yönetimi",
  operations: "Operasyon",
  policy: "Politika",
  unspecified: "Belirtilmedi",
};

const SENTENCES: Record<string, string> = {
  "contact channel (e.g., email or phone)": "İletişim kanalı (örneğin e-posta veya telefon)",
  "whether the visitor is an existing lead": "Ziyaretçinin mevcut bir kayıt olup olmadığı",
  "preferred appointment date or timeframe": "Tercih edilen randevu tarihi veya zaman aralığı",
  "specific clinic or location preference": "Belirli bir klinik veya konum tercihi",
  "contact channel (email, phone, etc.)": "İletişim kanalı (e-posta, telefon vb.)",
  "whether the visitor is an existing lead in the system": "Ziyaretçinin sistemde kayıtlı olup olmadığı",
  "preferred language for communication": "İletişim için tercih edilen dil",
  "record the visitor's inquiry details in the system.": "Ziyaretçi talebinin ayrıntılarını sisteme kaydedin.",
  "route the pricing inquiry to sales / operations for confirmation.": "Fiyat sorusunu onay için Satış / Operasyon ekibine yönlendirin.",
  "escalate the medical suitability evaluation to an authorized healthcare professional.": "Tıbbi uygunluk değerlendirmesini yetkili sağlık profesyoneline iletin.",
  "send the appointment availability request to the scheduling team for confirmation.": "Randevu müsaitliği sorusunu onay için randevu ekibine iletin.",
  "request the visitor's preferred contact channel (e.g., email or phone).": "Ziyaretçiden tercih ettiği iletişim kanalını isteyin.",
  "ask whether the visitor is an existing lead in the system.": "Ziyaretçinin sistemde kayıtlı olup olmadığını sorun.",
  "ask for the visitor's preferred appointment date or timeframe.": "Tercih edilen randevu tarihi veya zaman aralığını sorun.",
  "ask for any specific clinic or location preference within germany.": "Almanya içinde belirli bir klinik veya konum tercihi olup olmadığını sorun.",
  "record the inquiry details in the crm system.": "Talep ayrıntılarını kayıt sistemine işleyin.",
  "classify the request as an international visitor hair transplant inquiry.": "Talebi, yurt dışından gelen bir ziyaretçinin saç ekimi sorusu olarak sınıflandırın.",
  "route the pricing question to the sales / operations team for confirmation.": "Fiyat sorusunu onay için Satış / Operasyon ekibine yönlendirin.",
  "send a request to the scheduling team to confirm appointment availability.": "Randevu müsaitliğini doğrulaması için randevu ekibine talep gönderin.",
  "request the visitor's preferred contact channel.": "Ziyaretçiden tercih ettiği iletişim kanalını isteyin.",
  "determine whether the visitor is a new lead or an existing lead.": "Ziyaretçinin yeni bir kayıt mı yoksa mevcut bir kayıt mı olduğunu belirleyin.",
  "document that pricing, appointment availability, and medical suitability require human confirmation before providing a response.": "Yanıt vermeden önce fiyat, randevu müsaitliği ve tıbbi uygunluğun insan onayı gerektirdiğini kayda geçirin.",
  "record the greeting in the system as a low-priority general information request.": "Selamı sisteme düşük öncelikli genel bilgi talebi olarak kaydedin.",
  'send a standard acknowledgment response (e.g., "selam, teşekkür ederiz.").': "Kısa bir karşılama yanıtı gönderin. Örneğin: Selam, teşekkür ederiz.",
  "classify the interaction under the müşteri bilgilendirme team as a simple greeting.": "Görüşmeyi basit bir selam olarak Müşteri Bilgilendirme ekibine yazın.",
  "do not escalate or assume any further intent until additional information is provided.": "Ek bilgi gelene kadar üst onaya çıkarmayın ve başka bir niyet varsaymayın.",
  "if the visitor follows up with a specific question, re-classify and route the request accordingly.": "Ziyaretçi ardından net bir soru sorarsa talebi yeniden sınıflandırıp ilgili ekibe yönlendirin.",
  "request details": "Talep ayrıntıları",
  "contact information": "İletişim bilgisi",
  "employee identification": "Çalışan kimliği",
};

const PHRASES: [string, string][] = [
  ["Authorized Healthcare Professional", "yetkili sağlık profesyoneli"],
  ["Sales / Operations", "Satış / Operasyon"],
  ["Sales/Operations", "Satış / Operasyon"],
  ["International Operations", "Uluslararası Operasyon"],
  ["Customer Information", "Müşteri Bilgilendirme"],
  ["Scheduling team", "randevu ekibi"],
  ["Scheduling", "randevu planlama"],
  ["escalation", "eskalasyon"],
  ["not_found", "bilgi tabanında yok"],
  ["Employee Knowledge", "çalışan bilgi kaynağı"],
];

export function fieldLabel(value: string): string {
  const known = FIELD_LABELS[fold(value)];
  return known ?? value;
}

function soften(value: string): string {
  return value
    .toLowerCase()
    .replace(/[\u2010\u2011\u2012\u2013\u2014]/g, "-")
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

export function localizeText(value: string): string {
  const folded = soften(value);
  const known = SENTENCES[folded];
  if (known) return known;
  const hinted = hintTurkish(folded);
  if (hinted) return hinted;
  return PHRASES.reduce((text, [from, to]) => text.replaceAll(from, to), value);
}

function hintTurkish(folded: string): string | null {
  if (folded.includes("record the greeting") || (folded.includes("greeting") && folded.includes("general information"))) {
    return "Selamı sisteme düşük öncelikli genel bilgi talebi olarak kaydedin.";
  }
  if (folded.includes("acknowledgment")) {
    return "Kısa bir karşılama yanıtı gönderin. Örneğin: Selam, teşekkür ederiz.";
  }
  if (folded.includes("do not escalate") || folded.includes("assume any further intent")) {
    return "Ek bilgi gelene kadar üst onaya çıkarmayın ve başka bir niyet varsaymayın.";
  }
  if (folded.includes("re-classify") || folded.includes("reclassify") || folded.includes("follows up")) {
    return "Ziyaretçi ardından net bir soru sorarsa talebi yeniden sınıflandırıp ilgili ekibe yönlendirin.";
  }
  if (folded.includes("simple greeting")) {
    return "Görüşmeyi basit bir selam olarak Müşteri Bilgilendirme ekibine yazın.";
  }
  return null;
}

const EXCERPT_RESPONSE = `Talep türü:
Yurt dışından gelen ziyaretçi için fiyat, tıbbi uygunluk ve randevu müsaitliği.

Öncelik:
Orta

Sorumlu ekip:
- Fiyat ve paket: Satış / Operasyon
- Tıbbi uygunluk: Yetkili sağlık profesyoneli
- Randevu müsaitliği: Randevu ekibi

Önerilen adımlar:
1. Fiyat sorusunu onay için Satış / Operasyon ekibine yönlendirin.
2. Tıbbi uygunluk değerlendirmesini yetkili sağlık profesyoneline iletin.
3. Randevu müsaitliğini randevu ekibiyle doğrulayın.
4. Seyahat, otel veya transfer sözü vermeyin. Bunlar açık operasyon onayı ister.
5. Müsaitlik veya fiyat varsaymayın. Yalnızca yazılı kaynaklara ya da insan onayına dayanın.

Üst onay:
Hayır. Bu, yazılı yönlendirme kurallarının içindedir. Yalnızca iç yönlendirme sonuçsuz kalırsa veya ekipler arasında bir engel çıkarsa üst onaya çıkarın.`;

const EXCERPT_PLAYBOOK = `4. Sıkı lojistik kuralı
Uçuş, otel, konaklama, havalimanı transferi, şehir içi ulaşım, vize desteği, seyahat ayarlama ve paket içeriği örnek hizmete kendiliğinden dahil değildir. Çalışan ya da yapay zeka, onaylı güncel bir kaynak o hizmeti açıkça doğrulamadan bunların sağlandığını, ayarlandığını, koordine edildiğini, ödendiğini veya pakete dahil olduğunu söylememelidir.

5. Örnek akış: Almanya saç ekimi talebi
Girdi: Almanya'dan bir ziyaretçi saç ekimi, fiyat, randevu zamanı, otel ve havalimanı transferi soruyor.
İç değerlendirme: Kategori = yurt dışı ziyaretçi + fiyat + randevu. Başka bir aciliyet yoksa öncelik üçüncü düzeydir. Genel süreç açık bilgiden yanıtlanabilir. Fiyat ve müsaitlik operasyon onayı ister. Otel ve transfer doğrulanmamış kabul edilir. Tıbbi uygunluk, meslek sahibi bir değerlendirme ister.
Önerilen devir: Uluslararası operasyon lojistiği doğrular. Randevu ekibi müsaitliği doğrular.`;

const EXCERPT_LEAD = `Talep edilen hizmet kategorisi ve asıl niyet netse kayıt takibe uygun işaretlenebilir. Tıbbi uygunluk, yapay zekanın kayıt eleme ölçütü değildir.
Yurt dışı ziyaretçide ülke ve tercih edilen dil yönlendirmeye yardımcı olabilir. Seyahat hizmetleri varsayılmamalıdır. Fiyat konusunda, güncel fiyatın onaylı bir kaynak veya insan onayı gerektirdiği belirtilmelidir.

4. Örnek iç kayıt
Kayıt numarası: 1042
Dil: İngilizce
Ülke: Almanya
Kategori: Yurt dışı ziyaretçi + fiyat
Aşama: Takibe uygun
Öncelik: Üçüncü düzey
Talep: Saç ekimiyle ilgileniyor. Güncel fiyat, randevu süreci ve konaklama soruyor.
Bilinen: Genel hizmet yolu bilgi tabanında vardır.
Bilinmeyen: Güncel fiyat, randevu müsaitliği, konaklama ve transfer seçenekleri.
Sonraki adım: Operasyon onayı için uluslararası operasyona yönlendirin. Kişiye özel tıbbi değerlendirmeyi ilgili uzmana bırakın.`;

export function presentExcerpt(text: string): string {
  const folded = text.toLowerCase();
  if (folded.includes("responsible team") || folded.includes("pricing, medical suitability")) {
    return EXCERPT_RESPONSE;
  }
  if (folded.includes("strict logistics") || folded.includes("germany hair transplant")) {
    return EXCERPT_PLAYBOOK;
  }
  if (folded.includes("qualified for follow-up") || folded.includes("lead-int-1042")) {
    return EXCERPT_LEAD;
  }
  return localizeText(text);
}

export function formatWhen(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("tr-TR", { dateStyle: "medium", timeStyle: "short" });
}

export function preview(value: string, limit = 88): string {
  const cleaned = value.replace(/\s+/g, " ").trim();
  if (cleaned.length <= limit) return cleaned;
  return `${cleaned.slice(0, limit).trimEnd()}…`;
}

const ROUTE_PATTERNS: { label: string; needles: string[] }[] = [
  { label: "Satış / Operasyon", needles: ["sales / operations", "sales/operations", "satış / operasyon"] },
  { label: "Yetkili sağlık profesyoneli", needles: ["authorized healthcare professional", "yetkili sağlık profesyoneli"] },
  { label: "Randevu planlama", needles: ["scheduling", "randevu ekibi", "randevu planlama"] },
  { label: "Uluslararası operasyon", needles: ["international operations", "uluslararası operasyon"] },
  { label: "Müşteri bilgilendirme", needles: ["customer information", "müşteri bilgilendirme"] },
];

export function routingMentions(parts: string[]): string[] {
  const blob = parts.join("\n").toLowerCase();
  return ROUTE_PATTERNS.filter((item) => item.needles.some((needle) => blob.includes(needle))).map(
    (item) => item.label,
  );
}

export function formatScore(score: number | null): string | null {
  if (score === null || Number.isNaN(score)) return null;
  return score.toFixed(2);
}
