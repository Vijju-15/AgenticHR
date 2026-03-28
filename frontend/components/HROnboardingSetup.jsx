'use client';

import { useEffect, useState } from 'react';

const DEPARTMENTS = ['Engineering', 'HR', 'Finance', 'Operations', 'Marketing', 'Sales'];

export default function HROnboardingSetup({ tenantId }) {
  const [form, setForm] = useState({
    employee_name: '',
    employee_email: '',
    role: 'intern',
    department: 'Engineering',
    start_date: '',
    manager_email: '',
    manager_id: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [journeys, setJourneys] = useState([]);
  const [loadingJourneys, setLoadingJourneys] = useState(false);

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function initiate(e) {
    e.preventDefault();
    if (!tenantId) return setMessage('Missing tenant_id');

    const employeeName = form.employee_name.trim();
    const employeeEmail = form.employee_email.trim().toLowerCase();
    if (!employeeName || !employeeEmail || !form.start_date) {
      setMessage('Please fill employee name, email, and start date.');
      return;
    }

    const generatedEmployeeId = `emp_${employeeEmail.split('@')[0].replace(/[^a-z0-9]/gi, '').toLowerCase()}`;

    setSubmitting(true);
    setMessage('');
    try {
      const res = await fetch('/api/onboarding/initiate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: tenantId,
          employee_id: generatedEmployeeId,
          employee_name: employeeName,
          employee_email: employeeEmail,
          role: form.role,
          department: form.department,
          start_date: form.start_date,
          manager_id: form.manager_id || null,
          manager_email: form.manager_email || null,
          metadata: { initiated_from: 'hr_dashboard' },
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || 'Failed to initiate onboarding');

      setMessage(`Onboarding initiated. Workflow: ${data.workflow_id || 'created'}`);
      await fetchJourneys();
    } catch (err) {
      setMessage(`Failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  async function fetchJourneys() {
    if (!tenantId) return;
    setLoadingJourneys(true);
    try {
      const qs = new URLSearchParams({ tenant_id: tenantId });
      const res = await fetch(`/api/onboarding/journeys?${qs}`, { cache: 'no-store' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load journeys');
      setJourneys(data.journeys || []);
    } catch {
      setJourneys([]);
    } finally {
      setLoadingJourneys(false);
    }
  }

  useEffect(() => {
    fetchJourneys();
  }, [tenantId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--ahr-surface)' }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--ahr-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--ahr-text)' }}>Employee Setup</h3>
          <p style={{ margin: '2px 0 0', fontSize: '0.76rem', color: 'var(--ahr-text-3)' }}>
            Triggers provisioning workflow: employee record, ID, credentials, onboarding profile and checklist
          </p>
        </div>
        <button onClick={fetchJourneys} style={btnGhost}>Refresh</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12, padding: 12, borderBottom: '1px solid var(--ahr-border)' }}>
        <form onSubmit={initiate} style={{ display: 'grid', gap: 8 }}>
          <input value={form.employee_name} onChange={(e) => setField('employee_name', e.target.value)} placeholder="Employee full name" style={inputStyle} />
          <input value={form.employee_email} onChange={(e) => setField('employee_email', e.target.value)} placeholder="Employee email" style={inputStyle} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <input value={form.role} onChange={(e) => setField('role', e.target.value)} placeholder="Role (intern/fresher/engineer)" style={inputStyle} />
            <select value={form.department} onChange={(e) => setField('department', e.target.value)} style={inputStyle}>
              {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <input type="date" value={form.start_date} onChange={(e) => setField('start_date', e.target.value)} style={inputStyle} />
            <input value={form.manager_email} onChange={(e) => setField('manager_email', e.target.value)} placeholder="Manager email (optional)" style={inputStyle} />
          </div>

          <button type="submit" disabled={submitting} style={btnPrimary}>{submitting ? 'Initiating...' : 'Initiate Onboarding'}</button>
          {message ? <div style={{ ...msg, color: message.startsWith('Onboarding') ? '#22c55e' : '#ef4444' }}>{message}</div> : null}
        </form>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ahr-text)', marginBottom: 8 }}>
          Onboarding Progress ({loadingJourneys ? 'loading...' : journeys.length})
        </div>

        {journeys.length === 0 ? (
          <div style={emptyBox}>No onboarding journeys yet.</div>
        ) : (
          journeys.map((j) => (
            <div key={j.journey_id} style={card}>
              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--ahr-text)' }}>{j.employee_name}</div>
              <div style={{ fontSize: '0.77rem', color: 'var(--ahr-text-3)', marginTop: 2 }}>
                {j.employee_id} | start: {j.start_date}
              </div>
              <div style={{ marginTop: 8, fontSize: '0.76rem', color: 'var(--ahr-text-2)' }}>
                Day: {j.current_day} | Progress: {j.progress_pct}%
              </div>
              <div style={{ height: 8, background: 'var(--ahr-surface-2)', borderRadius: 999, marginTop: 6, overflow: 'hidden' }}>
                <div style={{ width: `${Math.max(0, Math.min(100, j.progress_pct || 0))}%`, height: '100%', background: 'linear-gradient(135deg,#22c55e,#16a34a)' }} />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

const inputStyle = {
  border: '1px solid var(--ahr-border)',
  borderRadius: 8,
  background: 'var(--ahr-bg)',
  color: 'var(--ahr-text)',
  padding: '8px 10px',
  fontSize: '0.8rem',
};

const btnPrimary = {
  marginTop: 6,
  border: 'none',
  borderRadius: 8,
  background: 'var(--ahr-gradient)',
  color: '#fff',
  fontWeight: 700,
  padding: '9px 12px',
  fontSize: '0.78rem',
  cursor: 'pointer',
};

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

const msg = {
  border: '1px solid var(--ahr-border)',
  borderRadius: 8,
  padding: '8px 10px',
  fontSize: '0.77rem',
  background: 'var(--ahr-bg)',
};

const emptyBox = {
  border: '1px dashed var(--ahr-border)',
  borderRadius: 12,
  padding: '18px 16px',
  textAlign: 'center',
  color: 'var(--ahr-text-3)',
  fontSize: '0.84rem',
};
