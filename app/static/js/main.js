/* ── OffshoreIQ Frontend — main.js ──────────────────────────────── */
'use strict';

// ── Example RFPs ─────────────────────────────────────────────────
const EXAMPLE_RFPS = {
  banking: `We are seeking a nearshore team to lead a core banking modernization project for a major French bank. 
The engagement requires deep expertise in SAP S/4HANA migration, Java Spring Boot backend development, and PostgreSQL database optimization. 
The team must hold active SAP S/4HANA certification and demonstrate proven GDPR and PCI-DSS compliance experience from prior banking mandates.
French fluency is mandatory for daily client communication. The project spans 18 months with a team of 6-8 engineers.`,

  cyber: `We require a cybersecurity-specialized team for our German insurance group's risk management platform. 
Required skills include ISO 27001 implementation, Python-based security tooling, Azure cloud security architecture, and CISSP-level expertise.
The team must have delivered similar ISO 27001 and GDPR compliant projects in the insurance or financial sector.
English and French communication required. 12-month engagement with possibility of extension.`,

  devops: `TotalEnergies is looking for a cloud migration and DevOps transformation team. 
We need engineers proficient in Kubernetes orchestration, GCP infrastructure, Python automation, and CI/CD pipeline architecture.
The team must have GCP Professional certification and experience with ISO 27001 and SOC 2 compliant deployments in the energy sector.
English-speaking team preferred. 8-month project, fully remote with monthly on-site in Paris.`,

  crm: `Telefonica Spain requires a Salesforce CRM integration team for their customer experience platform.
Skills required: Salesforce administration and customization, Python integration development, REST API design, and Agile/Scrum methodology.
Salesforce Admin certification preferred. GDPR compliance experience essential given EU data residency requirements.
Spanish and/or English communication. 6-month initial engagement.`,
};

// ── Node color palette ────────────────────────────────────────────
const NODE_COLORS = {
  Engineer:  '#388bfd',
  Skill:     '#3fb950',
  Certification: '#bc8cff',
  Project:   '#d29922',
  Client:    '#f85149',
  ESNFirm:   '#39d0d8',
};

// ── Load example RFP ─────────────────────────────────────────────
function loadExample(key) {
  document.getElementById('rfpInput').value = EXAMPLE_RFPS[key] || '';
}

// ── Seed database ─────────────────────────────────────────────────
async function seedDatabase() {
  const btn = document.getElementById('seedBtn');
  btn.disabled = true;
  btn.textContent = '⟳ Seeding...';
  try {
    const res = await fetch('/api/v1/admin/seed', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast('✅ Database seeded successfully!', 'success');
    } else {
      showToast('❌ Seed failed: ' + (data.detail || 'Unknown error'), 'error');
    }
  } catch (e) {
    showToast('❌ Network error during seed.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '⟳ Seed Database';
  }
}

// ── Main analyze function ─────────────────────────────────────────
async function analyzeRFP() {
  const rfpText = document.getElementById('rfpInput').value.trim();
  if (!rfpText) {
    showToast('⚠️ Please enter an RFP before analyzing.', 'info');
    return;
  }

  setLoading(true);
  clearResults();

  try {
    const res = await fetch('/api/v1/rfp/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rfp_text: rfpText }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    renderResults(data);
    showToast('✅ Analysis complete!', 'success');
  } catch (e) {
    showToast(`❌ Error: ${e.message}`, 'error');
    console.error('Analysis failed:', e);
  } finally {
    setLoading(false);
  }
}

// ── Render all results ────────────────────────────────────────────
function renderResults(data) {
  document.getElementById('resultsPanel').style.display = 'flex';

  renderAgentTrace(data.agent_trace || []);
  renderRequirements(data.extracted_requirements || {}, data.rfp_summary);
  renderEngineers(data.matched_engineers || []);
  renderGaps(data.skill_gaps || []);
  renderProposal(data.proposal_text || '');
  renderGraph(data.graph_data || { nodes: [], edges: [] });
}

// ── Agent trace ───────────────────────────────────────────────────
function renderAgentTrace(steps) {
  const trace = document.getElementById('agentTrace');
  const container = document.getElementById('traceSteps');
  trace.style.display = 'block';
  container.innerHTML = '';

  const icons = {
    RFPParserAgent:          '🔍',
    TeamBuilderAgent:        '🤖',
    GapAnalystAgent:         '⚠️',
    ProposalDrafterAgent:    '📄',
    GraphVisualizationAgent: '🕸️',
  };

  steps.forEach((step, i) => {
    setTimeout(() => {
      const el = document.createElement('div');
      el.className = 'oiq-trace-step';
      el.innerHTML = `
        <div class="oiq-trace-step__icon">${icons[step.agent] || '⚙️'}</div>
        <div class="oiq-trace-step__body">
          <div class="oiq-trace-step__agent">${step.agent}</div>
          <div class="oiq-trace-step__output">${escHtml(step.output)}</div>
        </div>
      `;
      container.appendChild(el);
    }, i * 120);
  });
}

// ── Requirements ──────────────────────────────────────────────────
function renderRequirements(req, summary) {
  const el = document.getElementById('requirementsContent');
  const makeTags = (arr, cls) =>
    (arr || []).map(t => `<span class="oiq-tag ${cls}">${escHtml(t)}</span>`).join('');

  el.innerHTML = `
    <div class="oiq-req-grid">
      ${summary ? `<div class="oiq-req-row"><p style="font-size:12px;color:var(--oiq-text-muted);margin-bottom:6px;">${escHtml(summary)}</p></div>` : ''}
      <div class="oiq-req-row">
        <span class="oiq-req-label">Skills Required</span>
        <div class="oiq-tags">${makeTags(req.skills, 'oiq-tag--skill') || '<span style="color:var(--oiq-text-muted);font-size:12px;">None extracted</span>'}</div>
      </div>
      <div class="oiq-req-row">
        <span class="oiq-req-label">Compliance Frameworks</span>
        <div class="oiq-tags">${makeTags(req.compliance_frameworks, 'oiq-tag--compliance') || '<span style="color:var(--oiq-text-muted);font-size:12px;">None specified</span>'}</div>
      </div>
      <div class="oiq-req-row">
        <span class="oiq-req-label">Certifications</span>
        <div class="oiq-tags">${makeTags(req.certifications, 'oiq-tag--cert') || '<span style="color:var(--oiq-text-muted);font-size:12px;">None specified</span>'}</div>
      </div>
      <div class="oiq-req-row">
        <span class="oiq-req-label">Languages · Sector · Seniority</span>
        <div class="oiq-tags">
          ${makeTags(req.languages, 'oiq-tag--lang')}
          ${req.sector ? `<span class="oiq-tag oiq-tag--neutral">${escHtml(req.sector)}</span>` : ''}
          ${req.seniority ? `<span class="oiq-tag oiq-tag--neutral">${escHtml(req.seniority)}</span>` : ''}
        </div>
      </div>
    </div>
  `;
}

// ── Engineers ─────────────────────────────────────────────────────
function renderEngineers(engineers) {
  const grid = document.getElementById('engineersGrid');
  if (!engineers.length) {
    grid.innerHTML = '<p style="color:var(--oiq-text-muted);font-size:13px;">No matching engineers found. Try seeding the database first.</p>';
    return;
  }

  grid.className = 'oiq-engineers-grid';
  grid.innerHTML = engineers.map(eng => {
    const initials = eng.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
    const score = eng.match_score;
    const scoreClass = score >= 0.75 ? 'high' : score >= 0.5 ? 'medium' : 'low';
    const skillTags = (eng.matching_skills || []).slice(0, 4)
      .map(s => `<span class="oiq-tag oiq-tag--skill">${escHtml(s)}</span>`).join('');

    return `
      <div class="oiq-engineer-card">
        <div class="oiq-engineer-card__avatar">${initials}</div>
        <div class="oiq-engineer-card__body">
          <div class="oiq-engineer-card__name">${escHtml(eng.name)}</div>
          <div class="oiq-engineer-card__meta">
            📍 ${escHtml(eng.city)} · ${eng.years_exp}y exp · 🗣️ ${(eng.languages || []).join(', ')}
          </div>
          <div class="oiq-engineer-card__skills">${skillTags}</div>
        </div>
        <div class="oiq-engineer-card__score">
          <div class="oiq-score-ring oiq-score-ring--${scoreClass}">
            ${Math.round(score * 100)}%
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ── Skill gaps ────────────────────────────────────────────────────
function renderGaps(gaps) {
  const card = document.getElementById('gapsCard');
  const el   = document.getElementById('gapsContent');

  if (!gaps.length) {
    card.style.display = 'none';
    return;
  }

  card.style.display = 'block';
  el.innerHTML = gaps.map(g => `
    <div class="oiq-gap-item">
      <div class="oiq-gap-item__skill">⚠️ ${escHtml(g.skill)}</div>
      <div class="oiq-gap-item__suggestion">${escHtml(g.suggestion)}</div>
    </div>
  `).join('');
}

// ── Proposal ──────────────────────────────────────────────────────
function renderProposal(text) {
  document.getElementById('proposalContent').innerHTML =
    `<div class="oiq-proposal-text">${escHtml(text)}</div>`;
}

function copyProposal() {
  const text = document.querySelector('.oiq-proposal-text')?.innerText || '';
  navigator.clipboard.writeText(text).then(() => showToast('📋 Copied to clipboard!', 'success'));
}

// ── D3 Force Graph ────────────────────────────────────────────────
function renderGraph(graphData) {
  const { nodes, edges } = graphData;
  const svg = d3.select('#graphSvg');
  svg.selectAll('*').remove();

  if (!nodes.length) {
    svg.append('text')
      .attr('x', '50%').attr('y', '50%')
      .attr('text-anchor', 'middle')
      .attr('fill', '#7d8590')
      .attr('font-size', '13')
      .text('No graph data — run analysis first.');
    return;
  }

  // Build legend
  const legendEl = document.getElementById('graphLegend');
  const types = [...new Set(nodes.map(n => n.type))].filter(Boolean);
  legendEl.innerHTML = types.map(t => `
    <div class="oiq-legend-item">
      <div class="oiq-legend-dot" style="background:${NODE_COLORS[t] || '#888'}"></div>
      ${t}
    </div>
  `).join('');

  const container = document.getElementById('graphContainer');
  const W = container.clientWidth  || 600;
  const H = container.clientHeight || 340;

  // Deduplicate nodes by id
  const nodeMap = {};
  nodes.forEach(n => { if (n.id) nodeMap[n.id] = n; });
  const uniqueNodes = Object.values(nodeMap);

  // Build valid edge list (only edges where both source+target exist in nodeMap)
  const links = edges
    .filter(e => e.source && e.target && nodeMap[e.source] && nodeMap[e.target])
    .map(e => ({ source: e.source, target: e.target, label: e.label || '' }));

  const tooltip = d3.select('body').selectAll('.oiq-tooltip').data([null]).join('div')
    .attr('class', 'oiq-tooltip')
    .style('opacity', 0);

  const zoom = d3.zoom().scaleExtent([0.3, 3])
    .on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoom);

  const g = svg.append('g');

  // Arrow markers
  const defs = svg.append('defs');
  Object.entries(NODE_COLORS).forEach(([type, color]) => {
    defs.append('marker')
      .attr('id', `arrow-${type}`)
      .attr('viewBox', '0 -4 8 8')
      .attr('refX', 18).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-4L8,0L0,4')
      .attr('fill', color)
      .attr('opacity', 0.7);
  });

  const sim = d3.forceSimulation(uniqueNodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(W / 2, H / 2))
    .force('collision', d3.forceCollide(22));

  // Links
  const link = g.append('g').selectAll('line')
    .data(links).join('line')
    .attr('stroke', d => {
      const targetNode = nodeMap[typeof d.target === 'object' ? d.target.id : d.target];
      return NODE_COLORS[targetNode?.type] || '#555';
    })
    .attr('stroke-opacity', 0.5)
    .attr('stroke-width', 1.5)
    .attr('marker-end', d => {
      const targetNode = nodeMap[typeof d.target === 'object' ? d.target.id : d.target];
      return `url(#arrow-${targetNode?.type || 'Skill'})`;
    });

  // Link labels
  const linkLabel = g.append('g').selectAll('text')
    .data(links).join('text')
    .attr('font-size', 8)
    .attr('fill', '#555')
    .attr('text-anchor', 'middle')
    .text(d => d.label);

  // Nodes
  const node = g.append('g').selectAll('g')
    .data(uniqueNodes).join('g')
    .attr('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end',   (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }))
    .on('mouseover', (e, d) => {
      tooltip.style('opacity', 1)
        .html(`<strong>${escHtml(d.label || d.id)}</strong><br><span style="color:#7d8590">${d.type}</span>${d.city ? `<br>📍 ${escHtml(d.city)}` : ''}${d.exp ? `<br>${d.exp}y experience` : ''}`);
    })
    .on('mousemove', e => {
      tooltip.style('left', (e.pageX + 12) + 'px').style('top', (e.pageY - 28) + 'px');
    })
    .on('mouseout', () => tooltip.style('opacity', 0));

  node.append('circle')
    .attr('r', d => d.type === 'Engineer' ? 14 : d.type === 'Project' ? 11 : 8)
    .attr('fill', d => NODE_COLORS[d.type] || '#888')
    .attr('fill-opacity', 0.85)
    .attr('stroke', '#0d1117')
    .attr('stroke-width', 2);

  node.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', d => d.type === 'Engineer' ? 28 : 22)
    .attr('font-size', d => d.type === 'Engineer' ? 10 : 9)
    .attr('fill', '#e6edf3')
    .attr('font-weight', d => d.type === 'Engineer' ? '600' : '400')
    .text(d => {
      const label = d.label || d.id || '';
      return label.length > 16 ? label.slice(0, 15) + '…' : label;
    });

  sim.on('tick', () => {
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    linkLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });
}

// ── Utilities ─────────────────────────────────────────────────────
function setLoading(on) {
  const btn     = document.getElementById('analyzeBtn');
  const txt     = document.getElementById('analyzeBtnText');
  const spinner = document.getElementById('analyzeBtnSpinner');
  btn.disabled     = on;
  txt.style.display     = on ? 'none' : 'inline';
  spinner.style.display = on ? 'inline-block' : 'none';
}

function clearResults() {
  document.getElementById('resultsPanel').style.display  = 'none';
  document.getElementById('agentTrace').style.display    = 'none';
  document.getElementById('traceSteps').innerHTML        = '';
  document.getElementById('gapsCard').style.display      = 'none';
  d3.select('#graphSvg').selectAll('*').remove();
}

function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `oiq-toast oiq-toast--${type} oiq-toast--visible`;
  setTimeout(() => { t.classList.remove('oiq-toast--visible'); }, 3500);
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
