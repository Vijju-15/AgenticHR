'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ChatInterface from '@/components/ChatInterface';
import UpcomingMeetsList from '@/components/UpcomingMeetsList';
import InternLeaveStatus from '@/components/InternLeaveStatus';

const QUICK_PROMPTS = [
  'What is the leave policy?',
  'How do I apply for annual leave?',
  'What are the working hours?',
  'I need help with my onboarding',
  'What documents did I need to submit?',
  'How can I contact HR?',
];

export default function InternDashboard() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [quickInput, setQuickInput] = useState('');
  const [activeTab, setActiveTab] = useState('chat');
  const [isDark, setIsDark] = useState(false);

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
    if (parsed.role === 'hr') { router.replace('/hr'); return; }
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

  function handleLogout() {
    sessionStorage.removeItem('ahr_user');
    router.push('/');
  }

  function handleQuickPrompt(text) {
    // We pass the text up to ChatInterface via a shared state trick
    setQuickInput(text);
    setTimeout(() => setQuickInput(''), 50); // reset after ChatInterface picks it up
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
      {/* ── Navbar ───────────────────────────────────────────────────── */}
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
              background: isDark ? 'rgba(34,197,94,0.15)' : '#f0fdf4',
              color: isDark ? '#4ade80' : '#15803d',
              padding: '2px 8px',
              borderRadius: 999,
            }}
          >
            My Portal
          </span>
        </div>

        {/* Tab switcher */}
        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { id: 'chat',  label: 'Chat' },
            { id: 'meets', label: 'Upcoming Meets' },
            { id: 'leave', label: 'My Leave Status' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                padding: '5px 14px',
                borderRadius: 8,
                border: 'none',
                background: activeTab === t.id ? 'var(--ahr-accent)' : 'var(--ahr-surface-2)',
                color: activeTab === t.id ? '#fff' : 'var(--ahr-text-2)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* User + theme + logout */}
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
              background: 'linear-gradient(135deg,#22c55e,#16a34a)',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.8rem',
              flexShrink: 0,
            }}
          >
            {user.name?.[0]?.toUpperCase() || 'I'}
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
          display: 'flex',
          overflow: 'hidden',
          maxWidth: activeTab === 'meets' ? 860 : 900,
          margin: '0 auto',
          width: '100%',
          flexDirection: 'column',
        }}
      >
        {activeTab === 'chat' ? (
          <>
            {/* Welcome strip */}
            <div style={{ padding: '16px 24px 4px', background: 'var(--ahr-bg)' }}>
              <h2 style={{ margin: '0 0 4px', fontSize: '1.1rem', fontWeight: 700, color: 'var(--ahr-text)' }}>
                Welcome, {user.name?.split(' ')[0] || 'there'}! 👋
              </h2>
              <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--ahr-text-3)' }}>
                Ask me anything about your onboarding, leaves, policies, or company info.
              </p>

              {/* Quick prompts */}
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10, marginBottom: 2 }}>
                {QUICK_PROMPTS.map((p) => (
                  <button
                    key={p}
                    onClick={() => handleQuickPrompt(p)}
                    style={{
                      padding: '5px 12px',
                      borderRadius: 999,
                      border: '1px solid var(--ahr-border)',
                      background: 'var(--ahr-surface-2)',
                      color: 'var(--ahr-accent)',
                      fontSize: '0.75rem',
                      fontWeight: 500,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ height: 1, background: 'var(--ahr-border)' }} />
            <div style={{ flex: 1, overflow: 'hidden', background: 'var(--ahr-surface)' }}>
              <InternChat user={user} initialInput={quickInput} />
            </div>
          </>
        ) : activeTab === 'meets' ? (
          /* ── Upcoming Meets tab ── */
          <div style={{ flex: 1, overflow: 'hidden', background: 'var(--ahr-surface)' }}>
            <UpcomingMeetsList
              internEmail={user.email}
              title="Upcoming Meets"
            />
          </div>
        ) : (
          <div style={{ flex: 1, overflow: 'hidden', background: 'var(--ahr-surface)' }}>
            <InternLeaveStatus
              tenantId={user.tenant_id || 'acme_corp'}
              employeeEmail={user.email}
              employeeId={user.employee_id || ''}
            />
          </div>
        )}
      </main>

      <style jsx global>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

/**
 * Thin wrapper around ChatInterface that handles external quick-prompt injection.
 */
function InternChat({ user, initialInput }) {
  const [key, setKey] = useState(0);
  const [prefill, setPrefill] = useState('');

  useEffect(() => {
    if (initialInput) {
      setPrefill(initialInput);
      setKey((k) => k + 1);
    }
  }, [initialInput]);

  return (
    <ChatInterface
      key={key}
      user={user}
      placeholder="Ask about leave policy, onboarding steps, company benefits…"
      greeting={
        prefill
          ? undefined
          : `Hi ${user?.name?.split(' ')[0] || 'there'}! I'm your HR assistant. Ask me anything — leave policies, onboarding tasks, documents, and more.`
      }
      autoSendMessage={prefill}
    />
  );
}
