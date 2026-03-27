'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { sarApi, CaseSummary } from '@/lib/api';
import { RiskBadge, StatusBadge } from '@/components/RiskBadge';
import {
  Activity, FileText, AlertTriangle, CheckCircle,
  Shield, Zap, ArrowRight, Clock, Play, TrendingUp, RefreshCw
} from 'lucide-react';

const S = { // inline style helpers
  card: { background: '#111', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 16, padding: 20 } as React.CSSProperties,
  pipeNode: { background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 12, padding: '10px 12px', textAlign: 'center' as const, minWidth: 80, flexShrink: 0 as const },
  section: { background: '#111', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 16, overflow: 'hidden' as const },
};

export default function Dashboard() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    sarApi.getCases().then(setCases).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const total = cases.length;
  const red = cases.filter(c => ['red','critical'].includes(c.risk_tier)).length;
  const amber = cases.filter(c => c.risk_tier === 'amber').length;
  const filed = cases.filter(c => c.status === 'filed').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div className="animate-fade-up" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#fff', marginBottom: 4 }}>Dashboard</h1>
          <p style={{ fontSize: 13, color: '#52525b' }}>AI-powered SAR pipeline · FIU-IND STR · XGBoost + Groq</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button 
            onClick={() => {
              setLoading(true);
              sarApi.refreshPipeline(300).then(() => load()).catch(() => setLoading(false));
            }}
            disabled={loading}
            style={{ 
              display: 'flex', alignItems: 'center', gap: 6, 
              background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', 
              borderRadius: 8, color: '#3b82f6', fontSize: 12, padding: '7px 12px', 
              cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1
            }}
          >
            <Zap style={{ width: 13, height: 13 }} /> Load Batch (300)
          </button>
          <button onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#111', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, color: '#71717a', fontSize: 12, padding: '7px 12px', cursor: 'pointer' }}>
            <RefreshCw style={{ width: 13, height: 13 }} /> Refresh
          </button>
        </div>
      </div>

      {/* Metrics */}
      <div className="animate-fade-up-1" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { label: 'Total Cases', value: total, icon: FileText, color: '#3b82f6', bg: 'rgba(59,130,246,0.1)' },
          { label: 'High Risk', value: red, icon: AlertTriangle, color: '#f43f5e', bg: 'rgba(244,63,94,0.1)' },
          { label: 'Amber Alerts', value: amber, icon: Activity, color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
          { label: 'Filed SARs', value: filed, icon: CheckCircle, color: '#10b981', bg: 'rgba(16,185,129,0.1)' },
        ].map(m => (
          <div key={m.label} style={S.card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: m.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <m.icon style={{ width: 15, height: 15, color: m.color }} />
              </div>
              <TrendingUp style={{ width: 13, height: 13, color: '#27272a' }} />
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: m.color, marginBottom: 2 }}>{loading ? '—' : m.value}</div>
            <div style={{ fontSize: 11, color: '#52525b' }}>{m.label}</div>
          </div>
        ))}
      </div>

      {/* Empty CTA */}
      {!loading && total === 0 && (
        <div className="animate-fade-up-2" style={{ ...S.card, textAlign: 'center', padding: 48, background: 'linear-gradient(135deg, rgba(59,130,246,0.06) 0%, #111 80%)' }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
            <Zap style={{ width: 20, height: 20, color: '#3b82f6' }} />
          </div>
          <h2 style={{ fontSize: 17, fontWeight: 600, color: '#fff', marginBottom: 8 }}>Start with a demo case</h2>
          <p style={{ fontSize: 13, color: '#52525b', marginBottom: 20 }}>Run the 3 pre-loaded AML scenarios to see the full pipeline in action.</p>
          <Link href="/app/demo" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#2563eb', color: '#fff', padding: '10px 20px', borderRadius: 10, fontSize: 13, fontWeight: 500, textDecoration: 'none' }}>
            <Play style={{ width: 14, height: 14 }} /> Run Demo Cases
          </Link>
        </div>
      )}

      {/* Pipeline */}
      <div className="animate-fade-up-2" style={{ ...S.card }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <Shield style={{ width: 14, height: 14, color: '#52525b' }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>6-Agent SAR Pipeline</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflowX: 'auto', paddingBottom: 4 }}>
          {[
            { n: '01', name: 'Ingestion',   color: '#3b82f6' },
            { n: '02', name: 'Risk Score',  color: '#8b5cf6' },
            { n: '03', name: 'Narrative',   color: '#06b6d4' },
            { n: '04', name: 'Compliance',  color: '#f59e0b' },
            { n: '05', name: 'Audit',       color: '#10b981' },
            { n: '06', name: 'Review',      color: '#f43f5e' },
          ].map((s, i, arr) => (
            <div key={s.n} style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
              <div style={S.pipeNode}>
                <div className="mono" style={{ fontSize: 10, fontWeight: 600, color: s.color, marginBottom: 3 }}>{s.n}</div>
                <div style={{ fontSize: 11, fontWeight: 500, color: '#fff' }}>{s.name}</div>
              </div>
              {i < arr.length - 1 && <span style={{ color: '#27272a', fontSize: 14, flexShrink: 0 }}>→</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Recent Cases */}
      {!loading && total > 0 && (
        <div className="animate-fade-up-3" style={S.section}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Activity style={{ width: 14, height: 14, color: '#52525b' }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>Recent Cases</span>
            </div>
            <Link href="/app/cases" style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#3b82f6', textDecoration: 'none' }}>
              View all <ArrowRight style={{ width: 12, height: 12 }} />
            </Link>
          </div>
          {cases.slice(0, 6).map((c, i) => (
            <Link key={c.case_id} href={`/app/cases/${c.case_id}`}
              className="row-hover"
              style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '12px 20px', borderTop: i > 0 ? '1px solid rgba(255,255,255,0.05)' : 'none', textDecoration: 'none' }}>
              <span className="mono" style={{ fontSize: 12, color: '#3b82f6', fontWeight: 500, width: 140, flexShrink: 0 }}>{c.case_id}</span>
              <span style={{ fontSize: 12, color: '#52525b', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.subject}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
                <RiskBadge tier={c.risk_tier} size="sm" />
                <StatusBadge status={c.status} />
                <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#3f3f46' }}>
                  <Clock style={{ width: 11, height: 11 }} />
                  {c.last_updated !== 'Unknown' ? new Date(c.last_updated).toLocaleTimeString() : '—'}
                </span>
                <ArrowRight style={{ width: 13, height: 13, color: '#3f3f46' }} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
