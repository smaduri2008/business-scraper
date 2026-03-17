import React, { useState } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'https://business-scraper-production-fac3.up.railway.app';

const S = {
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: '#94a3b8', marginBottom: 6 },
  input: {
    width: '100%', padding: '12px 16px',
    background: '#0f172a', border: '1px solid #334155',
    borderRadius: 8, color: '#e2e8f0', fontSize: 14, outline: 'none',
  },
  select: {
    width: '100%', padding: '12px 16px',
    background: '#0f172a', border: '1px solid #334155',
    borderRadius: 8, color: '#e2e8f0', fontSize: 14, outline: 'none',
  },
  button: {
    width: '100%', padding: '12px', background: '#3b82f6',
    border: 'none', borderRadius: 8, color: '#fff',
    fontSize: 15, fontWeight: 600, cursor: 'pointer', marginTop: 4,
  },
  buttonDisabled: { background: '#475569', cursor: 'not-allowed' },
  error: {
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 8, padding: '12px 16px', color: '#f87171', fontSize: 13, marginTop: 8,
  },
  hint: { fontSize: 11, color: '#475569', marginTop: 4 },
};

function Spinner() {
  return (
    <svg style={{ animation: 'spin 1s linear infinite', width: 20, height: 20, marginRight: 8 }} viewBox="0 0 24 24">
      <style>{`@keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }`}</style>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" opacity={0.25} />
      <path fill="currentColor" opacity={0.75} d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function SearchForm({ onSearch }) {
  const [niche, setNiche] = useState('');
  const [location, setLocation] = useState('');
  const [maxResults, setMaxResults] = useState('10');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ niche, location, max_results: parseInt(maxResults) }),
      });

      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.error || 'Analysis failed');
      }

      const data = await res.json();
      const sorted = (data.businesses || []).sort((a, b) =>
        (b.analysis?.opportunity_score || 0) - (a.analysis?.opportunity_score || 0)
      );
      onSearch(sorted, {
        niche: data.niche, location: data.location,
        processing_time_seconds: data.processing_time_seconds,
        job_id: data.job_id, has_more: data.has_more, total_found: data.total_found,
      });
    } catch (err) {
      setError(err.message || 'Failed to analyse. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: '#1e293b', borderRadius: 16, padding: '28px', boxShadow: '0 4px 24px rgba(0,0,0,0.4)' }}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={S.label} htmlFor="niche">Business Niche</label>
          <input
            id="niche" type="text" value={niche}
            onChange={e => setNiche(e.target.value)}
            placeholder="e.g., medspas, dentists, restaurants"
            style={S.input} required
          />
        </div>
        <div>
          <label style={S.label} htmlFor="location">Location</label>
          <input
            id="location" type="text" value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="e.g., Miami, FL"
            style={S.input} required
          />
        </div>
        <div>
          <label style={S.label} htmlFor="maxResults">Number of Results</label>
          <select id="maxResults" value={maxResults} onChange={e => setMaxResults(e.target.value)} style={S.select}>
            <option value="10">10 businesses (Fast ~30s)</option>
            <option value="25">25 businesses (~1–2 min)</option>
            <option value="50">50 businesses (~3–5 min)</option>
            <option value="100">100 businesses (~10 min)</option>
          </select>
          <p style={S.hint}>💡 First 10 results load instantly. Click "Load More" for additional results.</p>
        </div>
        {error && <div style={S.error}>{error}</div>}
        <button
          type="submit"
          disabled={loading}
          style={{ ...S.button, ...(loading ? S.buttonDisabled : {}) }}
        >
          {loading ? (
            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Spinner /> Analysing Businesses…
            </span>
          ) : '🔍 Analyse Businesses'}
        </button>
        {loading && (
          <p style={{ textAlign: 'center', color: '#475569', fontSize: 12 }}>
            This may take 30–60 seconds. Getting first 10 results…
          </p>
        )}
      </form>
    </div>
  );
}

export default SearchForm;
