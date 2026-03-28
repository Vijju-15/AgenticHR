'use client';

import { useEffect, useState } from 'react';

const ORCHESTRATOR_URL =
  typeof window !== 'undefined' && process.env.NEXT_PUBLIC_ORCHESTRATOR_URL
    ? process.env.NEXT_PUBLIC_ORCHESTRATOR_URL
    : 'http://localhost:8001';

export default function HRLeaveApprovals({ tenantId, approverId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [decisionNote, setDecisionNote] = useState({});
  const [activeRequest, setActiveRequest] = useState(null);
  const [savingDecision, setSavingDecision] = useState(false);

  async function fetchPending() {
    if (!tenantId) return;
    setLoading(true);
    setError('');
    try {
      const qs = new URLSearchParams({ tenant_id: tenantId, status: 'PENDING' });
      const res = await fetch(`/api/leave/requests?${qs}`, { cache: 'no-store' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load leave requests');
      setItems(data.leave_requests || []);
    } catch (e) {
      setError(e.message || 'Failed to load leave requests');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchPending();
  }, [tenantId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function decide(requestId, decision) {
    setSavingDecision(true);
    try {
      const note = decisionNote[requestId] || '';
      const safeRequestId = encodeURIComponent(requestId);
      const payload = {
        approver_id: approverId || 'hr_admin',
        decision,
        approver_note: note,
      };

      let res = await fetch(`/api/leave/requests/${safeRequestId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      // Fallback: call orchestrator directly if proxy route fails unexpectedly.
      if (res.status >= 500) {
        res = await fetch(`${ORCHESTRATOR_URL}/leave/requests/${safeRequestId}/decision`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || 'Decision failed');
      setActiveRequest(null);
      await fetchPending();
    } catch (e) {
      alert(e.message || 'Decision failed');
    } finally {
      setSavingDecision(false);
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--ahr-surface)' }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--ahr-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--ahr-text)' }}>Leave Approvals</h3>
          <p style={{ margin: '2px 0 0', fontSize: '0.76rem', color: 'var(--ahr-text-3)' }}>Approve or reject pending requests</p>
        </div>
        <button onClick={fetchPending} style={btnGhost}>Refresh</button>
      </div>

      <div style={{ padding: '8px 16px', fontSize: '0.76rem', color: 'var(--ahr-text-3)', borderBottom: '1px solid var(--ahr-border)' }}>
        {loading ? 'Loading...' : `${items.length} pending request${items.length === 1 ? '' : 's'}`}
        {error ? <span style={{ color: '#ef4444', marginLeft: 8 }}>{error}</span> : null}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
        {items.length === 0 ? (
          <div style={emptyBox}>No pending leave requests.</div>
        ) : (
          items.map((r) => (
            <button
              key={r.request_id}
              style={cardButton}
              onClick={() => setActiveRequest(r)}
              type="button"
            >
              <div style={card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--ahr-text)' }}>{r.employee_name}</div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--ahr-text-3)' }}>{r.employee_email}</div>
                </div>
                <span style={badgePending}>PENDING</span>
              </div>

              <div style={{ marginTop: 8, fontSize: '0.79rem', color: 'var(--ahr-text-2)' }}>
                {r.leave_type} leave | {r.start_date} to {r.end_date} | {r.num_days} day(s)
              </div>
              <div style={{ marginTop: 6, fontSize: '0.78rem', color: 'var(--ahr-text-2)', textAlign: 'left' }}>
                Reason preview: {String(r.reason || 'No reason provided').slice(0, 60)}{String(r.reason || '').length > 60 ? '…' : ''}
              </div>
              <div style={{ marginTop: 8, fontSize: '0.72rem', color: 'var(--ahr-accent)', textAlign: 'left', fontWeight: 600 }}>
                Click to review full reason and decide
              </div>
              </div>
            </button>
          ))
        )}
      </div>

      {activeRequest ? (
        <div style={modalBackdrop} onClick={() => setActiveRequest(null)}>
          <div style={modalCard} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'start' }}>
              <div>
                <h4 style={{ margin: 0, color: 'var(--ahr-text)', fontSize: '0.95rem' }}>Leave Request Review</h4>
                <div style={{ marginTop: 4, fontSize: '0.78rem', color: 'var(--ahr-text-3)' }}>{activeRequest.request_id}</div>
              </div>
              <button type="button" style={closeBtn} onClick={() => setActiveRequest(null)}>Close</button>
            </div>

            <div style={{ marginTop: 12, fontSize: '0.84rem', color: 'var(--ahr-text)' }}>
              <div><strong>Employee:</strong> {activeRequest.employee_name}</div>
              <div style={{ marginTop: 4 }}><strong>Email:</strong> {activeRequest.employee_email}</div>
              <div style={{ marginTop: 4 }}><strong>Leave:</strong> {activeRequest.leave_type} | {activeRequest.start_date} to {activeRequest.end_date} | {activeRequest.num_days} day(s)</div>
            </div>

            <div style={reasonBox}>
              <div style={{ fontSize: '0.78rem', color: 'var(--ahr-text-3)', marginBottom: 6 }}>Reason from intern</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--ahr-text)', lineHeight: 1.5 }}>{activeRequest.reason || 'No reason provided.'}</div>
            </div>

              <textarea
                placeholder="Optional note"
                value={decisionNote[activeRequest.request_id] || ''}
                onChange={(e) => setDecisionNote((prev) => ({ ...prev, [activeRequest.request_id]: e.target.value }))}
                style={noteInput}
              />

              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button
                  onClick={() => decide(activeRequest.request_id, 'rejected')}
                  style={btnReject}
                  disabled={savingDecision}
                >
                  {savingDecision ? 'Saving...' : 'Reject'}
                </button>
                <button
                  onClick={() => decide(activeRequest.request_id, 'approved')}
                  style={btnApprove}
                  disabled={savingDecision}
                >
                  {savingDecision ? 'Saving...' : 'Approve'}
                </button>
              </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

const btnGhost = {
  border: '1px solid var(--ahr-border)',
  background: 'var(--ahr-surface-2)',
  color: 'var(--ahr-text-2)',
  borderRadius: 8,
  fontSize: '0.75rem',
  padding: '5px 10px',
  cursor: 'pointer',
};

const card = {
  border: '1px solid var(--ahr-border)',
  borderRadius: 12,
  background: 'var(--ahr-bg)',
  padding: 12,
  marginBottom: 10,
};

const cardButton = {
  border: 'none',
  background: 'transparent',
  padding: 0,
  width: '100%',
  textAlign: 'left',
  cursor: 'pointer',
};

const badgePending = {
  alignSelf: 'start',
  fontSize: '0.68rem',
  fontWeight: 700,
  color: '#f59e0b',
  background: 'rgba(245,158,11,0.14)',
  borderRadius: 999,
  padding: '2px 8px',
};

const noteInput = {
  width: '100%',
  marginTop: 10,
  marginBottom: 8,
  minHeight: 58,
  borderRadius: 8,
  border: '1px solid var(--ahr-border)',
  background: 'var(--ahr-surface)',
  color: 'var(--ahr-text)',
  padding: 8,
  fontSize: '0.78rem',
  resize: 'vertical',
};

const btnApprove = {
  border: 'none',
  background: 'linear-gradient(135deg,#22c55e,#16a34a)',
  color: '#fff',
  borderRadius: 8,
  fontSize: '0.75rem',
  fontWeight: 700,
  padding: '6px 12px',
  cursor: 'pointer',
};

const btnReject = {
  border: '1px solid rgba(239,68,68,0.4)',
  background: 'rgba(239,68,68,0.12)',
  color: '#ef4444',
  borderRadius: 8,
  fontSize: '0.75rem',
  fontWeight: 700,
  padding: '6px 12px',
  cursor: 'pointer',
};

const emptyBox = {
  border: '1px dashed var(--ahr-border)',
  borderRadius: 12,
  padding: '18px 16px',
  textAlign: 'center',
  color: 'var(--ahr-text-3)',
  fontSize: '0.84rem',
};

const modalBackdrop = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(2,6,23,0.65)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1200,
  padding: 14,
};

const modalCard = {
  width: 'min(560px, 96vw)',
  maxHeight: '90vh',
  overflowY: 'auto',
  borderRadius: 14,
  border: '1px solid var(--ahr-border)',
  background: 'var(--ahr-surface)',
  padding: 14,
};

const closeBtn = {
  border: '1px solid var(--ahr-border)',
  background: 'var(--ahr-surface-2)',
  color: 'var(--ahr-text-2)',
  borderRadius: 8,
  fontSize: '0.75rem',
  padding: '5px 10px',
  cursor: 'pointer',
};

const reasonBox = {
  marginTop: 12,
  border: '1px solid var(--ahr-border)',
  borderRadius: 10,
  background: 'var(--ahr-bg)',
  padding: 10,
};
