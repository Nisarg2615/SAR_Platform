import { AppShell } from '@/components/AppShell';
import { ZeroTrustProvider } from '@/components/ZeroTrustGate';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ZeroTrustProvider>
      <AppShell>{children}</AppShell>
    </ZeroTrustProvider>
  );
}
