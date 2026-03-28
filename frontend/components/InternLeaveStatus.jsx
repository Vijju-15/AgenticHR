'use client';

import { useEffect, useState } from 'react';

export default function InternLeaveStatus({ tenantId, employeeEmail, employeeId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function fetchMyLeaves() {
    if (!tenantId || (!employeeEmail && !employeeId)) return;
    setLoading(true);
    setError('');
    try {
      const qs = new URLSearchParams({ tenant_id: tenantId });
      if (employeeEmail) {
        qs.set('employee_email', employeeEmail);
      } else if (employeeId) {
        qs.set('employee_id', employeeId);
      }

      const res = await fetch(`/api/leave/requests?${qs.toString()}`, { cache: 'no-store' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load leave status');
      setItems(data.leave_requests || []);
    } catch (e) {
      setError(e.message || 'Failed to load leave status');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchMyLeaves();
  }, [tenantId, employeeEmail, employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--ahr-surface)' }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--ahr-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--ahr-text)' }}>My Leave Requests</h3>
          <p style={{ margin: '2px 0 0', fontSize: '0.76rem', color: 'var(--ahr-text-3)' }}>
            Track approvals and rejections from HR
          </p>
        </div>
        <button onClick={fetchMyLeaves} style={btnGhost}>Refresh</button>
      </div>

      <div style={{ padding: '8px 16px', fontSize: '0.76rem', color: 'var(--ahr-text-3)', borderBottom: '1px solid var(--ahr-border)' }}>
        {loading ? 'Loading...' : `${items.length} request${items.length === 1 ? '' : 's'}`}
        {error ? <span style={{ color: '#ef4444', marginLeft: 8 }}>{error}</span> : null}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
        {items.length === 0 ? (
          <div style={emptyBox}>No leave requests yet. Apply from chat and your request will appear here.</div>
        ) : (
          items.map((r) => (
            <div key={r.request_id} style={card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ fontSize: '0.86rem', color: 'var(--ahr-text)', fontWeight: 700 }}>{r.leave_type} leave</div>
                <span style={statusBadge(r.status)}>{r.status}</span>
              </div>

              <div style={{ marginTop: 7, fontSize: '0.8rem', color: 'var(--ahr-text-2)' }}>
                {r.start_date} to {r.end_date} | {r.num_days} day(s)
              </div>
              <div style={{ marginTop: 6, fontSize: '0.8rem', color: 'var(--ahr-text-2)' }}>
                <strong>Reason:</strong> {r.reason || 'No reason provided'}
              </div>

              {r.status !== 'PENDING' ? (
                <div style={decisionBox}>
                  <div style={{ fontSize: '0.74rem', color: 'var(--ahr-text-3)' }}>HR Decision Note</div>
                  <div style={{ marginTop: 4, fontSize: '0.8rem', color: 'var(--ahr-text)' }}>
                    {r.approver_note || 'No note from HR.'}
                  </div>
                </div>
              ) : null}

              <div style={{ marginTop: 8, fontSize: '0.72rem', color: 'var(--ahr-text-3)' }}>
                Request ID: {r.request_id}
              </div>
            </div>
          ))
        )}
      </div>
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

const decisionBox = {
  marginTop: 10,
  border: '1px solid var(--ahr-border)',
  borderRadius: 10,
  background: 'var(--ahr-surface)',
  padding: 8,
};

const emptyBox = {
  border: '1px dashed var(--ahr-border)',
  borderRadius: 12,
  padding: '18px 16px',
  textAlign: 'center',
  color: 'var(--ahr-text-3)',
  fontSize: '0.84rem',
};

function statusBadge(status) {
  const current = String(status || 'PENDING').toUpperCase();
  if (current === 'APPROVED') {
    return {
      fontSize: '0.68rem',
      fontWeight: 700,
      color: '#22c55e',
      background: 'rgba(34,197,94,0.14)',
      borderRadius: 999,
      padding: '2px 8px',
      alignSelf: 'start',
    };
  }
  if (current === 'REJECTED') {
    return {
      fontSize: '0.68rem',
      fontWeight: 700,
      color: '#ef4444',
      background: 'rgba(239,68,68,0.14)',
      borderRadius: 999,
      padding: '2px 8px',
      alignSelf: 'start',
    };
  }
  return {
    fontSize: '0.68rem',
    fontWeight: 700,
    color: '#f59e0b',
    background: 'rgba(245,158,11,0.14)',
    borderRadius: 999,
    padding: '2px 8px',
    alignSelf: 'start',
  };
}