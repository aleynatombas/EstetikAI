import { useEffect, useState, type ReactNode } from "react";
import { BookOpen } from "lucide-react";
import {
  fetchActivity,
  fetchEscalations,
  fetchKnowledge,
  fetchRequest,
  fetchRequests,
  type ActivityEvent,
  type Analysis,
  type EscalationReport,
  type KnowledgeCatalog,
  type RequestSummary,
  type SavedRequest,
} from "./api";
import {
  documentTitle,
  fieldLabel,
  formatScore,
  formatWhen,
  localizeText,
  presentExcerpt,
  preview,
  priorityLabel,
  priorityTone,
  routingMentions,
  splitVerified,
} from "./format";

const EVENT_LABELS: Record<string, string> = {
  request_received: "Talep alındı",
  analysis_completed: "Yapay zeka analizi tamamlandı",
  knowledge_sources_used: "Bilgi kaynakları kullanıldı",
  escalation_created: "Eskalasyon oluşturuldu",
};

export function AnalysisPanels({
  analysis,
  submitted,
  showRouting,
}: {
  analysis: Analysis;
  submitted?: string;
  showRouting?: boolean;
}) {
  const tone = priorityTone(analysis.priority);
  const routes = showRouting
    ? routingMentions([
        ...analysis.recommended_actions,
        ...analysis.verified_information,
        analysis.reason,
      ])
    : [];
  return (
    <div className="result">
      <section className="summary">
        <div>
          <p className="meta-label">Talep Türü</p>
          <p className="meta-value">{fieldLabel(analysis.request_type)}</p>
        </div>
        <div>
          <p className="meta-label">Kategori</p>
          <p className="meta-value">{fieldLabel(analysis.category)}</p>
        </div>
        <div>
          <p className="meta-label">Öncelik</p>
          <p className={`badge ${tone}`}>{priorityLabel(analysis.priority)}</p>
        </div>
      </section>

      {submitted ? (
        <p className="submitted">
          <span>Orijinal talep</span>
          {submitted}
        </p>
      ) : null}

      {analysis.anythingllm_error ? (
        <section className="notice error" role="alert">
          <h2>Çalışan bilgi kaynağına ulaşılamadı</h2>
          <p>Bilgi çalışma alanı sorgulanamadı. Kaynak dışında kurumsal bilgi eklenmedi.</p>
        </section>
      ) : null}

      <section className="panel verified">
        <div className="panel-head">
          <h2>Doğrulanmış Bilgiler</h2>
          <p>Kurumsal belgelerden olduğu gibi alınan alıntılar.</p>
        </div>
        {analysis.verified_information.length === 0 ? (
          <p className="empty">Doğrulanmış kurumsal bilgi dönmedi.</p>
        ) : (
          <ul className="facts">
            {analysis.verified_information.map((item) => {
              const fact = splitVerified(item);
              return (
                <li key={item}>
                  <p className="fact-source">{documentTitle(fact.source)}</p>
                  <p className="fact-text">{presentExcerpt(fact.text || item)}</p>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="split">
        <article className="panel">
          <div className="panel-head">
            <h2>Eksik Bilgiler</h2>
            <p>Çalışanın hâlâ toplaması gereken ayrıntılar.</p>
          </div>
          {analysis.missing_information.length === 0 ? (
            <p className="empty">Eksik bilgi kaydı yok.</p>
          ) : (
            <ul className="plain-list">
              {analysis.missing_information.map((item) => (
                <li key={item}>{localizeText(item)}</li>
              ))}
            </ul>
          )}
        </article>
        <article className="panel">
          <div className="panel-head">
            <h2>Önerilen Aksiyonlar</h2>
            <p>Doğrulanmış yanıta dayanan operasyon adımları.</p>
          </div>
          {analysis.recommended_actions.length === 0 ? (
            <p className="empty">Operasyon adımı dönmedi.</p>
          ) : (
            <ol className="actions">
              {analysis.recommended_actions.map((item, index) => (
                <li key={item}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <p>{localizeText(item)}</p>
                </li>
              ))}
            </ol>
          )}
        </article>
      </section>

      {routes.length > 0 ? (
        <section className="panel">
          <div className="panel-head">
            <h2>Önerilen yönlendirmeler</h2>
            <p>Yanıt metninde açıkça geçen ekipler.</p>
          </div>
          <ul className="routes">
            {routes.map((route) => (
              <li key={route}>{route}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className={analysis.escalation_required ? "escalation required" : "escalation clear"}>
        <p className="eyebrow">Eskalasyon Durumu</p>
        <h2>{analysis.escalation_required ? "İnsan onayı gerekli" : "İnsan onayı gerekmiyor"}</h2>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Eskalasyon Nedeni</h2>
        </div>
        <p className="reason">{localizeText(analysis.reason) || "Yanıt bir gerekçe içermiyor."}</p>
      </section>

      {analysis.knowledge_sources.length > 0 ? (
        <section className="panel">
          <div className="panel-head">
            <h2>Kullanılan Bilgi Kaynakları</h2>
            <p>Çalışan bilgi kaynağının işaret ettiği belgeler.</p>
          </div>
          <ul className="sources">
            {analysis.knowledge_sources.map((source) => {
              const score = formatScore(source.score);
              return (
                <li key={source.title}>
                  <BookOpen size={16} strokeWidth={1.75} />
                  <div>
                    <p className="source-title">{documentTitle(source.title)}</p>
                    <p className="source-meta">{score ? `Benzerlik ${score}` : "Bilgi kaynağı"}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

export function RequestsPage() {
  const [items, setItems] = useState<RequestSummary[] | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<SavedRequest | null>(null);
  const [detailError, setDetailError] = useState("");

  useEffect(() => {
    let active = true;
    fetchRequests()
      .then((records) => {
        if (active) setItems(records);
      })
      .catch((caught: unknown) => {
        console.error("Request list failed");
        if (active) setError(caught instanceof Error ? caught.message : "Kayıtlar alınamadı.");
      });
    return () => {
      active = false;
    };
  }, []);

  async function openRecord(id: string) {
    setDetailError("");
    try {
      setSelected(await fetchRequest(id));
    } catch (caught) {
      console.error("Request detail failed");
      setDetailError(caught instanceof Error ? caught.message : "Talep ayrıntısı alınamadı.");
    }
  }

  return (
    <Page
      eyebrow="Operasyon"
      title="İstekler"
      lede="Yapay zeka tarafından analiz edilen ziyaretçi taleplerini görüntüleyin."
    >
      {error ? <Notice title="Kayıtlar alınamadı" body={error} /> : null}
      {detailError ? <Notice title="Ayrıntı alınamadı" body={detailError} /> : null}
      {items === null && !error ? <p className="empty">Kayıtlar yükleniyor.</p> : null}
      {items && items.length === 0 ? (
        <section className="panel">
          <p className="empty">Henüz analiz edilmiş bir talep bulunmuyor.</p>
        </section>
      ) : null}
      {items && items.length > 0 ? (
        <section className="panel list-panel">
          <div className="record record-head" aria-hidden="true">
            <span>Talep</span>
            <span>Kategori</span>
            <span>Öncelik</span>
            <span>Durum</span>
            <span>Eskalasyon</span>
            <span>Tarih</span>
          </div>
          {items.map((item) => (
            <button key={item.id} type="button" className="record" onClick={() => openRecord(item.id)}>
              <span className="record-request">{preview(item.original_request)}</span>
              <span>{fieldLabel(item.category)}</span>
              <span className={`badge inline ${priorityTone(item.priority)}`}>{priorityLabel(item.priority)}</span>
              <span>{item.anythingllm_error ? "Bilgi kaynağı hatası" : "Analiz tamamlandı"}</span>
              <span>{item.escalation_required ? "İnsan onayı gerekli" : "Onay gerekmiyor"}</span>
              <span>{formatWhen(item.created_at)}</span>
            </button>
          ))}
        </section>
      ) : null}
      {selected ? (
        <Drawer title="Talep ayrıntısı" onClose={() => setSelected(null)}>
          <AnalysisPanels analysis={selected} submitted={selected.original_request} showRouting />
        </Drawer>
      ) : null}
    </Page>
  );
}

export function KnowledgePage() {
  const [catalog, setCatalog] = useState<KnowledgeCatalog | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchKnowledge()
      .then((value) => {
        if (active) setCatalog(value);
      })
      .catch((caught: unknown) => {
        console.error("Knowledge catalog failed");
        if (active) setError(caught instanceof Error ? caught.message : "Bilgi kaynakları alınamadı.");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Page
      eyebrow="Kurumsal bilgi"
      title="Bilgi Merkezi"
      lede="Yapay zeka ajanlarının yanıt oluştururken kullandığı doğrulanmış kurumsal bilgi kaynakları."
    >
      {error ? <Notice title="Bilgi kaynağı alınamadı" body={error} /> : null}
      {catalog ? (
        <section className="summary">
          <div>
            <p className="meta-label">Bilgi tabanı</p>
            <p className="meta-value">{catalog.connected ? "Bağlı" : "Bağlı değil"}</p>
          </div>
          <div>
            <p className="meta-label">Çalışma alanı</p>
            <p className="meta-value source-title">Çalışan bilgi alanı</p>
          </div>
          {catalog.workspace_name ? (
            <div>
              <p className="meta-label">Ad</p>
              <p className="meta-value source-title">
                {catalog.workspace_name.replace("Employee Knowledge", "Çalışan Bilgi Kaynağı")}
              </p>
            </div>
          ) : null}
        </section>
      ) : null}
      <p className="note">
        Bu kaynaklar bilgi ajanı tarafından çalışan bilgi kaynağında aranır ve yalnızca ilgili bilgi parçaları ajanlara aktarılır.
      </p>
      {catalog && !catalog.connected ? (
        <section className="panel">
          <p className="empty">Çalışma alanına şu an ulaşılamıyor.</p>
        </section>
      ) : null}
      {catalog && catalog.documents.length === 0 ? (
        <section className="panel">
          <p className="empty">Gösterilecek kurumsal belge bulunmuyor.</p>
        </section>
      ) : null}
      {catalog && catalog.documents.length > 0 ? (
        <ul className="documents">
          {catalog.documents.map((document) => (
            <li key={document.title} className="panel document">
              <p className="source-title">{documentTitle(document.title)}</p>
              <p className="source-meta">Tür · Belge</p>
              <p className="source-meta">
                {document.use_count > 0
                  ? `${document.use_count} analizde kullanıldı`
                  : "Henüz bir analizde kullanılmadı"}
              </p>
              {document.last_request_preview ? (
                <p className="source-meta">Son kullanım · {preview(document.last_request_preview, 72)}</p>
              ) : null}
              {document.last_used_at ? <p className="source-meta">{formatWhen(document.last_used_at)}</p> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </Page>
  );
}

export function EscalationsPage() {
  const [report, setReport] = useState<EscalationReport | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<SavedRequest | null>(null);

  useEffect(() => {
    let active = true;
    fetchEscalations()
      .then((value) => {
        if (active) setReport(value);
      })
      .catch((caught: unknown) => {
        console.error("Escalation list failed");
        if (active) setError(caught instanceof Error ? caught.message : "Eskalasyonlar alınamadı.");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Page
      eyebrow="İnsan onayı"
      title="Eskalasyonlar"
      lede="İnsan müdahalesi gereken analizler."
    >
      {error ? <Notice title="Eskalasyonlar alınamadı" body={error} /> : null}
      {report ? (
        <section className="summary">
          <div>
            <p className="meta-label">Açık eskalasyonlar</p>
            <p className="meta-value">{report.open_count}</p>
          </div>
          <div>
            <p className="meta-label">Yüksek öncelik</p>
            <p className="meta-value">{report.high_count}</p>
          </div>
          <div>
            <p className="meta-label">Orta öncelik</p>
            <p className="meta-value">{report.medium_count}</p>
          </div>
        </section>
      ) : null}
      {report && report.items.length === 0 ? (
        <section className="panel">
          <p className="empty">Henüz insan müdahalesi gerektiren bir talep bulunmuyor.</p>
        </section>
      ) : null}
      {report && report.items.length > 0 ? (
        <section className="panel list-panel">
          <div className="record escalation-record record-head" aria-hidden="true">
            <span>Talep</span>
            <span>Kategori</span>
            <span>Öncelik</span>
            <span>Eskalasyon nedeni</span>
            <span>Oluşturulma tarihi</span>
          </div>
          {report.items.map((item) => (
            <button
              key={item.id}
              type="button"
              className="record escalation-record"
              onClick={() => setSelected(item)}
            >
              <span className="record-request">{preview(item.original_request)}</span>
              <span>{fieldLabel(item.category)}</span>
              <span className={`badge inline ${priorityTone(item.priority)}`}>{priorityLabel(item.priority)}</span>
              <span>{localizeText(preview(item.reason, 96))}</span>
              <span>{formatWhen(item.created_at)}</span>
            </button>
          ))}
        </section>
      ) : null}
      {selected ? (
        <Drawer title="Eskalasyon ayrıntısı" onClose={() => setSelected(null)}>
          <AnalysisPanels analysis={selected} submitted={selected.original_request} showRouting />
        </Drawer>
      ) : null}
    </Page>
  );
}

export function ActivityPage({ onOpen }: { onOpen: (id: string) => void }) {
  const [events, setEvents] = useState<ActivityEvent[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchActivity()
      .then((value) => {
        if (active) setEvents(value);
      })
      .catch((caught: unknown) => {
        console.error("Activity list failed");
        if (active) setError(caught instanceof Error ? caught.message : "Aktivite alınamadı.");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Page eyebrow="Kayıt" title="Aktivite" lede="Sistemde gerçekleşmiş uygulama olayları.">
      {error ? <Notice title="Aktivite alınamadı" body={error} /> : null}
      {events && events.length === 0 ? (
        <section className="panel">
          <p className="empty">Henüz kayıtlı bir olay bulunmuyor.</p>
        </section>
      ) : null}
      {events && events.length > 0 ? (
        <ol className="timeline">
          {events.map((event) => (
            <li key={event.id}>
              <button type="button" onClick={() => onOpen(event.request_id)}>
                <p className="arch-title">{EVENT_LABELS[event.event_type] ?? event.event_type}</p>
                <p className="arch-detail">{preview(event.request_preview, 120)}</p>
                <p className="source-meta">{formatWhen(event.created_at)}</p>
              </button>
            </li>
          ))}
        </ol>
      ) : null}
    </Page>
  );
}

export function RequestDrawerLoader({ id, onClose }: { id: string; onClose: () => void }) {
  const [record, setRecord] = useState<SavedRequest | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchRequest(id)
      .then((value) => {
        if (active) setRecord(value);
      })
      .catch((caught: unknown) => {
        console.error("Activity request detail failed");
        if (active) setError(caught instanceof Error ? caught.message : "Talep ayrıntısı alınamadı.");
      });
    return () => {
      active = false;
    };
  }, [id]);

  return (
    <Drawer title="Talep ayrıntısı" onClose={onClose}>
      {error ? <Notice title="Ayrıntı alınamadı" body={error} /> : null}
      {record ? <AnalysisPanels analysis={record} submitted={record.original_request} showRouting /> : null}
      {!record && !error ? <p className="empty">Ayrıntı yükleniyor.</p> : null}
    </Drawer>
  );
}

function Page({
  eyebrow,
  title,
  lede,
  children,
}: {
  eyebrow: string;
  title: string;
  lede: string;
  children: ReactNode;
}) {
  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="lede">{lede}</p>
      </header>
      {children}
    </div>
  );
}

function Notice({ title, body }: { title: string; body: string }) {
  return (
    <section className="notice error" role="alert">
      <h2>{title}</h2>
      <p>{body}</p>
    </section>
  );
}

function Drawer({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="drawer-backdrop" role="presentation" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="drawer-bar">
          <h2>{title}</h2>
          <button type="button" className="text-button" onClick={onClose}>
            Kapat
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}
