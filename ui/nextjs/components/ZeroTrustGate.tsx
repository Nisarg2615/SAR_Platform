'use client';
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { ShieldAlert, RefreshCw, Key } from 'lucide-react';
import { sarApi } from '@/lib/api';

// MOCK: In production this decodes the Keycloak RS256 JWT
export type Role = 'ANALYST_L1' | 'ANALYST_L2' | 'COMPLIANCE_OFFICER' | 'AUDITOR';

interface SessionPayload {
  user_id: string;
  name: string;
  role: Role;
  exp: number;
}

const ZTContext = createContext<SessionPayload | null>(null);

export function useZeroTrustSession() {
  return useContext(ZTContext);
}

// 7.1 Keycloak Auth Gate + 7.2 Session Manager (Mocked)
export function ZeroTrustProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate checking st.session_state / JWT validation from Keycloak
    const mockToken = localStorage.getItem('zt_token');
    if (mockToken) {
      setSession(JSON.parse(mockToken));
    }
    setLoading(false);
  }, []);

  const login = (role: Role) => {
    const payload: SessionPayload = {
      user_id: `user-${Math.random().toString(36).substring(7)}`,
      name: role === 'COMPLIANCE_OFFICER' ? 'Arjun Dev' : 'Samira R.',
      role,
      exp: Date.now() + 15 * 60 * 1000, // 15 min JWT TTL
    };
    localStorage.setItem('zt_token', JSON.stringify(payload));
    setSession(payload);
    
    // Log auth audit
    sarApi.logAuditEvent({
      user_id: payload.user_id,
      user_role: payload.role,
      event_type: 'SESSION_INITIALIZED',
      metadata: { method: 'MOCK_KEYCLOAK_SSO', device_posture: 'PASS', ip: '10.0.0.42' }
    }).catch(() => {});
  };

  const logout = () => {
    if (session) {
      sarApi.logAuditEvent({
        user_id: session.user_id,
        user_role: session.role,
        event_type: 'SESSION_TERMINATED',
        metadata: { reason: 'USER_LOGOUT' }
      }).catch(() => {});
    }
    localStorage.removeItem('zt_token');
    setSession(null);
  };

  if (loading) {
    return <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', color: '#fff' }}><RefreshCw className="spin" /></div>;
  }

  if (!session) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', color: '#fff' }}>
        <div style={{ background: '#111', border: '1px solid rgba(255,255,255,0.07)', padding: 40, borderRadius: 20, maxWidth: 400, width: '100%', textAlign: 'center' }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: 'rgba(59,130,246,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <Key style={{ color: '#3b82f6' }} />
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Zero Trust Gateway</h1>
          <p style={{ fontSize: 13, color: '#a1a1aa', marginBottom: 24, lineHeight: 1.5 }}>
            To access the SAR Intelligence Platform, please authenticate.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(['ANALYST_L1', 'ANALYST_L2', 'COMPLIANCE_OFFICER', 'AUDITOR'] as Role[]).map(r => (
              <button key={r} onClick={() => login(r)}
                style={{ padding: '10px 16px', background: '#18181b', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 8, color: '#e4e4e7', fontSize: 13, cursor: 'pointer', transition: 'all 0.1s' }}
                onMouseOver={e => e.currentTarget.style.background = '#27272a'}
                onMouseOut={e => e.currentTarget.style.background = '#18181b'}>
                Login as <strong>{r}</strong>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Session expiry check (Simulates 7.2 Inactivity/Refresh timeout)
  if (Date.now() > session.exp) {
    logout();
    return null;
  }

  return (
    <ZTContext.Provider value={session}>
      {children}
      {/* Dev toggle to logout */}
      <button onClick={logout} style={{ position: 'fixed', bottom: 16, right: 16, background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', color: '#f43f5e', fontSize: 11, padding: '6px 10px', borderRadius: 6, cursor: 'pointer', zIndex: 9999 }}>
        End Session ({session.role})
      </button>
    </ZTContext.Provider>
  );
}

// 7.3 Role-Gated UI Renderer
const ROLE_PERMISSIONS: Record<Role, string[]> = {
  ANALYST_L1: ['view_alert_queue', 'view_case_summary', 'view_transaction_list'],
  ANALYST_L2: ['view_alert_queue', 'view_case_summary', 'view_transaction_list', 'view_graph_panel', 'annotate_case', 'view_shap_explanation'],
  COMPLIANCE_OFFICER: ['view_alert_queue', 'view_case_summary', 'view_transaction_list', 'view_graph_panel', 'annotate_case', 'view_shap_explanation', 'view_typology_report', 'approve_sar', 'export_str_document', 'view_pii_unmasked'],
  AUDITOR: ['view_graph_panel', 'view_audit_trail', 'view_case_summary'],
};

export function RoleGate({ permission, children }: { permission: string; children: ReactNode }) {
  const session = useZeroTrustSession();
  
  if (!session) return null; // No hints
  const userPerms = ROLE_PERMISSIONS[session.role] || [];
  
  if (!userPerms.includes(permission)) {
    return null; // Forbidden components render nothing, zero hints leaked (7.3)
  }

  return <>{children}</>;
}

// Higher order component replacement for `@requires_permission` back-end decorator
export function withRoleGate(Component: React.ComponentType<any>, permission: string) {
  return function RoleGatedComponent(props: any) {
    return (
      <RoleGate permission={permission}>
        <Component {...props} />
      </RoleGate>
    );
  };
}
