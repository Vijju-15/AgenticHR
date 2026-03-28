'use client';

import { useState, useRef, useEffect } from 'react';

const LIAISON_URL =
  typeof window !== 'undefined' && process.env.NEXT_PUBLIC_LIAISON_URL
    ? process.env.NEXT_PUBLIC_LIAISON_URL
    : 'http://localhost:8002';

/**
 * ChatInterface – shared chat component for both HR and Intern dashboards.
 *
 * Props:
 *   user        – { email, name, role, tenant_id }
 *   placeholder – input placeholder text
 *   greeting    – first bot message
 *   onMeetingScheduled – optional callback(meetingInfo) fired when a meeting
 *                        is successfully scheduled (used by HR Dashboard to
 *                        refresh the calendar).
 */
export default function ChatInterface({ user, placeholder, greeting, onMeetingScheduled, autoSendMessage }) {
  const defaultGreeting =
    greeting ||
    `Hi${user?.name ? ` ${user.name.split(' ')[0]}` : ''}! I'm your AgenticHR assistant. How can I help you today?`;

  const [messages, setMessages] = useState([
    { id: 'init', role: 'bot', text: defaultGreeting, ts: new Date() },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const didAutoSend = useRef(false);

  // Auto-send a pre-filled message (from quick-prompt buttons)
  useEffect(() => {
    if (autoSendMessage && !didAutoSend.current) {
      didAutoSend.current = true;
      sendMessage(autoSendMessage);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSendMessage]);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function sendMessage(text) {
    if (!text.trim() || loading) return;

    const userMsg = { id: Date.now(), role: 'user', text: text.trim(), ts: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const body = {
        user_id: user?.email || 'anonymous',
        tenant_id: user?.tenant_id || 'acme_corp',
        message: text.trim(),
        user_role: user?.role || 'employee',
        user_name: user?.name || '',
        metadata: {
          employee_id: user?.employee_id || '',
          employee_email: user?.email || '',
          personal_email: user?.personal_email || '',
        },
      };

      const res = await fetch(`${LIAISON_URL}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`Liaison returned ${res.status}`);
      }

      const data = await res.json();
      const reply = data.response || data.message || data.response_text || 'I could not process your request right now.';

      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'bot', text: reply, ts: new Date() },
      ]);

      // If the liaison response indicates a meeting was scheduled, notify parent
      if (
        onMeetingScheduled &&
        (reply.toLowerCase().includes('meeting') || reply.toLowerCase().includes('scheduled')) &&
        data.meeting_id
      ) {
        onMeetingScheduled(data);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'bot',
          text: '⚠️ Sorry, I could not reach the server. Make sure the Liaison Agent is running on port 8002.',
          ts: new Date(),
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--ahr-surface)',
      }}
    >
      {/* Message list */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        {loading && (
          <div style={{ display: 'flex', gap: 6, padding: '10px 0', alignItems: 'center' }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                background: 'linear-gradient(135deg,#3b82f6,#7c3aed)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" />
              </svg>
            </div>
            <div className="bubble-bot" style={{ padding: '10px 14px' }}>
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--ahr-border)' }} />

      {/* Input row */}
      <div
        style={{
          padding: '12px 16px',
          display: 'flex',
          gap: 10,
          alignItems: 'flex-end',
          background: 'var(--ahr-surface)',
        }}
      >
        <textarea
          ref={inputRef}
          rows={1}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            // Auto-grow
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || 'Type a message…'}
          style={{
            flex: 1,
            resize: 'none',
            border: '2px solid var(--ahr-border)',
            borderRadius: 12,
            padding: '10px 14px',
            fontSize: '0.9rem',
            fontFamily: 'inherit',
            outline: 'none',
            transition: 'border-color 0.2s',
            lineHeight: 1.5,
            maxHeight: 120,
            overflow: 'auto',
            background: 'var(--ahr-surface-2)',
            color: 'var(--ahr-text)',
          }}
          onFocus={(e) => (e.target.style.borderColor = 'var(--ahr-accent)')}
          onBlur={(e) => (e.target.style.borderColor = 'var(--ahr-border)')}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background:
              loading || !input.trim()
                ? 'var(--ahr-border)'
                : 'var(--ahr-gradient)',
            border: 'none',
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'background 0.2s',
            flexShrink: 0,
          }}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill={loading || !input.trim() ? '#94a3b8' : 'white'}
          >
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>
    </div>
  );
}

function parseInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/);
  return parts.map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i}>{p.slice(2, -2)}</strong>
      : p
  );
}

function renderBotText(text) {
  const statusColors = { '\u2705': '#22c55e', '\u26a0\ufe0f': '#f59e0b', '\u274c': '#ef4444', '\u2139\ufe0f': '#3b82f6', '\u23f3': '#f59e0b' };
  const lines = text.split('\n');
  const output = [];
  let bullets = [];
  let key = 0;

  const flushBullets = () => {
    if (!bullets.length) return;
    output.push(
      <ul key={key++} style={{ margin: '4px 0 8px', padding: 0, listStyle: 'none' }}>
        {bullets.map((b, j) => (
          <li key={j} style={{ display: 'flex', gap: 8, marginBottom: 4, alignItems: 'flex-start' }}>
            <span style={{ color: 'var(--ahr-accent)', fontWeight: 700, flexShrink: 0, lineHeight: 1.6, fontSize: '0.85rem' }}>›</span>
            <span>{parseInline(b)}</span>
          </li>
        ))}
      </ul>
    );
    bullets = [];
  };

  for (const line of lines) {
    const t = line.trim();
    if (!t) { flushBullets(); continue; }

    // Emoji status prefix
    let statusColor = null;
    let content = t;
    for (const [emoji, color] of Object.entries(statusColors)) {
      if (t.startsWith(emoji)) {
        statusColor = color;
        content = t.slice(emoji.length).trim();
        break;
      }
    }

    if (statusColor) {
      flushBullets();
      output.push(
        <div key={key++} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: statusColor, flexShrink: 0, display: 'block' }} />
          <strong style={{ fontSize: '0.88rem', lineHeight: 1.4 }}>{parseInline(content)}</strong>
        </div>
      );
      continue;
    }

    if (t.startsWith('\u2022 ') || t.startsWith('- ')) {
      bullets.push(t.slice(2));
      continue;
    }

    flushBullets();
    output.push(<p key={key++} style={{ margin: '2px 0 6px', lineHeight: 1.6 }}>{parseInline(t)}</p>);
  }
  flushBullets();
  return output.length ? output : <span>{text}</span>;
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  const time = msg.ts
    ? new Date(msg.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <div
      className="fade-in"
      style={{
        display: 'flex',
        gap: 8,
        flexDirection: isUser ? 'row-reverse' : 'row',
        alignItems: 'flex-end',
      }}
    >
      {/* Avatar */}
      {!isUser && (
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: 'var(--ahr-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" />
          </svg>
        </div>
      )}

      <div
        style={{
          maxWidth: '75%',
          display: 'flex',
          flexDirection: 'column',
          gap: 3,
          alignItems: isUser ? 'flex-end' : 'flex-start',
        }}
      >
        <div
          className={isUser ? 'bubble-user' : 'bubble-bot'}
          style={{
            padding: '10px 14px',
            fontSize: '0.875rem',
            lineHeight: 1.6,
            ...(isUser ? { whiteSpace: 'pre-wrap', wordBreak: 'break-word' } : {}),
            border: msg.isError ? '1px solid #fca5a5' : 'none',
          }}
        >
          {isUser ? msg.text : renderBotText(msg.text)}
        </div>
        <span style={{ fontSize: '0.7rem', color: 'var(--ahr-text-3)', paddingLeft: 4 }}>{time}</span>
      </div>
    </div>
  );
}
