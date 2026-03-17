import React, { useState } from 'react';
import WebsiteGrade from './WebsiteGrade';
import BrandInfo from './BrandInfo';
import AuditSections from './AuditSections';

const API_URL = process.env.REACT_APP_API_URL || 'https://business-scraper-production-fac3.up.railway.app';

const S = {
  container: { maxWidth: 800, margin: '0 auto', padding: '0 16px' },
  form: {
    background: '#1e293b',
    borderRadius: 16,
    padding: '28px',
    boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
  },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: '#94a3b8', marginBottom: 6 },
  input: {
    width: '100%',
    padding: '12px 16px',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: 8,
    color: '#e2e8f0',
    fontSize: 14,
    outline: 'none',
  },
  button: {
    width: '100%',
    padding: '12px',
    background: '#3b82f6',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: 16,
    transition: 'background 0.2s',
  },
  buttonDisabled: {
    background: '#475569',
    cursor: 'not-allowed',
  },
  error: {
    background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 8,
    padding: '12px 16px',
    color: '#f87171',
    fontSize: 13,
    marginTop: 12,
  },
  hint: { fontSize: 11, color: '#475569', marginTop: 6 },
};

function Spinner() {
  return (
    <svg
      style={{ animation: 'spin 1s linear infinite', width: 20, height: 20, marginRight: 8 }}
      viewBox="0 0 24 24"
    >
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" opacity={0.25} />
      <path fill="currentColor" opacity={0.75} d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function WebsiteAudit() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await fetch(`${API_URL}/api/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || `Request failed (${res.status})`);
      }

      setResult(data);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={S.container}>
      {/* ── Input form ── */}
      <div style={S.form}>
        <form onSubmit={handleSubmit}>
          <label style={S.label} htmlFor="audit-url">
            Website URL
          </label>
          <input
            id="audit-url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            style={S.input}
            disabled={loading}
            required
          />
          <p style={S.hint}>Paste any business website URL to run a full brand audit.</p>

          {error && <div style={S.error}>{error}</div>}

          <button
            type="submit"
            disabled={loading || !url.trim()}
            style={{ ...S.button, ...(loading || !url.trim() ? S.buttonDisabled : {}) }}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Spinner /> Auditing website…
              </span>
            ) : (
              '🔍 Run Brand Audit'
            )}
          </button>
        </form>

        {loading && (
          <p style={{ textAlign: 'center', color: '#475569', fontSize: 12, marginTop: 10 }}>
            This may take 30–60 seconds while we scrape and analyse the site.
          </p>
        )}
      </div>

      {/* ── Results ── */}
      {result && (
        <div style={{ marginTop: 24 }}>
          {/* URL header */}
          <div style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 11, color: '#475569', marginBottom: 2 }}>Audited URL</p>
            <a
              href={result.normalized_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#60a5fa', fontSize: 14, wordBreak: 'break-all' }}
            >
              {result.normalized_url}
            </a>
          </div>

          {/* Website Grade */}
          <WebsiteGrade grade={result.website_grade} />

          {/* Brand Info */}
          <BrandInfo brand={result.brand} />

          {/* AI Audit Sections */}
          <AuditSections audit={result.audit} />

          {/* Website data summary */}
          <WebsiteDataSummary data={result.website_data} />
        </div>
      )}
    </div>
  );
}

function WebsiteDataSummary({ data }) {
  if (!data) return null;

  const stats = [
    { label: 'Text length', value: data.text_length ? `${data.text_length.toLocaleString()} chars` : '—' },
    { label: 'Mobile ready', value: data.has_mobile_viewport ? '✅ Yes' : '❌ No' },
    { label: 'Images', value: data.images_count != null ? `${data.images_count} (${data.images_with_alt} with alt)` : '—' },
    { label: 'Internal links', value: data.internal_links_count != null ? data.internal_links_count : '—' },
    { label: 'Services found', value: data.services?.length || 0 },
    { label: 'Prices found', value: data.prices?.length || 0 },
    { label: 'CTAs', value: data.cta_buttons?.length || 0 },
  ];

  return (
    <div style={{ background: '#1e293b', borderRadius: 12, padding: '16px', marginBottom: 16 }}>
      <p style={{ fontSize: 13, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
        Website Data
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8 }}>
        {stats.map(({ label, value }) => (
          <div key={label} style={{ background: '#0f172a', borderRadius: 8, padding: '10px 12px' }}>
            <p style={{ fontSize: 10, color: '#475569', textTransform: 'uppercase', marginBottom: 2 }}>{label}</p>
            <p style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 600 }}>{value}</p>
          </div>
        ))}
      </div>

      {data.services?.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <p style={{ fontSize: 11, color: '#475569', marginBottom: 6 }}>Services</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {data.services.slice(0, 10).map((s, i) => (
              <span key={i} style={{ background: 'rgba(59,130,246,0.15)', color: '#93c5fd', borderRadius: 20, padding: '2px 10px', fontSize: 11 }}>
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {data.cta_buttons?.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <p style={{ fontSize: 11, color: '#475569', marginBottom: 6 }}>CTAs</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {data.cta_buttons.map((c, i) => (
              <span key={i} style={{ background: 'rgba(34,197,94,0.12)', color: '#86efac', borderRadius: 20, padding: '2px 10px', fontSize: 11 }}>
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default WebsiteAudit;
