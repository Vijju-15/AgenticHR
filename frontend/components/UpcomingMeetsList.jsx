'use client';

import { useEffect, useMemo, useState } from 'react';

function startOfToday() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

function isMeetingUpcoming(meeting) {
  if (meeting.status === 'cancelled') return false;
  const now = new Date();
  const end = new Date(meeting.end_datetime || meeting.start_datetime);
  return end >= now;
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString([], {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function UpcomingMeetsList({ internEmail, title = 'Upcoming Meets' }) {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function fetchMeetings() {
    if (!internEmail) return;

    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ tenant_id: 'acme_corp', intern_email: internEmail });
      const res = await fetch(`/api/meetings?${params}`, { cache: 'no-store' });
      const data = await res.json();

      if (!res.ok) throw new Error(data.error || 'Failed to load meetings');
      setMeetings(data.meetings || []);
    } catch (e) {
      setError(e.message || 'Failed to load meetings');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchMeetings();
    const id = setInterval(fetchMeetings, 15000);
    return () => clearInterval(id);
  }, [internEmail]); // eslint-disable-line react-hooks/exhaustive-deps

  const upcomingMeetings = useMemo(() => {
    return meetings
      .filter((m) => isMeetingUpcoming(m))
      .sort((a, b) => new Date(a.start_datetime) - new Date(b.start_datetime));
  }, [meetings]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--ahr-surface)' }}>
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--ahr-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--ahr-surface)',
        }}
      >
        <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--ahr-text)' }}>{title}</h2>
        <button
          onClick={fetchMeetings}
          title="Refresh meetings"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--ahr-text-2)',
            padding: 4,
            borderRadius: 6,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 4v6h-6" /><path d="M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
          </svg>
        </button>
      </div>

      <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--ahr-border)', fontSize: '0.78rem', color: 'var(--ahr-text-3)' }}>
        {loading ? 'Refreshing meetings...' : `${upcomingMeetings.length} upcoming meet${upcomingMeetings.length === 1 ? '' : 's'}`}
        {error ? <span style={{ color: '#ef4444', marginLeft: 10 }}>{error}</span> : null}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {upcomingMeetings.length === 0 ? (
          <div
            style={{
              border: '1px dashed var(--ahr-border)',
              borderRadius: 12,
              padding: '18px 16px',
              textAlign: 'center',
              color: 'var(--ahr-text-3)',
              fontSize: '0.85rem',
              background: 'var(--ahr-bg)',
            }}
          >
            No upcoming meets. Meetings for past days are automatically removed.
          </div>
        ) : (
          upcomingMeetings.map((m) => (
            <div
              key={m.meeting_id}
              style={{
                border: '1px solid var(--ahr-border)',
                borderRadius: 12,
                padding: '12px 14px',
                background: 'var(--ahr-bg)',
                marginBottom: 10,
                boxShadow: 'var(--ahr-shadow)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--ahr-text)' }}>{m.title || 'HR Meeting'}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--ahr-text-2)', marginTop: 3 }}>
                    {formatDate(m.start_datetime)} | {formatTime(m.start_datetime)} - {formatTime(m.end_datetime)}
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--ahr-text-3)', marginTop: 4 }}>
                    Host: {m.hr_email || 'HR Team'}
                  </div>
                </div>

                {m.meet_link ? (
                  <a
                    href={m.meet_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      flexShrink: 0,
                      textDecoration: 'none',
                      background: 'var(--ahr-gradient)',
                      color: '#fff',
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      padding: '8px 12px',
                      borderRadius: 8,
                    }}
                  >
                    Join Meet
                  </a>
                ) : (
                  <span style={{ flexShrink: 0, fontSize: '0.75rem', color: 'var(--ahr-text-3)' }}>Link pending</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
