import React, { useState } from 'react';
import SearchForm from './components/SearchForm';
import BusinessCard from './components/BusinessCard';
import WebsiteAudit from './components/WebsiteAudit';

const TABS = [
  { id: 'finder', label: '🏢 Business Finder' },
  { id: 'audit', label: '🔍 Website Audit' },
];

const S = {
  app: { minHeight: '100vh', background: '#0f172a', color: '#e2e8f0' },
  header: {
    background: '#1e293b',
    padding: '20px 24px',
    borderBottom: '1px solid #334155',
    marginBottom: 32,
  },
  headerInner: { maxWidth: 1100, margin: '0 auto', display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' },
  logo: { fontSize: 22, fontWeight: 800, color: '#f1f5f9' },
  tagline: { fontSize: 12, color: '#64748b' },
  tabs: { display: 'flex', gap: 4, background: '#0f172a', borderRadius: 10, padding: 4 },
  tab: {
    padding: '8px 18px', border: 'none', borderRadius: 8,
    cursor: 'pointer', fontSize: 13, fontWeight: 600, transition: 'all 0.15s',
  },
  tabActive: { background: '#3b82f6', color: '#fff' },
  tabInactive: { background: 'transparent', color: '#64748b' },
  main: { maxWidth: 1100, margin: '0 auto', padding: '0 16px 48px' },
};

function BusinessFinderTab() {
  const [businesses, setBusinesses] = useState([]);
  const [meta, setMeta] = useState(null);

  const handleSearch = (sorted, metadata) => {
    setBusinesses(sorted);
    setMeta(metadata);
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 24, alignItems: 'start' }}>
      <div style={{ position: 'sticky', top: 24 }}>
        <SearchForm onSearch={handleSearch} />
      </div>
      <div>
        {meta && (
          <div style={{ marginBottom: 16, padding: '12px 16px', background: '#1e293b', borderRadius: 10 }}>
            <p style={{ fontSize: 13, color: '#64748b' }}>
              Found <strong style={{ color: '#93c5fd' }}>{meta.total_found}</strong> businesses for{' '}
              <strong style={{ color: '#f1f5f9' }}>{meta.niche}</strong> in{' '}
              <strong style={{ color: '#f1f5f9' }}>{meta.location}</strong>
              {' '}· {meta.processing_time_seconds}s
            </p>
          </div>
        )}
        {businesses.map((biz, i) => (
          <BusinessCard key={biz.id || i} business={biz} index={i + 1} />
        ))}
        {businesses.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#475569' }}>
            <p style={{ fontSize: 40, marginBottom: 12 }}>🏢</p>
            <p style={{ fontSize: 15 }}>Search for businesses above to see results.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('finder');

  return (
    <div style={S.app}>
      {/* Header */}
      <header style={S.header}>
        <div style={S.headerInner}>
          <div>
            <div style={S.logo}>Business Scraper</div>
            <div style={S.tagline}>Find & audit local business websites</div>
          </div>

          {/* Tab switcher */}
          <div style={{ marginLeft: 'auto' }}>
            <div style={S.tabs}>
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    ...S.tab,
                    ...(activeTab === tab.id ? S.tabActive : S.tabInactive),
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main style={S.main}>
        {activeTab === 'finder' && <BusinessFinderTab />}
        {activeTab === 'audit' && <WebsiteAudit />}
      </main>
    </div>
  );
}
