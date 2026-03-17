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
    marginBottom: 12,
  },
  bullet: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
    fontSize: 13,
    color: '#cbd5e1',
    lineHeight: 1.5,
  },
  dot: {
    flexShrink: 0,
    width: 6,
    height: 6,
    borderRadius: '50%',
    marginTop: 6,
  },
  tagline: {
    fontSize: 13,
    color: '#cbd5e1',
    lineHeight: 1.6,
    padding: '10px 14px',
    background: '#0f172a',
    borderRadius: 8,
    borderLeft: '3px solid #3b82f6',
  },
};

function BulletList({ items, dotColor }) {
  if (!items?.length) return null;
  return (
    <ul style={{ listStyle: 'none', padding: 0 }}>
      {items.map((item, i) => (
        <li key={i} style={S.bullet}>
          <span style={{ ...S.dot, background: dotColor }} />
          {item}
        </li>
      ))}
    </ul>
  );
}

function AuditSections({ audit }) {
  if (!audit) return null;
  const { brand_summary, positioning_guess, conversion_notes, top_recommendations } = audit;

  const hasContent =
    brand_summary?.length ||
    positioning_guess ||
    conversion_notes?.length ||
    top_recommendations?.length;

  if (!hasContent) return null;

  return (
    <>
      {brand_summary?.length > 0 && (
        <div style={S.card}>
          <p style={S.heading}>Brand Summary</p>
          <BulletList items={brand_summary} dotColor="#3b82f6" />
        </div>
      )}

      {positioning_guess && (
        <div style={S.card}>
          <p style={S.heading}>Positioning</p>
          <p style={S.tagline}>{positioning_guess}</p>
        </div>
      )}

      {conversion_notes?.length > 0 && (
        <div style={S.card}>
          <p style={S.heading}>Conversion Notes</p>
          <BulletList items={conversion_notes} dotColor="#eab308" />
        </div>
      )}

      {top_recommendations?.length > 0 && (
        <div style={S.card}>
          <p style={S.heading}>Top Recommendations</p>
          <BulletList items={top_recommendations} dotColor="#22c55e" />
        </div>
      )}
    </>
  );
}

export default AuditSections;
