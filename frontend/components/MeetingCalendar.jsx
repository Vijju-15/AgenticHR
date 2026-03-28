'use client';

import { useState, useEffect } from 'react';

const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
];
const DAYS_SHORT = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

function getMeetingDisplayStatus(meeting, now = new Date()) {
  if (meeting.status === 'cancelled') return 'cancelled';
  const end = new Date(meeting.end_datetime || meeting.start_datetime);
  if (end < now) return 'ended';
  return meeting.status || 'scheduled';
}

/**
 * MeetingCalendar
 *
 * Props:
 *   hrEmail     – string, filter meetings by HR email
 *   internEmail – string, filter meetings by intern email (for intern view)
 *   readOnly    – bool, hides the cancel button (used in intern view)
 *   title       – string, override the calendar panel heading
 *   onRefresh   – optional callback to attach the refresh fn to parent
 */
export default function MeetingCalendar({ hrEmail, internEmail, readOnly = false, title, onRefreshRef }) {
  const today = new Date();
  const [year, setYear]       = useState(today.getFullYear());
  const [month, setMonth]     = useState(today.getMonth()); // 0-indexed
  const [selectedDay, setSelectedDay] = useState(null);
  const [meetings, setMeetings]       = useState([]);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState('');

  // Expose refresh fn to parent via ref callback
  useEffect(() => {
    if (onRefreshRef) onRefreshRef.current = fetchMeetings;
  });

  async function fetchMeetings() {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ tenant_id: 'acme_corp' });
      if (hrEmail)     params.set('hr_email', hrEmail);
      if (internEmail) params.set('intern_email', internEmail);

      const res  = await fetch(`/api/meetings?${params}`, { cache: 'no-store' });
      const data = await res.json();

      if (!res.ok) throw new Error(data.error || 'Failed to load meetings');
      setMeetings(data.meetings || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchMeetings();
    // Poll every 15 seconds to pick up newly scheduled Google Meet links
    const id = setInterval(fetchMeetings, 15000);
    return () => clearInterval(id);
  }, [hrEmail, internEmail]); // eslint-disable-line

  // ── Calendar math ──────────────────────────────────────────────────
  const firstDayOfMonth = new Date(year, month, 1).getDay();
  const daysInMonth     = new Date(year, month + 1, 0).getDate();

  // Build a Set of days (of current month) that have meetings
  const meetingDays = new Set(
    meetings
      .filter((m) => {
        const d = new Date(m.start_datetime);
        return d.getFullYear() === year && d.getMonth() === month;
      })
      .map((m) => new Date(m.start_datetime).getDate()),
  );

  // Meetings for the selected day
  const selectedMeetings = selectedDay
    ? meetings.filter((m) => {
        const d = new Date(m.start_datetime);
        return (
          d.getFullYear() === year &&
          d.getMonth() === month &&
          d.getDate() === selectedDay
        );
      })
    : [];

  function prevMonth() {
    if (month === 0) { setMonth(11); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
    setSelectedDay(null);
  }

  function nextMonth() {
    if (month === 11) { setMonth(0); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
    setSelectedDay(null);
  }

  function formatTime(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* ── Header ── */}
      <div
        style={{
          padding: '16px 20px',
          background: 'var(--ahr-surface)',
          borderBottom: '1px solid var(--ahr-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--ahr-text)' }}>
            {title || 'Meeting Calendar'}
          </h2>
          {loading && (
            <span style={{ fontSize: '0.7rem', color: 'var(--ahr-text-3)' }}>Refreshing…</span>
          )}
          {error && (
            <span style={{ fontSize: '0.7rem', color: '#ef4444' }}>{error}</span>
          )}
        </div>
        <button
          onClick={fetchMeetings}
          title="Refresh meetings"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 4,
            color: 'var(--ahr-text-2)',
            borderRadius: 6,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 4v6h-6" /><path d="M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
          </svg>
        </button>
      </div>

      {/* ── Month navigation ── */}
      <div
        style={{
          padding: '12px 20px 8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--ahr-surface)',
        }}
      >
        <button onClick={prevMonth} style={navBtnStyle}>‹</button>
        <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--ahr-text)' }}>
          {MONTHS[month]} {year}
        </span>
        <button onClick={nextMonth} style={navBtnStyle}>›</button>
      </div>

      {/* ── Day-of-week header ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', padding: '0 12px', background: 'var(--ahr-surface)' }}>
        {DAYS_SHORT.map((d) => (
          <div
            key={d}
            style={{
              textAlign: 'center',
              fontSize: '0.7rem',
              fontWeight: 700,
              color: 'var(--ahr-text-3)',
              padding: '4px 0 6px',
            }}
          >
            {d}
          </div>
        ))}
      </div>

      {/* ── Day grid ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          gap: 3,
          padding: '0 12px 8px',
          background: 'var(--ahr-surface)',
        }}
      >
        {/* Empty cells before first day */}
        {Array.from({ length: firstDayOfMonth }).map((_, i) => (
          <div key={`empty-${i}`} />
        ))}

        {/* Day cells */}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const isToday =
            today.getDate() === day &&
            today.getMonth() === month &&
            today.getFullYear() === year;
          const hasMtg = meetingDays.has(day);
          const isSel  = selectedDay === day;

          let cls = 'cal-day';
          if (hasMtg) cls += ' has-meeting';
          if (isSel)  cls += ' selected';
          if (isToday && !isSel) cls += ' today';

          return (
            <div
              key={day}
              className={cls}
              onClick={() => setSelectedDay(isSel ? null : day)}
            >
              <span>{day}</span>
              {hasMtg && !isSel && <span className="cal-dot" />}
            </div>
          );
        })}
      </div>

      {/* ── Meetings panel ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 16px 16px', background: 'var(--ahr-bg)' }}>
        {selectedDay ? (
          selectedMeetings.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '20px 0',
                color: 'var(--ahr-text-3)',
                fontSize: '0.82rem',
              }}
            >
              No meetings on {MONTHS[month]} {selectedDay}
            </div>
          ) : (
            selectedMeetings.map((m) => (
              <MeetingCard key={m.meeting_id} meeting={m} formatTime={formatTime} onCancel={fetchMeetings} readOnly={readOnly} />
            ))
          )
        ) : (
          <UpcomingMeetings meetings={meetings} today={today} />
        )}
      </div>
    </div>
  );
}

/* ── Meeting Card ─────────────────────────────────────────────────────── */
function MeetingCard({ meeting: m, formatTime, onCancel, readOnly = false }) {
  const [cancelling, setCancelling] = useState(false);
  const displayStatus = getMeetingDisplayStatus(m);
  const isEnded = displayStatus === 'ended';

  const statusColor = {
    scheduled: '#22c55e',
    pending:   '#f59e0b',
    cancelled: '#ef4444',
    ended: '#64748b',
  }[displayStatus] || '#94a3b8';

  async function handleCancel() {
    if (!confirm(`Cancel meeting "${m.title}"?`)) return;
    setCancelling(true);
    try {
      await fetch(`/api/meetings?meeting_id=${m.meeting_id}`, { method: 'DELETE' });
      onCancel();
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div
      className="fade-in"
      style={{
        background: 'var(--ahr-surface)',
        border: '1px solid var(--ahr-border)',
        borderRadius: 14,
        padding: '12px 14px',
        marginBottom: 10,
        boxShadow: 'var(--ahr-shadow)',
      }}
    >
      {/* Title + status badge */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--ahr-text)' }}>{m.title}</span>
        <span
          style={{
            fontSize: '0.7rem',
            fontWeight: 600,
            color: statusColor,
            background: statusColor + '1a',
            padding: '2px 8px',
            borderRadius: 999,
          }}
        >
          {displayStatus}
        </span>
      </div>

      {/* Time */}
      <div style={{ fontSize: '0.78rem', color: 'var(--ahr-text-2)', marginBottom: 4 }}>
        🕐 {formatTime(m.start_datetime)} – {formatTime(m.end_datetime)} &nbsp;·&nbsp; {m.duration_mins} min
      </div>

      {/* Intern */}
      <div style={{ fontSize: '0.78rem', color: 'var(--ahr-text-2)', marginBottom: 8 }}>
        👤 With <strong>{m.intern_name || m.intern_email}</strong> ({m.intern_email})
      </div>

      {/* Meet link */}
      {displayStatus === 'cancelled' ? (
        <div style={{ fontSize: '0.75rem', color: '#ef4444', fontStyle: 'italic' }}>
          This meeting was cancelled.
        </div>
      ) : isEnded ? (
        <div style={{ fontSize: '0.75rem', color: 'var(--ahr-text-3)', fontStyle: 'italic' }}>
          Meeting ended with {m.intern_name || m.intern_email}
        </div>
      ) : m.meet_link ? (
        <a
          href={m.meet_link}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '7px 14px',
            borderRadius: 8,
            background: 'var(--ahr-meet-btn)',
            color: '#fff',
            fontSize: '0.8rem',
            fontWeight: 600,
            textDecoration: 'none',
            boxShadow: '0 2px 8px rgba(0,0,0,0.20)',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
            <path d="M17 10.5V7a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h12a1 1 0 001-1v-3.5l4 4v-11l-4 4z"/>
          </svg>
          Join Google Meet
        </a>
      ) : (
        <div style={{ fontSize: '0.75rem', color: '#f59e0b', fontStyle: 'italic' }}>
          ⏳ Generating Meet link…
        </div>
      )}

      {/* Cancel — hidden for interns */}
      {!readOnly && m.status !== 'cancelled' && !isEnded && (
        <button
          onClick={handleCancel}
          disabled={cancelling}
          style={{
            marginTop: 8,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '0.72rem',
            color: '#ef4444',
            padding: 0,
            textDecoration: 'underline',
          }}
        >
          {cancelling ? 'Cancelling…' : 'Cancel meeting'}
        </button>
      )}
    </div>
  );
}

/* ── Upcoming meetings list (when no day selected) ───────────────────── */
function UpcomingMeetings({ meetings, today }) {
  const upcoming = meetings
    .filter((m) => new Date(m.start_datetime) >= today && m.status !== 'cancelled')
    .slice(0, 5);

  if (upcoming.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--ahr-text-3)', fontSize: '0.82rem' }}>
        <div style={{ fontSize: '1.8rem', marginBottom: 8 }}>📅</div>
        No upcoming meetings
        <br />
        <span style={{ fontSize: '0.75rem' }}>Ask the chat to schedule one!</span>
      </div>
    );
  }

  return (
    <div>
      <p style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--ahr-text-3)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        Upcoming
      </p>
      {upcoming.map((m) => {
        const d = new Date(m.start_datetime);
        return (
          <div
            key={m.meeting_id}
            style={{
              display: 'flex',
              gap: 10,
              marginBottom: 8,
              padding: '8px 10px',
              borderRadius: 10,
              background: 'var(--ahr-surface-2)',
              border: '1px solid var(--ahr-border)',
              cursor: 'default',
            }}
          >
            {/* Date badge */}
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 8,
                background: 'var(--ahr-gradient)',
                color: '#fff',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                fontSize: '0.65rem',
                lineHeight: 1,
              }}
            >
              <span style={{ fontWeight: 700, fontSize: '1rem' }}>{d.getDate()}</span>
              <span>{MONTHS[d.getMonth()].slice(0, 3)}</span>
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--ahr-text)' }}>{m.title}</div>
              <div style={{ fontSize: '0.73rem', color: 'var(--ahr-text-2)' }}>
                {d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {m.intern_name || m.intern_email}
              </div>
              {m.meet_link && (
                <a
                  href={m.meet_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: '0.72rem', color: 'var(--ahr-accent)', textDecoration: 'none', fontWeight: 600 }}
                >
                  Join →
                </a>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Small helpers ──────────────────────────────────────────────────────
const navBtnStyle = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  fontSize: '1.3rem',
  color: 'var(--ahr-text-2)',
  width: 28,
  height: 28,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 6,
};
