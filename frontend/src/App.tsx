import { useEffect, useState, type ReactNode } from "react";
import {
  ArrowRight,
  Check,
  ChevronDown,
  Circle,
  UserRound,
  Users,
} from "lucide-react";
import { analyzeRequest, fetchHealth, type Analysis } from "./api";
import { documentTitle, fieldLabel, localizeText, priorityLabel } from "./format";

type Phase = "idle" | "running" | "done" | "error";
type Audience = "employee" | "client";

type ChatDraft = {
  requestText: string;
  phase: Phase;
  validation: string;
  error: string;
  analysis: Analysis | null;
  submitted: string;
};

const TEAM = [
  {
    given: "Elif",
    title: "Karşılama",
    photo: "/team/elif.png",
    role: "Talebi kapıda karşılar. Ne istendiğini ve ne kadar acil olduğunu ayırır.",
  },
  {
    given: "Kerem",
    title: "Bilgi",
    photo: "/team/kerem.png",
    role: "Resmi belgelere bakar. Cevabı belgede yazanla sınırlar.",
  },
  {
    given: "Selin",
    title: "Operasyon",
    photo: "/team/selin.png",
    role: "Belgeden sonraki adımı çıkarır. Çalışana ne yapacağını söyler.",
  },
  {
    given: "Emre",
    title: "Uygunluk",
    photo: "/team/emre.png",
    role: "Fiyat, randevu ve tıbbi karar uydurulmuş mu diye son kez bakar.",
  },
];

const EMPLOYEE_PLACEHOLDER = "Ziyaretçi talebini yazın...";
const CLIENT_PLACEHOLDER = "Sorunuzu yazın...";

const EMPLOYEE_GREETING =
  "Talep masasına hoş geldiniz. Ziyaretçi talebini yazın ya da bir örneği seçin. Resmi belgelere bakıp size nasıl ilerleyeceğinizi söyleyeyim.";
const CLIENT_GREETING =
  "Danışmaya hoş geldiniz. Sorunuzu yazın ya da bir örneği seçin. Yanıtı klinik belgelerinden veririm. Fiyat, randevu ve tıbbi kararı burada uydurmam.";

const EMPLOYEE_EXAMPLES = [
  {
    label: "Almanya'dan fiyat ve randevu",
    text: "Almanya'dan gelen bir ziyaretçi saç ekimi için fiyat, uygunluk ve en yakın randevu tarihini soruyor.",
  },
  {
    label: "İşlem günü ve bakım",
    text: "Hollanda'dan gelen bir ziyaretçi saç ekimi işlem gününün nasıl geçeceğini ve sonrası bakımı soruyor.",
  },
];
const CLIENT_EXAMPLES = [
  {
    label: "Saç ekimi süreci ve fiyat",
    text: "Almanya'dan geliyorum. Saç ekimi süreci nasıl ilerler? Fiyatı ve en yakın randevu ne zaman?",
  },
  {
    label: "İyileşme döneminde dikkat",
    text: "Saç ekimi sonrası ilk günlerde nelere dikkat etmeliyim?",
  },
];
const EMPLOYEE_ASSISTANTS = ["Karşılama", "Bilgi", "Operasyon", "Uygunluk"];

const EMPLOYEE_STAGES = [
  "Karşılama ajanı",
  "CrewAI",
  "Bilgi ajanı",
  "AnythingLLM",
  "Operasyon ajanı",
  "Uygunluk ajanı",
  "Yanıt",
];
const CLIENT_STAGES = ["Sorunuz alındı", "Bilgiler kontrol ediliyor", "Yanıt hazırlanıyor"];

function blankChat(): ChatDraft {
  return {
    requestText: "",
    phase: "idle",
    validation: "",
    error: "",
    analysis: null,
    submitted: "",
  };
}

export function App() {
  const [audience, setAudience] = useState<Audience>("employee");
  const [about, setAbout] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [employeeChat, setEmployeeChat] = useState<ChatDraft>(blankChat);
  const [clientChat, setClientChat] = useState<ChatDraft>(blankChat);
  const chat = audience === "client" ? clientChat : employeeChat;
  const forClient = audience === "client";

  useEffect(() => {
    let active = true;
    fetchHealth().then((ok) => {
      if (active) setOnline(ok);
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    document.title = forClient ? "EstetikAI — Danışma" : "EstetikAI — Talep masası";
  }, [forClient]);

  async function onAnalyze() {
    const setChat = forClient ? setClientChat : setEmployeeChat;
    const cleaned = chat.requestText.trim();
    if (!cleaned) {
      setChat((prev) => ({
        ...prev,
        validation: forClient ? "Önce sorunuzu yazın." : "Analizden önce bir ziyaretçi talebi yazın.",
        error: "",
      }));
      return;
    }
    setChat((prev) => ({
      ...prev,
      validation: "",
      error: "",
      phase: "running",
      analysis: null,
      submitted: cleaned,
      requestText: "",
    }));
    try {
      const result = await analyzeRequest(cleaned, forClient ? "client" : "employee");
      setChat((prev) => ({ ...prev, analysis: result, phase: "done" }));
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Yanıtı tamamlayamadık. Lütfen yeniden deneyin.";
      console.error("Analysis request failed");
      setChat((prev) => ({ ...prev, error: message, phase: "error" }));
    }
  }

  return (
    <div className={`${forClient ? "shell audience-client" : "shell audience-employee"}${about ? " about-open" : ""}`}>
      <aside className="sidebar">
        <div className="brand">
          <span className="mark" aria-hidden="true">
            E
          </span>
          <div>
            <p className="brand-name">EstetikAI</p>
            <p className="brand-sub">{forClient ? "Danışma" : "Talep masası"}</p>
          </div>
        </div>
        <button
          type="button"
          className={about ? "meet-button on" : "meet-button"}
          aria-expanded={about}
          onClick={() => setAbout((open) => !open)}
        >
          <Users size={18} strokeWidth={1.75} />
          <span>
            <span className="meet-title">Bizi tanıyın</span>
            <span className="meet-hint">Ekip ve araçlar</span>
          </span>
        </button>
        <div className="sidebar-foot">
          <div className="audience" role="group" aria-label="Panel seçimi">
            <button
              type="button"
              className={forClient ? "" : "on"}
              onClick={() => setAudience("employee")}
            >
              Çalışan
            </button>
            <button
              type="button"
              className={forClient ? "on" : ""}
              onClick={() => setAudience("client")}
            >
              Danışan
            </button>
          </div>
          <div className="mode">
            <UserRound size={16} strokeWidth={1.75} />
            <div>
              <p className="mode-label">{forClient ? "Danışma" : "Talep masası"}</p>
              <p className="mode-value">{forClient ? "Kendi sorunuz" : "Kurum içi kullanım"}</p>
            </div>
          </div>
          <div className="status">
            <Circle size={8} className={online ? "status-dot online" : "status-dot"} />
            <div>
              <p className="mode-label">Sistem Durumu</p>
              <p className="mode-value">
                {online === null ? "Kontrol ediliyor" : online ? "Servis çevrimiçi" : "Servis erişilemiyor"}
              </p>
            </div>
          </div>
        </div>
      </aside>
      <main className="main">
        {about ? <AboutScreen onClose={() => setAbout(false)} /> : null}
        {!about ? (
        <RequestCenter
          audience={audience}
          requestText={chat.requestText}
          submitted={chat.submitted}
          phase={chat.phase}
          validation={chat.validation}
          error={chat.error}
          analysis={chat.analysis}
          onChange={(value) => {
            const setChat = forClient ? setClientChat : setEmployeeChat;
            setChat((prev) => ({ ...prev, requestText: value }));
          }}
          onAnalyze={onAnalyze}
        />
        ) : null}
      </main>
    </div>
  );
}

function AboutScreen({ onClose }: { onClose: () => void }) {
  return (
    <div className="about-page">
      <div className="page">
        <div className="about-top">
          <header className="page-head">
            <p className="eyebrow">Bizi tanıyın</p>
            <h1>Sohbetin arkası</h1>
            <p className="lede">
              Çalışan talebini Elif, Kerem, Selin ve Emre sırayla hazırlar. Danışanın yanıtı halka açık belgelerden gelir.
              İşi CrewAI geçirir. Belgeler AnythingLLM’de durur.
            </p>
          </header>
          <button type="button" className="text-button" onClick={onClose}>
            Sohbete dön
          </button>
        </div>
        <ol className="team">
            {TEAM.map((person) => (
              <li key={person.given} className="person">
                <img src={person.photo} alt={`${person.given}, ${person.title}`} />
                <div>
                  <p className="team-name">{person.given}</p>
                  <p className="team-title">{person.title}</p>
                  <p className="team-role">{person.role}</p>
                </div>
              </li>
            ))}
        </ol>
        <section className="tool-grid">
          <article className="panel">
            <h2>CrewAI</h2>
            <p>
              Hazır ekip düzenidir. Elif işi Kerem’e, Kerem Selin’e, Selin Emre’ye bırakır. Sırayı CrewAI yürütür.
            </p>
          </article>
          <article className="panel">
            <h2>AnythingLLM</h2>
            <p>
              Hazır belge asistanıdır. Klinik belgeleri orada durur. Kerem oraya sorar, belgede yazanı ve belge adını getirir.
            </p>
          </article>
        </section>
      </div>
    </div>
  );
}

function asksRestricted(text: string): boolean {
  const folded = text.toLocaleLowerCase("tr");
  return ["fiyat", "ücret", "randevu", "uygunluk", "doktor", "hekim", "paket", "otel", "konaklama", "transfer", "teşhis", "garanti"].some(
    (word) => folded.includes(word),
  );
}

function clientAsk(item: string): string | null {
  const folded = `${item} ${localizeText(item)}`.toLocaleLowerCase("tr");
  if (folded.includes("employee") || folded.includes("çalışan kim")) return null;
  if (folded.includes("contact") || folded.includes("iletişim") || folded.includes("e-posta") || folded.includes("telefon")) {
    return "Size dönüş için telefon veya e-posta yazar mısınız?";
  }
  if (folded.includes("request detail") || folded.includes("talep ayrınt") || folded.includes("hangi işlem")) {
    return "Hangi işlem hakkında konuşmak istediğinizi yazar mısınız?";
  }
  return localizeText(item);
}

function readableAnswer(text: string): string {
  return text.replace(/\*\*/g, "").trim();
}

function clientReply(analysis: Analysis, submitted: string): string {
  const topic = fieldLabel(analysis.category);
  const named = topic && topic !== "Belirtilmedi" && topic.toLowerCase() !== "unspecified";
  const human = analysis.anythingllm_error || (analysis.escalation_required && asksRestricted(submitted));
  const parts = [
    "Ben kliniğin danışan asistanıyım. Size klinik belgelerinden yanıt veriyorum.",
    named ? `Sorunuz: ${topic}.` : "Sorunuzu aldım.",
  ];
  if (analysis.anythingllm_error) {
    parts.push("Şu an klinik belgelerine ulaşamadım. Bir klinik yetkilisi size dönüş yapacak.");
  } else if (human) {
    parts.push(
      "Belgelerimiz bu soruda net bir fiyat, randevu günü veya tıbbi uygunluk vermiyor. Bunları klinik yetkilisi söyler. Ben burada uydurmam.",
    );
  } else {
    parts.push("Belgelerimize göre bu sorunuzu genel bilgi olarak yanıtlayabilirim. Size özel fiyat veya tıbbi karar yazmam.");
  }
  const asks = analysis.missing_information.map(clientAsk).filter((item): item is string => Boolean(item));
  const unique = [...new Set(asks)];
  if (unique.length > 0) {
    parts.push(`Devam etmek için şunları yazabilirsiniz:\n${unique.map((item) => `• ${item}`).join("\n")}`);
  }
  return parts.join("\n\n");
}

function RequestCenter({
  audience,
  requestText,
  submitted,
  phase,
  validation,
  error,
  analysis,
  onChange,
  onAnalyze,
}: {
  audience: Audience;
  requestText: string;
  submitted: string;
  phase: Phase;
  validation: string;
  error: string;
  analysis: Analysis | null;
  onChange: (value: string) => void;
  onAnalyze: () => void;
}) {
  const running = phase === "running";
  const forClient = audience === "client";
  const stages = forClient ? CLIENT_STAGES : EMPLOYEE_STAGES;
  const role = forClient ? "Danışan asistanı" : "Çalışan asistanı";

  return (
    <div className="chat-screen">
      <header className="chat-top">
        <span className="mark" aria-hidden="true">
          E
        </span>
        <div>
          <p className="desk-title">{forClient ? "Danışma" : "Talep masası"}</p>
          <p className="mode-value">{role}</p>
        </div>
      </header>

      <div className="chat-body">
      <div className="chat-log" aria-live="polite">
        <AssistantBubble role={role}>
          <p>{forClient ? CLIENT_GREETING : EMPLOYEE_GREETING}</p>
        </AssistantBubble>
        {submitted ? <UserBubble text={submitted} label={forClient ? "Danışan" : "Çalışan"} /> : null}
        {running ? (
          <AssistantBubble role={role}>
            <StageList stages={stages} />
          </AssistantBubble>
        ) : null}
        {phase === "done" ? (
          <AssistantBubble role={role}>
            <StageFold
              title={forClient ? "Belgeler kontrol edildi" : "Dört asistan baktı"}
              stages={forClient ? CLIENT_STAGES : EMPLOYEE_ASSISTANTS}
            />
          </AssistantBubble>
        ) : null}
        {phase === "done" && analysis ? (
          <AssistantBubble role={role}>
            {forClient ? <ClientLetter analysis={analysis} submitted={submitted} /> : <EmployeeSheet analysis={analysis} submitted={submitted} />}
          </AssistantBubble>
        ) : null}
        {phase === "error" ? (
          <AssistantBubble role={role}>
            <p>{error}</p>
          </AssistantBubble>
        ) : null}
      </div>
      </div>

      <form
        className="chat-bar"
        onSubmit={(event) => {
          event.preventDefault();
          onAnalyze();
        }}
      >
        <label className="visually-hidden" htmlFor="visitor-request">
          {forClient ? "Sorunuz" : "Ziyaretçi talebi"}
        </label>
        <textarea
          id="visitor-request"
          rows={1}
          value={requestText}
          placeholder={forClient ? CLIENT_PLACEHOLDER : EMPLOYEE_PLACEHOLDER}
          disabled={running}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onAnalyze();
            }
          }}
        />
        <button type="submit" className="primary" disabled={running}>
          {running ? "Yazıyor" : "Gönder"}
          <ArrowRight size={16} strokeWidth={1.75} />
        </button>
      </form>
      {running ? null : (
        <ExampleChips items={forClient ? CLIENT_EXAMPLES : EMPLOYEE_EXAMPLES} onPick={onChange} />
      )}
      {validation ? <p className="field-error">{validation}</p> : null}
    </div>
  );
}

function sourceNames(analysis: Analysis): string[] {
  const names = analysis.knowledge_sources
    .map((source) => source.title.trim())
    .filter((title) => title.toLowerCase() !== "anythingllm textresponse")
    .map((title) => documentTitle(title));
  return [...new Set(names)];
}

function EmployeeSheet({ analysis, submitted }: { analysis: Analysis; submitted: string }) {
  const human = analysis.escalation_required && asksRestricted(submitted);
  const actions = analysis.recommended_actions.map((item) => localizeText(item)).filter(Boolean);
  const next = analysis.anythingllm_error
    ? "Talebi bir yetkiliye bırakın."
    : actions[0] || "Talebi kayda geçirin.";
  const approval = analysis.anythingllm_error ? "Belgeye ulaşılamadı" : human ? "Gerekli" : "Gerekmiyor";
  const rest = actions.slice(1);
  const gaps = analysis.missing_information.map((item) => localizeText(item)).filter(Boolean);
  const documents = sourceNames(analysis);

  return (
    <div className="answer-sheet">
      <p className="reply-role staff">Çalışana, resmi belgelerden</p>
      <dl className="answer-rows">
        <div>
          <dt>Talep türü</dt>
          <dd>{fieldLabel(analysis.request_type)}</dd>
        </div>
        <div>
          <dt>Öncelik</dt>
          <dd>{priorityLabel(analysis.priority)}</dd>
        </div>
        <div>
          <dt>Sonraki adım</dt>
          <dd>{next}</dd>
        </div>
        <div>
          <dt>İnsan onayı</dt>
          <dd>{approval}</dd>
        </div>
        <div>
          <dt>Resmi belgeler</dt>
          <dd>{documents.length > 0 ? documents.join(", ") : "Belge adı gelmedi."}</dd>
        </div>
      </dl>
      {rest.length > 0 ? (
        <>
          <p className="sheet-label">Diğer adımlar</p>
          <ul className="follow-list">
            {rest.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
      {gaps.length > 0 ? (
        <>
          <p className="sheet-label">Ziyaretçiden öğrenilecekler</p>
          <ul className="follow-list">
            {gaps.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}

function ClientLetter({ analysis, submitted }: { analysis: Analysis; submitted: string }) {
  const letter = readableAnswer(analysis.direct_answer) || clientReply(analysis, submitted);
  const documents = sourceNames(analysis);
  return (
    <div className="answer-sheet">
      <p className="reply-role">Danışana</p>
      <TypedReply text={letter} />
      <p className="letter-foot">Klinik belgelerinden{documents.length > 0 ? ` · ${documents.join(", ")}` : ""}</p>
    </div>
  );
}

function ExampleChips({
  items,
  onPick,
}: {
  items: { label: string; text: string }[];
  onPick: (text: string) => void;
}) {
  return (
    <div className="examples">
      {items.map((item) => (
        <button key={item.label} type="button" className="example" onClick={() => onPick(item.text)}>
          {item.label}
        </button>
      ))}
    </div>
  );
}

function StageFold({ title, stages }: { title: string; stages: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="stage-fold">
      <button type="button" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <span className="tick checked" aria-hidden="true">
          <Check size={11} strokeWidth={2.75} />
        </span>
        {title}
        <ChevronDown size={14} strokeWidth={1.75} className={open ? "fold-open" : undefined} />
      </button>
      {open ? (
        <ol className="stage-list">
          {stages.map((label) => (
            <li key={label} className="checked">
              <span className="tick" aria-hidden="true">
                <Check size={11} strokeWidth={2.75} />
              </span>
              <span>{label}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

function AssistantBubble({ children, role }: { children: ReactNode; role: string }) {
  return (
    <div className="turn assistant">
      <span className="mark small" aria-hidden="true">
        E
      </span>
      <div>
        <p className="who">{role}</p>
        <div className="bubble">{children}</div>
      </div>
    </div>
  );
}

function UserBubble({ text, label }: { text: string; label: string }) {
  return (
    <div className="turn user">
      <div>
        <p className="who">{label}</p>
        <div className="bubble">{text}</div>
      </div>
    </div>
  );
}

function StageList({ stages }: { stages: string[] }) {
  const [shown, setShown] = useState(1);
  const [typed, setTyped] = useState(0);
  const [checked, setChecked] = useState(0);

  useEffect(() => {
    const label = stages[shown - 1];
    if (!label) return;
    if (typed < label.length) {
      const timer = window.setTimeout(() => setTyped((current) => current + 1), 36);
      return () => window.clearTimeout(timer);
    }
    if (checked < shown) {
      const timer = window.setTimeout(() => setChecked(shown), 220);
      return () => window.clearTimeout(timer);
    }
    if (shown < stages.length) {
      const timer = window.setTimeout(() => {
        setShown((current) => current + 1);
        setTyped(0);
      }, 360);
      return () => window.clearTimeout(timer);
    }
  }, [checked, shown, stages, typed]);

  return (
    <ol className="stage-list">
      {stages.slice(0, shown).map((label, index) => {
        const writing = index === shown - 1 && typed < label.length;
        const text = writing ? label.slice(0, typed) : label;
        const on = index < checked;
        return (
          <li key={label} className={on ? "checked" : undefined}>
            <span className="tick" aria-hidden="true">
              {on ? <Check size={11} strokeWidth={2.75} /> : null}
            </span>
            <span>
              {text}
              {writing ? <span className="caret" aria-hidden="true" /> : null}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function TypedReply({ text }: { text: string }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    setCount(0);
    const timer = window.setInterval(() => {
      setCount((current) => {
        if (current >= text.length) {
          window.clearInterval(timer);
          return current;
        }
        return current + 1;
      });
    }, 18);
    return () => window.clearInterval(timer);
  }, [text]);

  const done = count >= text.length;
  return (
    <p>
      {text.slice(0, count)}
      {done ? null : <span className="caret" aria-hidden="true" />}
    </p>
  );
}
