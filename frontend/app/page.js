'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const submit = async () => {
    const value = email.trim().toLowerCase();

    if (!value) {
      setError('Please enter your work email.');
      return;
    }

    setLoading(true);
    setError('');

    let timeoutId;
    try {
      const controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort(), 10000);
      const res = await fetch('/api/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: value }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || 'Authentication failed. Please try again.');
        setLoading(false);
        return;
      }

      sessionStorage.setItem('ahr_user', JSON.stringify(data));
      const target = data.role === 'hr' ? '/hr' : '/intern';
      router.replace(target);
      // Fallback in case client router is blocked by a transient runtime issue.
      setTimeout(() => {
        if (window.location.pathname === '/') {
          window.location.assign(target);
        }
      }, 150);
      setLoading(false);
    } catch {
      setError('Could not connect to server. Make sure the backend is running.');
      setLoading(false);
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    submit();
  };

  return (
    <div className="landing-bg metal-login-page">
      <div className="metal-grid" aria-hidden="true" />
      <div className="metal-blob metal-blob-a" aria-hidden="true" />
      <div className="metal-blob metal-blob-b" aria-hidden="true" />
      <div className="metal-blob metal-blob-c" aria-hidden="true" />

      <div className="login-shell">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">
            <svg width="30" height="30" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="12" r="4" stroke="white" strokeWidth="2" fill="none" />
              <path d="M8 26c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none" />
            </svg>
          </div>
          <h1 className="brand-title">AgenticHR</h1>
          <p className="brand-subtitle">AI-powered HR assistant</p>
        </div>

        <div className="glass-card metal-card">
          <div className="metal-sheen" aria-hidden="true" />
          <h2 className="login-title">Sign in</h2>
          <p className="login-subtitle">Enter your work email to continue</p>

          <form onSubmit={onSubmit} className="login-form">
            <label className="email-label">Work Email</label>
            <input
              className={`email-input ${error ? 'email-input-error' : ''}`}
              type="email"
              autoComplete="email"
              placeholder="you@acme.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />

            {error && <p className="login-error">{error}</p>}

            <button type="submit" disabled={loading} className="login-submit-btn">
              {loading ? (
                <>
                  <span className="login-spinner" />
                  Signing in...
                </>
              ) : (
                'Continue'
              )}
            </button>
          </form>

          <div className="login-hint-box">
            <p className="login-hint-text">
              <strong>HR:</strong> hr@acme.com | hr.manager@acme.com
              <br />
              <strong>Intern:</strong> intern@acme.com | fresher@acme.com
            </p>
          </div>
        </div>

        <p className="login-footer">(c) 2025 AgenticHR | Powered by Gemini AI</p>
      </div>
    </div>
  );
}
