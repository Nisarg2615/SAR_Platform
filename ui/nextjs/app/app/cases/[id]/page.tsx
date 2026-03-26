'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { sarApi, SARCase, AccountAuditTrail } from '@/lib/api';
import { RiskBadge, StatusBadge } from '@/components/RiskBadge';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import {
  ArrowLeft, Download, FileText, CheckCircle, XCircle, Loader,
  Copy, Check, Lock, Clock, Shield, AlertTriangle, ChevronDown, ChevronUp, User, Play
} from 'lucide-react';

const TABS = ['Overview', 'Risk Analysis', 'SAR Report', 'Compliance', 'Audit Trail'];

const card: React.CSSProperties = {
  background: '#111',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 16,
  padding: 20,
};

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<SARCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('Overview');
  const [running, setRunning] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [groqLabel, setGroqLabel] = useState('');
  const [analyst, setAnalyst] = useState('Analyst-1');
  const [approving, setApproving] = useState(false);
  const [dismissing, setDismissing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [accountHistory, setAccountHistory] = useState<AccountAuditTrail | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState('');
  
  // Feature 3: Editable SAR Report State
  const [reportData, setReportData] = useState<SARReportData | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  
  // Collapsible section state for the report
  const [secOpen, setSecOpen] = useState({ 
    filing: true, subject: false, typology: false, narrative: true 
  });
  
  const reportRef = useRef<HTMLDivElement>(null);

  const reload = async () => {
    try { setData(await sarApi.getCase(id)); } catch { /* 404 */ }
    setLoading(false);
  };
  useEffect(() => { reload(); }, [id]);

  const runPipeline = async () => {
    if (!data || running) return;
    setRunning(true);
    try {
      await sarApi.runPipeline(id);
      await reload();
    } catch (e) {
      console.error(e);
      alert('Pipeline failed');
    } finally {
      setRunning(false);
    }
  };

  const generateNarrative = async () => {
    if (!data?.normalized || generating) return;
    setGenerating(true);
    setGroqLabel('Generating...');
    try {
      await sarApi.runPipeline(id);
      await reload();
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
      setGroqLabel('');
    }
  };

  useEffect(() => {
    if (tab === 'SAR Report' && data?.risk_assessment && !reportData) {
      setReportLoading(true);
      sarApi.getReportData(id).then(setReportData).finally(() => setReportLoading(false));
    }
  }, [tab, data, id, reportData]);

  const updateReport = (field: keyof SARReportData, value: any) => {
    setReportData(prev => prev ? { ...prev, [field]: value } as SARReportData : null);
  };

  const handleTypologyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    updateReport('typology', val);
    const codeMap: Record<string, string> = {
      'Structuring': 'Structuring (excl. smurfing)',
      'Layering': 'Layering',
      'Rapid Movement': 'Rapid Movement of Funds',
      'Smurfing': 'Smurfing',
      'High-Risk Geography': 'Transaction with High-Risk Geography',
      'TBML': 'Trade-Based Money Laundering',
      'Crypto Layering': 'Crypto Layering'
    };
    updateReport('typology_code', codeMap[val] || '');
  };

  const saveReport = async () => {
    if (!reportData) return;
    setSaving(true);
    try {
      await sarApi.saveReportData(id, reportData);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err) {
      console.error('Failed to save report:', err);
    } finally {
      setSaving(false);
    }
  };

  const downloadPDF = async () => {
    if (!data || !reportData) return;
    setPdfDownloading(true);
    try {
      const blob = await sarApi.downloadPdfFromServer(id, reportData);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `SAR-${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download PDF:', err);
      alert('Failed to generate PDF. Please ensure all report data is valid.');
    } finally {
      setPdfDownloading(false);
    }
  };

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200 }}>
      <Loader style={{ width: 18, height: 18, color: '#3b82f6', animation: 'spin 1s linear infinite' }} />
    </div>
  );

  if (!data) return (
    <div style={{ textAlign: 'center', padding: '80px 0' }}>
      <p style={{ color: '#3f3f46', fontSize: 13, marginBottom: 12 }}>Case not found</p>
      <button onClick={() => router.push('/app/cases')} style={{ color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer', fontSize: 13 }}>← Back to cases</button>
    </div>
  );

  const risk = data.risk_assessment;
  const narrative = data.narrative;
  const compliance = data.compliance;
  const audit = data.audit;
  const errors = data.error_log.filter(e => !e.error.includes('Neo4j write failed'));

  const reviewedCount = reportData ? [
    reportData.section_filing_reviewed,
    reportData.section_subject_reviewed,
    reportData.section_typology_reviewed,
    reportData.section_narrative_reviewed
  ].filter(Boolean).length : 0;
  
  const canDownload = reviewedCount === 4;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Back */}
      <button onClick={() => router.push('/app/cases')}
        style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#52525b', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, width: 'fit-content' }}>
        <ArrowLeft style={{ width: 13, height: 13 }} /> All Cases
      </button>

      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <h1 className="mono" style={{ fontSize: 20, fontWeight: 700, color: '#fff' }}>{id}</h1>
            <StatusBadge status={data.status} />
            {risk && <RiskBadge tier={risk.risk_tier} />}
          </div>
          <p style={{ fontSize: 13, color: '#52525b' }}>
            {data.normalized?.subject_name ?? 'Unknown'} · ${data.normalized?.total_amount_usd?.toLocaleString() ?? '0'} · {data.audit_trail.length} events
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {!data.normalized && (
            <button onClick={runPipeline} disabled={running}
              style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#2563eb', color: '#fff', padding: '8px 14px', borderRadius: 8, fontSize: 12, fontWeight: 500, cursor: 'pointer', border: 'none', opacity: running ? 0.6 : 1 }}>
              {running ? <Loader style={{ width: 13, height: 13, animation: 'spin 1s linear infinite' }} /> : <Play style={{ width: 13, height: 13 }} />}
              {running ? 'Running…' : 'Run Pipeline'}
            </button>
          )}
          {data.normalized && !narrative && risk?.risk_tier !== 'green' && (
            <button onClick={generateNarrative} disabled={generating}
              style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.25)', color: '#a78bfa', padding: '8px 14px', borderRadius: 8, fontSize: 12, fontWeight: 500, cursor: 'pointer', opacity: generating ? 0.6 : 1 }}>
              {generating ? <Loader style={{ width: 13, height: 13, animation: 'spin 1s linear infinite' }} /> : <FileText style={{ width: 13, height: 13 }} />}
              {generating ? groqLabel : 'Generate Narrative'}
            </button>
          )}
          {narrative && (
            <button onClick={downloadPDF}
              style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)', color: '#10b981', padding: '8px 14px', borderRadius: 8, fontSize: 12, fontWeight: 500, cursor: 'pointer' }}>
              <Download style={{ width: 13, height: 13 }} /> Download PDF
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)', gap: 0 }}>
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)} className={`tab ${tab === t ? 'active' : ''}`}>{t}</button>
        ))}
      </div>

      {/* ══ OVERVIEW ══ */}
      {tab === 'Overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div style={card}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <Shield style={{ width: 14, height: 14, color: '#52525b' }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>Pipeline Status</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                { label: 'Agent 1 — Ingestion', done: !!data.normalized },
                { label: 'Agent 2 — Risk Score', done: !!risk },
                { label: 'Agent 3 — Narrative', done: !!narrative },
                { label: 'Agent 4 — Compliance', done: !!compliance },
                { label: 'Agent 5 — Audit Hash', done: !!audit },
                { label: 'Agent 6 — Human Review', done: !!data.analyst_approved_by },
              ].map(({ label, done }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {done
                    ? <CheckCircle style={{ width: 14, height: 14, color: '#10b981', flexShrink: 0 }} />
                    : <div style={{ width: 14, height: 14, borderRadius: '50%', border: '1px solid #3f3f46', flexShrink: 0 }} />}
                  <span style={{ fontSize: 12, color: done ? '#e4e4e7' : '#3f3f46' }}>{label}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={card}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <FileText style={{ width: 14, height: 14, color: '#52525b' }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>Transaction Data</span>
            </div>
            {data.raw_transaction ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {Object.entries(data.raw_transaction).slice(0, 10).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                    <span style={{ fontSize: 10, color: '#3f3f46', textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0, textTransform: 'capitalize' as const }}>{k.replace(/_/g,' ')}</span>
                    <span style={{ fontSize: 12, color: '#a1a1aa', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis' }}>{String(v)}</span>
                  </div>
                ))}
              </div>
            ) : <span style={{ fontSize: 12, color: '#3f3f46' }}>No data</span>}
          </div>

          {errors.length > 0 && (
            <div style={{ ...card, borderColor: 'rgba(245,158,11,0.2)', gridColumn: '1/-1' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <AlertTriangle style={{ width: 14, height: 14, color: '#f59e0b' }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>Pipeline Warnings</span>
              </div>
              {errors.map((e, i) => (
                <div key={i} style={{ fontSize: 12, padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', lastChild: { borderBottom: 'none' } as React.CSSProperties }}>
                  <span style={{ color: '#52525b', marginRight: 8 }}>{e.agent}</span>
                  <span style={{ color: 'rgba(251,191,36,0.8)' }}>{e.error}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ══ RISK ANALYSIS ══ */}
      {tab === 'Risk Analysis' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {!risk ? <EmptyPanel msg="Run pipeline to see risk analysis" /> : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
                <div style={{ ...card, textAlign: 'center' }}>
                  <div style={{ fontSize: 36, fontWeight: 700, color: '#fff', marginBottom: 4 }}>
                    {(risk.risk_score * 100).toFixed(0)}<span style={{ fontSize: 16, color: '#52525b' }}>%</span>
                  </div>
                  <div style={{ fontSize: 11, color: '#52525b' }}>Risk Score</div>
                </div>
                <div style={{ ...card, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                  <RiskBadge tier={risk.risk_tier} size="lg" />
                  <div style={{ fontSize: 11, color: '#52525b' }}>Risk Tier</div>
                </div>
                <div style={{ ...card, textAlign: 'center' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#a78bfa', marginBottom: 4, textTransform: 'capitalize' }}>{risk.matched_typology}</div>
                  <div style={{ fontSize: 11, color: '#52525b', marginBottom: 4 }}>Matched Typology</div>
                  <div style={{ fontSize: 11, color: '#3f3f46' }}>{(risk.typology_confidence * 100).toFixed(0)}% conf</div>
                </div>
              </div>

              {Object.keys(risk.shap_values).length > 0 && (
                <div style={card}>
                  <h3 style={{ fontSize: 13, fontWeight: 600, color: '#fff', marginBottom: 16 }}>SHAP Feature Importance</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart
                      data={Object.entries(risk.shap_values).slice(0,8).map(([k,v]) => ({ name: k.replace(/_/g,' '), value: Math.abs(v as number), raw: v as number }))}
                      layout="vertical" margin={{ left: 0, right: 16 }}>
                      <XAxis type="number" tick={{ fill: '#52525b', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis type="category" dataKey="name" width={150} tick={{ fill: '#71717a', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#111', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontSize: 12 }}
                        formatter={(v: unknown, _: unknown, p: { payload?: { raw: number } }) => [Number(p.payload?.raw ?? v).toFixed(4), 'SHAP']} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {Object.values(risk.shap_values).slice(0,8).map((v, i) => (
                          <Cell key={i} fill={(v as number) > 0 ? '#3b82f6' : '#f43f5e'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <div style={{ display: 'flex', gap: 16, marginTop: 10 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#52525b' }}>
                      <span style={{ width: 8, height: 8, borderRadius: 2, background: '#3b82f6', display: 'inline-block' }} /> Increases risk
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#52525b' }}>
                      <span style={{ width: 8, height: 8, borderRadius: 2, background: '#f43f5e', display: 'inline-block' }} /> Decreases risk
                    </div>
                  </div>
                </div>
              )}

              {risk.signals.length > 0 && (
                <div style={card}>
                  <h3 style={{ fontSize: 13, fontWeight: 600, color: '#fff', marginBottom: 12 }}>Risk Signals</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {risk.signals.map((s, i) => (
                      <div key={i} style={{ display: 'flex', gap: 10, background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 10, padding: 12 }}>
                        <AlertTriangle style={{ width: 13, height: 13, color: '#f59e0b', flexShrink: 0, marginTop: 2 }} />
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 600, color: '#f59e0b', textTransform: 'capitalize', marginBottom: 3 }}>{s.signal_type}</div>
                          <div style={{ fontSize: 12, color: '#71717a' }}>{s.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ══ SAR REPORT (EDITABLE) ══ */}
      {tab === 'SAR Report' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {risk?.risk_tier === 'green' ? (
            <div style={{ ...card, textAlign: 'center', padding: 56 }}>
              <Shield style={{ display: 'inline-block', color: '#10b981', width: 26, height: 26, marginBottom: 16 }} />
              <p style={{ fontSize: 14, color: '#e4e4e7', marginBottom: 8, fontWeight: 500 }}>SAR Filing Not Required</p>
              <p style={{ fontSize: 13, color: '#a1a1aa' }}>This case was classified as GREEN (Low Risk). Regulatory reporting is automatically bypassed.</p>
            </div>
          ) : reportLoading ? (
            <div style={{ ...card, textAlign: 'center', padding: 56 }}>
              <Loader style={{ display: 'inline-block', color: '#71717a', width: 24, height: 24, animation: 'spin 1s linear infinite' }} />
              <p style={{ fontSize: 13, color: '#52525b', marginTop: 16 }}>Loading report data...</p>
            </div>
          ) : !reportData ? (
            <div style={{ ...card, textAlign: 'center', padding: 56 }}>
              <p style={{ fontSize: 13, color: '#52525b', marginBottom: 16 }}>Generate report data by running the pipeline.</p>
            </div>
          ) : (
            <>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 4px' }}>
                <span style={{ fontSize: 12, color: '#52525b', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 100, height: 4, background: '#27272a', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(reviewedCount / 4) * 100}%`, background: canDownload ? '#10b981' : '#3b82f6', transition: 'width 0.3s' }} />
                  </div>
                  {reviewedCount}/4 sections reviewed
                </span>
                <div style={{ display: 'flex', gap: 8 }}>
                  {saveSuccess && <span style={{ fontSize: 12, color: '#10b981', alignSelf: 'center', marginRight: 8 }}>Saved ✓</span>}
                  <button onClick={saveReport} disabled={saving}
                    style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#18181b', border: '1px solid #3f3f46', color: '#e4e4e7', padding: '8px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', opacity: saving ? 0.6 : 1 }}>
                    {saving ? <Loader style={{ width: 13, height: 13, animation: 'spin 1s linear infinite' }} /> : <FileText style={{ width: 13, height: 13 }} />}
                    Save Draft
                  </button>
                  <button onClick={downloadPDF} disabled={!canDownload || pdfDownloading}
                    style={{ display: 'flex', alignItems: 'center', gap: 6, background: canDownload ? 'rgba(16,185,129,0.1)' : 'rgba(255,255,255,0.05)', border: `1px solid ${canDownload ? 'rgba(16,185,129,0.25)' : 'transparent'}`, color: canDownload ? '#10b981' : '#52525b', padding: '8px 14px', borderRadius: 8, fontSize: 12, cursor: canDownload ? 'pointer' : 'not-allowed', transition: 'all 0.2s' }}>
                    {pdfDownloading ? <Loader style={{ width: 13, height: 13, animation: 'spin 1s linear infinite' }} /> : <Download style={{ width: 13, height: 13 }} />}
                    Download PDF
                  </button>
                </div>
              </div>

              <div ref={reportRef} style={{ ...card, display: 'flex', flexDirection: 'column', gap: 0 }}>
                {/* A. Filing & Institution Info */}
                <Sec title="Section A — Filing & Institution Info" open={secOpen.filing} onChange={() => toggleAccordion('filing')}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, padding: '4px 0 12px 0' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>Filing Institution Name</label>
                      <input value={reportData.filing_institution_name} onChange={e => updateReport('filing_institution_name', e.target.value)} className="input-dark" style={{ width: '100%' }} />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>Filing Institution Address</label>
                      <input value={reportData.filing_institution_address} onChange={e => updateReport('filing_institution_address', e.target.value)} className="input-dark" style={{ width: '100%' }} />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>Filing Date</label>
                      <input type="date" value={reportData.filing_date} onChange={e => updateReport('filing_date', e.target.value)} className="input-dark" style={{ width: '100%' }} />
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>Period Start</label>
                        <input type="date" value={reportData.report_period_start} onChange={e => updateReport('report_period_start', e.target.value)} className="input-dark" style={{ width: '100%' }} />
                      </div>
                      <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>Period End</label>
                        <input type="date" value={reportData.report_period_end} onChange={e => updateReport('report_period_end', e.target.value)} className="input-dark" style={{ width: '100%' }} />
                      </div>
                    </div>
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: reportData.section_filing_reviewed ? '#10b981' : '#a1a1aa', cursor: 'pointer', marginTop: 8 }}>
                    <input type="checkbox" checked={reportData.section_filing_reviewed} onChange={e => updateReport('section_filing_reviewed', e.target.checked)} style={{ accentColor: '#10b981' }} />
                    I have reviewed the filing and institution information.
                  </label>
                </Sec>

                {/* B. Subject & Transaction Info */}
                <Sec title="Section B — Subject & Transaction Info" open={secOpen.subject} onChange={() => toggleAccordion('subject')}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '4px 0 12px 0' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                      <KV label="Subject Name" value={reportData.subject_name} />
                      <KV label="Subject ID / Account" value={reportData.subject_account_id} mono />
                      <KV label="Total Suspicious Amount" value={`$${reportData.total_amount_usd.toLocaleString()}`} />
                      <KV label="Identifying Number" value={reportData.subject_id_number || 'N/A'} />
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: '#71717a', marginBottom: 8, textTransform: 'uppercase' }}>Transaction Types Involved</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {reportData.transaction_types.map((t, i) => (
                          <span key={i} style={{ background: '#18181b', border: '1px solid #27272a', padding: '4px 10px', borderRadius: 4, fontSize: 11, color: '#d4d4d8' }}>{t}</span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: '#71717a', marginBottom: 8, textTransform: 'uppercase' }}>Geographies Involved</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {reportData.geographies_involved.map((g, i) => (
                          <span key={i} style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', padding: '4px 10px', borderRadius: 4, fontSize: 11, color: '#93c5fd' }}>{g}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: reportData.section_subject_reviewed ? '#10b981' : '#a1a1aa', cursor: 'pointer', marginTop: 8 }}>
                    <input type="checkbox" checked={reportData.section_subject_reviewed} onChange={e => updateReport('section_subject_reviewed', e.target.checked)} style={{ accentColor: '#10b981' }} />
                    I have reviewed the subject and transaction summary.
                  </label>
                </Sec>

                {/* C. Fraud Typology */}
                <Sec title="Section C — Fraud Typology & Classification" open={secOpen.typology} onChange={() => toggleAccordion('typology')}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '4px 0 12px 0' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
                      <div>
                        <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>Primary Typology</label>
                        <select value={reportData.typology} onChange={handleTypologyChange} className="input-dark" style={{ width: '100%', appearance: 'auto' }}>
                          <option value="Unknown">Unknown</option>
                          <option value="Structuring">Structuring</option>
                          <option value="Layering">Layering</option>
                          <option value="Rapid Movement">Rapid Movement</option>
                          <option value="High-Risk Geography">High-Risk Geography</option>
                          <option value="Smurfing">Smurfing</option>
                          <option value="TBML">Trade-Based ML</option>
                          <option value="Crypto Layering">Crypto Layering</option>
                        </select>
                      </div>
                      <div>
                        <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>FinCEN Code</label>
                        <input value={reportData.typology_code} readOnly className="input-dark" style={{ width: '100%', background: '#0a0a0a', color: '#71717a' }} />
                      </div>
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>Typology Description</label>
                      <p style={{ fontSize: 12, color: '#a1a1aa', lineHeight: 1.5, background: '#111', padding: 12, borderRadius: 8, border: '1px solid #27272a', margin: 0 }}>
                        {reportData.typology_description || 'No description available.'}
                      </p>
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>Suspicion Reason (Visible on PDF)</label>
                      <textarea value={reportData.suspicion_reason} onChange={e => updateReport('suspicion_reason', e.target.value)} className="input-dark" style={{ width: '100%', resize: 'vertical', minHeight: 60 }} />
                    </div>
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: reportData.section_typology_reviewed ? '#10b981' : '#a1a1aa', cursor: 'pointer', marginTop: 8 }}>
                    <input type="checkbox" checked={reportData.section_typology_reviewed} onChange={e => updateReport('section_typology_reviewed', e.target.checked)} style={{ accentColor: '#10b981' }} />
                    I confirm the typology classification is accurate.
                  </label>
                </Sec>

                {/* D. AI Narrative */}
                <Sec title="Section D — Suspicious Activity Information (Narrative)" open={secOpen.narrative} onChange={() => toggleAccordion('narrative')}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '4px 0 12px 0' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <label style={{ display: 'block', fontSize: 10, color: '#71717a', textTransform: 'uppercase' }}>Mined Narrative Body</label>
                        <span style={{ fontSize: 10, color: '#8b5cf6', background: 'rgba(139,92,246,0.1)', padding: '2px 8px', borderRadius: 4 }}>AI Generated</span>
                      </div>
                      <textarea value={reportData.narrative_body} onChange={e => updateReport('narrative_body', e.target.value)} className="input-dark" style={{ width: '100%', resize: 'vertical', minHeight: 250, lineHeight: 1.6 }} />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 10, color: '#71717a', marginBottom: 6, textTransform: 'uppercase' }}>Analyst Internal Notes (Not included in filing)</label>
                      <textarea value={reportData.analyst_notes} onChange={e => updateReport('analyst_notes', e.target.value)} className="input-dark" style={{ width: '100%', resize: 'vertical', minHeight: 60 }} placeholder="Add any private notes for the audit trail..." />
                    </div>
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: reportData.section_narrative_reviewed ? '#10b981' : '#a1a1aa', cursor: 'pointer', marginTop: 8 }}>
                    <input type="checkbox" checked={reportData.section_narrative_reviewed} onChange={e => updateReport('section_narrative_reviewed', e.target.checked)} style={{ accentColor: '#10b981' }} />
                    I have reviewed and edited the generated narrative for filing.
                  </label>
                </Sec>
              </div>
            </>
          )}
        </div>
      )}

      {/* ══ COMPLIANCE ══ */}
      {tab === 'Compliance' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {!compliance ? <EmptyPanel msg="Compliance runs after pipeline execution" /> : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                {[
                  { label: 'BSA Compliant', ok: compliance.bsa_compliant },
                  { label: 'All Fields', ok: compliance.all_fields_complete },
                  { label: 'FinCEN Format', ok: compliance.fincen_format_valid },
                ].map(({ label, ok }) => (
                  <div key={label} style={{ ...card, display: 'flex', alignItems: 'center', gap: 10 }}>
                    {ok ? <CheckCircle style={{ width: 15, height: 15, color: '#10b981' }} /> : <XCircle style={{ width: 15, height: 15, color: '#f43f5e' }} />}
                    <span style={{ fontSize: 12, fontWeight: 500, color: ok ? '#10b981' : '#f43f5e' }}>{label}</span>
                  </div>
                ))}
              </div>
              <div style={card}>
                <h3 style={{ fontSize: 13, fontWeight: 600, color: '#fff', marginBottom: 12 }}>Compliance Issues</h3>
                {compliance.compliance_issues.length === 0 ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#10b981', fontSize: 13 }}>
                    <CheckCircle style={{ width: 15, height: 15 }} /> All 8 AML compliance rules passed
                  </div>
                ) : compliance.compliance_issues.map((issue, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 12 }}>
                    <XCircle style={{ width: 13, height: 13, color: '#f43f5e', flexShrink: 0, marginTop: 2 }} />
                    <span style={{ color: '#a1a1aa' }}>{issue}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ══ AUDIT TRAIL ══ */}
      {tab === 'Audit Trail' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {data.audit_trail.length === 0 ? <EmptyPanel msg="No audit events — run the pipeline first" /> : (
            <div style={{ background: '#111', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 16, overflow: 'hidden' }}>
              {data.audit_trail.map((entry, i) => (
                <div key={i} style={{ display: 'flex', gap: 14, padding: '14px 20px', borderTop: i > 0 ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ width: 22, height: 22, borderRadius: '50%', background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700, color: '#60a5fa', flexShrink: 0 }}>{i+1}</div>
                    {i < data.audit_trail.length - 1 && <div style={{ width: 1, flex: 1, background: 'rgba(255,255,255,0.05)', marginTop: 8 }} />}
                  </div>
                  <div style={{ flex: 1, paddingBottom: 4 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 3 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: '#fff' }}>{entry.agent}</span>
                      <span style={{ fontSize: 10, color: '#3f3f46' }}>{(entry.confidence * 100).toFixed(0)}% conf</span>
                    </div>
                    <div style={{ fontSize: 12, color: '#71717a', marginBottom: 4 }}>{entry.action}</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#3f3f46' }}>
                      <Clock style={{ width: 11, height: 11 }} />
                      {new Date(entry.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {audit && (
            <div style={card}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <Lock style={{ width: 14, height: 14, color: '#10b981' }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>Immutable SHA256 Hash</span>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <code className="mono" style={{ flex: 1, fontSize: 11, color: '#10b981', background: '#0a0a0a', padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)', wordBreak: 'break-all', lineHeight: 1.6 }}>
                  {audit.immutable_hash}
                </code>
                <button onClick={() => { navigator.clipboard.writeText(audit.immutable_hash); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
                  style={{ padding: 8, background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, cursor: 'pointer', flexShrink: 0 }}>
                  {copied ? <Check style={{ width: 15, height: 15, color: '#10b981' }} /> : <Copy style={{ width: 15, height: 15, color: '#52525b' }} />}
                </button>
              </div>
            </div>
          )}

          {/* Account History Section */}
          {data.normalized && data.normalized.subject_account_ids.length > 0 && (
            <div style={card}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <User style={{ width: 14, height: 14, color: '#3b82f6' }} />
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>Account History</span>
                  <span style={{ fontSize: 11, color: '#52525b' }}>— {data.normalized.subject_account_ids[0]}</span>
                </div>
                <button
                  onClick={async () => {
                    const acctId = data.normalized!.subject_account_ids[0];
                    setLoadingHistory(true);
                    setHistoryError('');
                    try {
                      const trail = await sarApi.getAccountAuditTrail(acctId);
                      setAccountHistory(trail);
                    } catch (e: unknown) {
                      setHistoryError(e instanceof Error ? e.message : 'No history found');
                    }
                    setLoadingHistory(false);
                  }}
                  style={{ fontSize: 11, padding: '5px 12px', background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, color: '#60a5fa', cursor: 'pointer' }}
                >
                  {loadingHistory ? 'Loading…' : 'View All Cases for This Account'}
                </button>
              </div>

              {historyError && (
                <div style={{ fontSize: 12, color: '#71717a', padding: '10px', background: '#0a0a0a', borderRadius: 8 }}>{historyError}</div>
              )}

              {accountHistory && (
                <div>
                  <div style={{ display: 'flex', gap: 16, marginBottom: 14, padding: '10px 14px', background: '#0a0a0a', borderRadius: 10, fontSize: 12 }}>
                    <span style={{ color: '#a1a1aa' }}>Total cases: <strong style={{ color: '#fff' }}>{accountHistory.total_cases}</strong></span>
                    <span style={{ color: '#f87171' }}>SAR required: <strong>{accountHistory.total_sar_required}</strong></span>
                    <span style={{ color: '#71717a' }}>Dismissed: <strong>{accountHistory.total_dismissed}</strong></span>
                    <span style={{ color: '#a1a1aa' }}>Avg score: <strong style={{ color: '#facc15' }}>{(accountHistory.risk_score_avg * 100).toFixed(0)}%</strong></span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {accountHistory.cases.map((c, i) => (
                      <details key={i} style={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 10, overflow: 'hidden' }}>
                        <summary style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10, fontSize: 12, listStyle: 'none' }}>
                          <span style={{ fontFamily: 'monospace', color: '#3b82f6', fontSize: 11 }}>{c.case_id}</span>
                          <RiskBadge tier={c.risk_tier as never} />
                          <StatusBadge status={c.status as never} />
                          <span style={{ marginLeft: 'auto', color: '#52525b', fontSize: 11 }}>${c.total_amount_usd.toLocaleString('en-US', { minimumFractionDigits: 0 })}</span>
                        </summary>
                        <div style={{ padding: '0 14px 14px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                          <div style={{ fontSize: 11, color: '#52525b', marginBottom: 8, paddingTop: 12 }}>Typology: <span style={{ color: '#a1a1aa' }}>{c.typology}</span></div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 10 }}>
                            {c.agent_decisions.map((d, j) => (
                              <div key={j} style={{ display: 'flex', gap: 8, fontSize: 11, color: '#52525b', padding: '4px 0', borderTop: j > 0 ? '1px solid rgba(255,255,255,0.03)' : 'none' }}>
                                <span style={{ color: '#3b82f6', minWidth: 100, flexShrink: 0 }}>{d.agent}</span>
                                <span style={{ color: '#71717a', flex: 1 }}>{d.action?.slice(0, 80)}{(d.action?.length ?? 0) > 80 ? '…' : ''}</span>
                                <span style={{ color: '#3f3f46' }}>{((d.confidence ?? 0) * 100).toFixed(0)}%</span>
                              </div>
                            ))}
                          </div>
                          {c.immutable_hash && (
                            <code style={{ fontSize: 10, color: '#10b981', display: 'block', wordBreak: 'break-all', padding: '6px 10px', background: '#111', borderRadius: 6 }}>
                              SHA256: {c.immutable_hash}
                            </code>
                          )}
                        </div>
                      </details>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmptyPanel({ msg }: { msg: string }) {
  return (
    <div style={{ background: '#111', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 16, padding: '64px 20px', textAlign: 'center', color: '#3f3f46', fontSize: 13 }}>
      {msg}
    </div>
  );
}

function Sec({ title, children, open = false }: { title: string; children: React.ReactNode; open?: boolean }) {
  const [o, setO] = useState(open);
  return (
    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: 12, marginBottom: 12 }}>
      <button onClick={() => setO(v => !v)} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0' }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{title}</span>
        {o ? <ChevronUp style={{ width: 12, height: 12, color: '#3f3f46' }} /> : <ChevronDown style={{ width: 12, height: 12, color: '#3f3f46' }} />}
      </button>
      {o && <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 5, paddingLeft: 4 }}>{children}</div>}
    </div>
  );
}

function KV({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
      <span style={{ fontSize: 10, color: '#3f3f46', textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0, textTransform: 'capitalize' as const }}>{label.replace(/_/g,' ')}</span>
      <span className={mono ? 'mono' : ''} style={{ fontSize: 12, textAlign: 'right', color: mono ? '#3b82f6' : '#a1a1aa' }}>{value}</span>
    </div>
  );
}
