'use client';

import { useState } from 'react';

export default function HRPolicyUpload({ tenantId }) {
  const [docType, setDocType] = useState('policy');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  async function onUpload(e) {
    e.preventDefault();
    if (!tenantId) return setMessage('Missing tenant');
    if (!file) return setMessage('Please select a file');

    setUploading(true);
    setMessage('');
    try {
      const form = new FormData();
      form.append('company_id', tenantId);
      form.append('doc_type', docType);
      form.append('file', file);

      const res = await fetch('/api/policies/upload', {
        method: 'POST',
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || 'Upload failed');

      setMessage(`Uploaded successfully: ${data.filename} (${data.chunks_stored} chunks)`);
      setFile(null);
      const input = document.getElementById('policy_file_input');
      if (input) input.value = '';
    } catch (err) {
      setMessage(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--ahr-surface)' }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--ahr-border)' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--ahr-text)' }}>Policy Upload</h3>
        <p style={{ margin: '2px 0 0', fontSize: '0.76rem', color: 'var(--ahr-text-3)' }}>
          Upload updated company policies to the Guide Agent knowledge base
        </p>
      </div>

      <form onSubmit={onUpload} style={{ padding: 16, display: 'grid', gap: 10 }}>
        <label style={label}>Document Type</label>
        <select value={docType} onChange={(e) => setDocType(e.target.value)} style={inputStyle}>
          <option value="policy">Policy</option>
          <option value="leave_policy">Leave Policy</option>
          <option value="onboarding_policy">Onboarding Policy</option>
          <option value="handbook">Employee Handbook</option>
        </select>

        <label style={label}>File (PDF / DOCX / TXT)</label>
        <input
          id="policy_file_input"
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          accept=".pdf,.doc,.docx,.txt"
          style={inputStyle}
        />

        <button type="submit" disabled={uploading} style={btnPrimary}>
          {uploading ? 'Uploading...' : 'Upload Policy'}
        </button>

        {message ? (
          <div style={{ ...msg, color: message.startsWith('Uploaded') ? '#22c55e' : '#ef4444' }}>{message}</div>
        ) : null}
      </form>
    </div>
  );
}

const label = { fontSize: '0.76rem', color: 'var(--ahr-text-3)', fontWeight: 600 };
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
const msg = {
  border: '1px solid var(--ahr-border)',
  borderRadius: 8,
  padding: '8px 10px',
  fontSize: '0.77rem',
  background: 'var(--ahr-bg)',
};
