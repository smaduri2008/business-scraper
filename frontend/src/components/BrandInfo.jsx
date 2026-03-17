import React from 'react';

const S = {
  card: {
    background: '#1e293b',
    borderRadius: 12,
    padding: '20px',
    marginBottom: 16,
  },
  heading: {
    fontSize: 13,
    fontWeight: 700,
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 10,
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  label: { fontSize: 12, color: '#64748b', minWidth: 60 },
  value: { fontSize: 13, color: '#e2e8f0' },
  tag: {
    display: 'inline-block',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: 20,
    padding: '2px 10px',
    fontSize: 11,
    color: '#94a3b8',
    marginRight: 4,
    marginBottom: 4,
  },
  link: { color: '#3b82f6', textDecoration: 'none', fontSize: 12 },
};

function pill(label, href) {
  return (
    <a key={label} href={href} target="_blank" rel="noopener noreferrer" style={{ ...S.tag, color: '#60a5fa' }}>
      {label}
    </a>
  );
}

function BrandInfo({ brand }) {
  if (!brand) return null;
  const { name, phones, emails, addresses, socials } = brand;

  const hasSomething =
    name || phones?.length || emails?.length || addresses?.length || Object.keys(socials || {}).length;
  if (!hasSomething) return null;

  return (
    <div style={S.card}>
      <p style={S.heading}>Brand Info</p>

      {name && (
        <div style={S.row}>
          <span style={S.label}>Name</span>
          <span style={{ ...S.value, fontWeight: 600 }}>{name}</span>
        </div>
      )}

      {phones?.length > 0 && (
        <div style={S.row}>
          <span style={S.label}>Phone</span>
          <span style={S.value}>{phones.join(', ')}</span>
        </div>
      )}

      {emails?.length > 0 && (
        <div style={S.row}>
          <span style={S.label}>Email</span>
          <span style={S.value}>{emails.join(', ')}</span>
        </div>
      )}

      {addresses?.length > 0 && (
        <div style={S.row}>
          <span style={S.label}>Address</span>
          <span style={S.value}>{addresses[0]}</span>
        </div>
      )}

      {Object.keys(socials || {}).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <span style={{ ...S.label, display: 'block', marginBottom: 4 }}>Socials</span>
          <div>
            {Object.entries(socials).map(([platform, url]) =>
              pill(platform.charAt(0).toUpperCase() + platform.slice(1), url)
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default BrandInfo;
