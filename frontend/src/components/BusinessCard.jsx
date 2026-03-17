import React from 'react';
import WebsiteGrade from './WebsiteGrade';

const S = {
  card: {
    background: '#1e293b', borderRadius: 16,
    padding: '24px', marginBottom: 16,
    boxShadow: '0 2px 12px rgba(0,0,0,0.3)',
    position: 'relative',
  },
  badge: {
    display: 'inline-block', borderRadius: 20,
    padding: '2px 10px', fontSize: 11, fontWeight: 700,
  },
  row: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 13, color: '#94a3b8' },
  tag: {
    display: 'inline-block', background: 'rgba(59,130,246,0.15)',
    color: '#93c5fd', borderRadius: 20, padding: '2px 10px', fontSize: 11,
    margin: '2px 4px 2px 0',
  },
};

function Stars({ rating }) {
  const r = parseFloat(rating) || 0;
  return (
    <span>
      {[1,2,3,4,5].map(i => (
        <span key={i} style={{ color: i <= Math.round(r) ? '#facc15' : '#334155', fontSize: 13 }}>★</span>
      ))}
    </span>
  );
}

function BusinessCard({ business, index }) {
  const score = business.analysis?.opportunity_score || 0;

  const scoreBadge = score >= 75
    ? { label: '🎯 Hot Lead', bg: 'rgba(34,197,94,0.15)', color: '#86efac', border: '1px solid rgba(34,197,94,0.3)' }
    : score >= 60
    ? { label: '✨ Good Target', bg: 'rgba(234,179,8,0.15)', color: '#fde047', border: '1px solid rgba(234,179,8,0.3)' }
    : { label: '📋 Potential', bg: 'rgba(100,116,139,0.15)', color: '#94a3b8', border: '1px solid #334155' };

  return (
    <div style={S.card}>
      {/* Badges */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        {index != null && (
          <span style={{ ...S.badge, background: 'rgba(59,130,246,0.2)', color: '#93c5fd', border: '1px solid rgba(59,130,246,0.3)' }}>
            #{index}
          </span>
        )}
        {score > 0 && (
          <span style={{ ...S.badge, background: scoreBadge.bg, color: scoreBadge.color, border: scoreBadge.border }}>
            {scoreBadge.label}
          </span>
        )}
      </div>

      {/* Name */}
      <h2 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', marginBottom: 4 }}>
        {business.name || 'Unknown Business'}
      </h2>

      {/* Rating */}
      {(business.rating || business.reviews_count) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
          {business.rating && <Stars rating={business.rating} />}
          {business.rating && <span style={{ fontSize: 13, color: '#cbd5e1' }}>{business.rating}</span>}
          {business.reviews_count && <span style={{ fontSize: 12, color: '#64748b' }}>({business.reviews_count.toLocaleString()} reviews)</span>}
        </div>
      )}

      {/* Contact */}
      {business.address && <div style={S.row}>📍 {business.address}</div>}
      {business.phone && <div style={S.row}>📞 {business.phone}</div>}
      {business.website && (
        <div style={S.row}>
          🌐{' '}
          <a href={business.website} target="_blank" rel="noopener noreferrer" style={{ color: '#60a5fa', fontSize: 13 }}>
            {business.website}
          </a>
        </div>
      )}

      {/* Website Grade */}
      {business.website_grade && <WebsiteGrade grade={business.website_grade} />}

      {/* Services */}
      {business.services?.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <p style={{ fontSize: 11, color: '#475569', marginBottom: 4, textTransform: 'uppercase' }}>Services</p>
          <div>{business.services.slice(0, 6).map((s, i) => <span key={i} style={S.tag}>{s}</span>)}</div>
        </div>
      )}

      {/* Analysis snippet */}
      {business.analysis?.competitive_assessment && (
        <p style={{ marginTop: 12, fontSize: 12, color: '#64748b', fontStyle: 'italic', lineHeight: 1.5 }}>
          {business.analysis.competitive_assessment}
        </p>
      )}
    </div>
  );
}

export default BusinessCard;
