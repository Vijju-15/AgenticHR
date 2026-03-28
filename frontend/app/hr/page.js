'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import ChatInterface from '@/components/ChatInterface';
import MeetingCalendar from '@/components/MeetingCalendar';
import HRLeaveApprovals from '@/components/HRLeaveApprovals';
import HRPolicyUpload from '@/components/HRPolicyUpload';
import HROnboardingSetup from '@/components/HROnboardingSetup';

export default function HRDashboard() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');
  const [opsTab, setOpsTab] = useState('calendar');
  const [isDark, setIsDark] = useState(false);
  const calendarRefreshRef = useRef(null);

  // Load theme from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('ahr-theme');
    const dark = saved === 'dark';
    setIsDark(dark);
    if (dark) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  }, []);

  function toggleTheme() {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('ahr-theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('ahr-theme', 'light');
    }
  }

  useEffect(() => {
    const raw = sessionStorage.getItem('ahr_user');
    if (!raw) { router.replace('/'); return; }

    const parsed = JSON.parse(raw);
    if (parsed.role !== 'hr') { router.replace('/intern'); return; }
    setUser(parsed);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!user) {
    return (
      <div className="landing-bg" style={{ flexDirection: 'column', gap: 12 }}>
        <div style={{ width: 36, height: 36, borderRadius: '50%', border: '3px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', animation: 'spin 0.7s linear infinite' }} />
        <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.85rem' }}>Loading…</p>
        <style jsx global>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  function handleMeetingScheduled() {
    // Trigger calendar refresh when liaison confirms a meeting was scheduled
    if (calendarRefreshRef.current) calendarRefreshRef.current();
  }

  function handleLogout() {
    sessionStorage.removeItem('ahr_user');
    router.push('/');
  }

  return (
    <div
      className="ahr-dashboard"
      style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--ahr-bg)',
        overflow: 'hidden',
      }}
    >
      {/* ── Top Navbar ───────────────────────────────────────────────── */}
      <header
        className="ahr-navbar"
        style={{
          height: 56,
          flexShrink: 0,
          background: 'var(--ahr-surface)',
          borderBottom: '1px solid var(--ahr-border)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          gap: 12,
          boxShadow: '0 1px 0 var(--ahr-border)',
        }}
      >
        {/* Logo */}
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 9,
            background: 'var(--ahr-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" />
          </svg>
        </div>

        <div style={{ flex: 1 }}>
          <span style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--ahr-text)' }}>AgenticHR</span>
          <span
            style={{
              marginLeft: 8,
              fontSize: '0.72rem',
              fontWeight: 600,
              background: isDark ? 'rgba(168,85,247,0.18)' : '#fde8d8',
              color: isDark ? '#c084fc' : '#c2410c',
              padding: '2px 8px',
              borderRadius: 999,
            }}
          >
            HR Dashboard
          </span>
        </div>

        {/* Mobile tab switcher */}
        <div
          className="mobile-tabs"
          style={{
            display: 'none',
            gap: 4,
          }}
        >
          {['chat', 'calendar', 'leave', 'policy', 'setup'].map((t) => (
            <button
              key={t}
              onClick={() => {
                setActiveTab(t);
                if (t !== 'chat') setOpsTab(t);
              }}
              style={{
                padding: '4px 12px',
                borderRadius: 8,
                border: 'none',
                background: activeTab === t ? 'var(--ahr-accent)' : 'var(--ahr-surface-2)',
                color: activeTab === t ? '#fff' : 'var(--ahr-text-2)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {t === 'leave' ? 'approvals' : t}
            </button>
          ))}
        </div>

        {/* User + logout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              border: '1px solid var(--ahr-border)',
              background: 'var(--ahr-surface-2)',
              color: 'var(--ahr-text-2)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'all 0.2s',
            }}
          >
            {isDark ? (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="4.5"/>
                <path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
              </svg>
            ) : (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
              </svg>
            )}
          </button>

          <div style={{ textAlign: 'right', lineHeight: 1.2 }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ahr-text)' }}>{user.name}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--ahr-text-3)' }}>{user.email}</div>
          </div>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: 'var(--ahr-gradient)',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.8rem',
              flexShrink: 0,
            }}
          >
            {user.name?.[0]?.toUpperCase() || 'H'}
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            style={{
              background: 'none',
              border: '1px solid var(--ahr-border)',
              borderRadius: 8,
              padding: '4px 10px',
              cursor: 'pointer',
              fontSize: '0.75rem',
              color: 'var(--ahr-text-2)',
              fontWeight: 500,
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: '1fr 360px',
          overflow: 'hidden',
          gap: 0,
        }}
      >
        {/* ── LEFT: Chat panel ── */}
        <div
          className="ahr-panel"
          style={{
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid var(--ahr-border)',
            overflow: 'hidden',
            background: 'var(--ahr-surface)',
          }}
        >
          {/* Chat header */}
          <div
            style={{
              padding: '14px 20px',
              borderBottom: '1px solid var(--ahr-border)',
              background: 'var(--ahr-surface)',
            }}
          >
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--ahr-text)' }}>
              AI Assistant
            </h3>
            <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--ahr-text-3)', marginTop: 2 }}>
              Ask about policies, schedule meetings, manage leave…
            </p>
          </div>

          <div style={{ flex: 1, overflow: 'hidden' }}>
            <ChatInterface
              user={user}
              placeholder="e.g. Schedule a meeting with intern@acme.com on Dec 15 at 3 PM"
              greeting={`Hi ${user.name?.split(' ')[0] || 'there'}! I'm your HR assistant. You can schedule meetings, check policies, or manage employee requests.`}
              onMeetingScheduled={handleMeetingScheduled}
            />
          </div>
        </div>

        {/* ── RIGHT: Calendar panel ── */}
        <div
          className="ahr-panel"
          style={{
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            background: 'var(--ahr-surface)',
          }}
        >
          <div
            style={{
              padding: '10px 12px',
              borderBottom: '1px solid var(--ahr-border)',
              display: 'flex',
              gap: 6,
              flexWrap: 'wrap',
              background: 'var(--ahr-surface)',
            }}
          >
            {[
              { id: 'calendar', label: 'Calendar' },
              { id: 'leave', label: 'Leave Approvals' },
              { id: 'policy', label: 'Policy Upload' },
              { id: 'setup', label: 'Employee Setup' },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  setOpsTab(t.id);
                  if (window.innerWidth <= 768) setActiveTab(t.id);
                }}
                style={{
                  padding: '5px 10px',
                  borderRadius: 8,
                  border: '1px solid var(--ahr-border)',
                  background: opsTab === t.id ? 'var(--ahr-accent)' : 'var(--ahr-surface-2)',
                  color: opsTab === t.id ? '#fff' : 'var(--ahr-text-2)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {t.label}
              </button>
            ))}
          </div>

          {opsTab === 'calendar' ? (
            <MeetingCalendar
              hrEmail={user.email}
              onRefreshRef={calendarRefreshRef}
            />
          ) : opsTab === 'leave' ? (
            <HRLeaveApprovals
              tenantId={user.tenant_id || 'acme_corp'}
              approverId={user.email || user.name || 'hr_admin'}
            />
          ) : opsTab === 'policy' ? (
            <HRPolicyUpload tenantId={user.tenant_id || 'acme_corp'} />
          ) : (
            <HROnboardingSetup tenantId={user.tenant_id || 'acme_corp'} />
          )}
        </div>
      </main>

      {/* Responsive styles */}
      <style jsx global>{`
        @media (max-width: 768px) {
          main {
            grid-template-columns: 1fr !important;
          }
          .mobile-tabs {
            display: flex !important;
          }
          main > div:first-child {
            display: ${activeTab === 'chat' ? 'flex' : 'none'} !important;
          }
          main > div:last-child {
            display: ${activeTab !== 'chat' ? 'flex' : 'none'} !important;
          }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
