'use client';

interface BadgeProps { tier: string; size?: 'sm' | 'md' | 'lg'; }
interface StatusProps { status: string; }

const TIER_MAP: Record<string, { label: string; cls: string }> = {
  red:      { label: 'RED',     cls: 'badge badge-red' },
  critical: { label: 'RED',     cls: 'badge badge-red' },
  amber:    { label: 'AMBER',   cls: 'badge badge-amber' },
  yellow:   { label: 'AMBER',   cls: 'badge badge-amber' },
  green:    { label: 'GREEN',   cls: 'badge badge-green' },
  low:      { label: 'GREEN',   cls: 'badge badge-green' },
  pending:  { label: 'PENDING', cls: 'badge badge-grey' },
};

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  pending:     { label: 'PENDING',     cls: 'badge badge-grey' },
  in_review:   { label: 'IN REVIEW',   cls: 'badge badge-blue' },
  filed:       { label: 'FILED',       cls: 'badge badge-green' },
  dismissed:   { label: 'DISMISSED',   cls: 'badge badge-grey' },
  investigating: { label: 'INVESTIGATING', cls: 'badge badge-purple' },
  approved:    { label: 'FILED',       cls: 'badge badge-green' },
};

/** Normalize Python enum strings like 'RiskTier.critical' → 'critical' */
function normalizeTier(raw: string | undefined | null): string {
  if (!raw) return '';
  const s = raw.toLowerCase();
  const dot = s.lastIndexOf('.');
  return dot !== -1 ? s.slice(dot + 1) : s;
}

function normalizeStatus(raw: string | undefined | null): string {
  if (!raw) return '';
  const s = raw.toLowerCase();
  const dot = s.lastIndexOf('.');
  return dot !== -1 ? s.slice(dot + 1) : s;
}

export function RiskBadge({ tier, size = 'md' }: BadgeProps) {
  const key = normalizeTier(tier);
  const t = TIER_MAP[key] ?? { label: key?.toUpperCase() ?? '?', cls: 'badge badge-grey' };
  const sizeStyle: React.CSSProperties =
    size === 'sm' ? { fontSize: 9, padding: '2px 8px' } :
    size === 'lg' ? { fontSize: 13, padding: '4px 14px' } : {};
  return <span className={t.cls} style={sizeStyle}>{t.label}</span>;
}

export function StatusBadge({ status }: StatusProps) {
  const key = normalizeStatus(status);
  const s = STATUS_MAP[key] ?? { label: key?.toUpperCase() ?? '?', cls: 'badge badge-grey' };
  return <span className={s.cls} style={{ fontSize: 9, padding: '2px 8px' }}>{s.label}</span>;
}
