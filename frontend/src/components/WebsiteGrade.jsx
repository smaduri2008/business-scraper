import React, { useState } from 'react';

function ScoreBar({ score, max = 100, color = 'blue' }) {
  const pct = Math.round((score / max) * 100);
  const colorMap = {
    blue: '#3b82f6',
    green: '#22c55e',
    yellow: '#eab308',
    red: '#ef4444',
  };
  const bar = colorMap[color] || colorMap.blue;
  return (
    <div style={{ background: '#1e293b', borderRadius: 4, height: 8, overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, background: bar, height: '100%', transition: 'width 0.5s' }} />
    </div>
  );
}

function scoreColor(score, max) {
  const pct = score / max;
  if (pct >= 0.7) return '#22c55e';
  if (pct >= 0.5) return '#eab308';
  return '#ef4444';
}

function WebsiteGrade({ grade }) {
  const [expanded, setExpanded] = useState(false);
  if (!grade || grade.total_score === 0) return null;

  const total = grade.total_score;
  const wq = grade.website_quality_score;
  const dp = grade.digital_presence_score;

  return (
    <div style={{ background: '#0f172a', borderRadius: 12, padding: '16px', marginTop: 12 }}>
      {/* Total Score */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 1 }}>
          Website Score
        </span>
        <span style={{ fontSize: 22, fontWeight: 700, color: scoreColor(total, 100) }}>
          {total}<span style={{ fontSize: 13, color: '#64748b' }}>/100</span>
        </span>
      </div>
      <ScoreBar score={total} max={100} color={total >= 70 ? 'green' : total >= 50 ? 'yellow' : 'red'} />

      {/* Sub-scores */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 14 }}>
        <div>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>Website Quality</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: scoreColor(wq, 50) }}>{wq}<span style={{ fontSize: 11, color: '#475569' }}>/50</span></div>
          <ScoreBar score={wq} max={50} color={wq >= 35 ? 'green' : wq >= 25 ? 'yellow' : 'red'} />
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>Digital Presence</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: scoreColor(dp, 50) }}>{dp}<span style={{ fontSize: 11, color: '#475569' }}>/50</span></div>
          <ScoreBar score={dp} max={50} color={dp >= 35 ? 'green' : dp >= 25 ? 'yellow' : 'red'} />
        </div>
      </div>

      {/* Toggle Details */}
      <button
        onClick={() => setExpanded(v => !v)}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: '#3b82f6', fontSize: 12, marginTop: 12, padding: 0,
        }}
      >
        {expanded ? '▲ Hide details' : '▼ Show details'}
      </button>

      {expanded && (
        <div style={{ marginTop: 12 }}>
          {grade.strengths?.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <p style={{ fontSize: 11, fontWeight: 600, color: '#22c55e', textTransform: 'uppercase', marginBottom: 4 }}>Strengths</p>
              <ul style={{ paddingLeft: 16 }}>
                {grade.strengths.map((s, i) => (
                  <li key={i} style={{ fontSize: 12, color: '#94a3b8', marginBottom: 2 }}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {grade.weaknesses?.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <p style={{ fontSize: 11, fontWeight: 600, color: '#ef4444', textTransform: 'uppercase', marginBottom: 4 }}>Weaknesses</p>
              <ul style={{ paddingLeft: 16 }}>
                {grade.weaknesses.map((w, i) => (
                  <li key={i} style={{ fontSize: 12, color: '#94a3b8', marginBottom: 2 }}>{w}</li>
                ))}
              </ul>
            </div>
          )}
          {grade.recommendations?.length > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, color: '#3b82f6', textTransform: 'uppercase', marginBottom: 4 }}>Recommendations</p>
              <ul style={{ paddingLeft: 16 }}>
                {grade.recommendations.map((r, i) => (
                  <li key={i} style={{ fontSize: 12, color: '#94a3b8', marginBottom: 2 }}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default WebsiteGrade;
