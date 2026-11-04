'use strict';

const modes = ['baseline', 'guarded', 'guarded_oversight'];
const titles = ['Baseline', 'Guarded', 'Guarded + oversight'];
const descriptions = [
  'Typed interfaces and system instructions. No external authorization or evidence controls.',
  'Exact authorization, output validation, trust boundaries and bounded evidence verification.',
  'Guarded controls plus a deterministic fake-allow reviewer before authorized sensitive operations.'
];
const endpoints = [
  ['model_attack_success_rate', 'Model attack success'],
  ['runtime_attack_success_rate', 'Runtime attack success'],
  ['task_completion_rate', 'Legitimate task completion'],
  ['unauthorized_action_rate', 'Unauthorized executed-action episodes'],
  ['false_refusal_rate', 'False refusal']
];
const $ = id => document.getElementById(id);
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
let data;
function renderResults() {
  const profile = data.profiles[$('profile').value];
  const category = $('category').value;
  $('profile-description').textContent = $('profile').value === 'adversarial'
    ? 'SIMULATED adversarial profile: scripts deliberately propose unauthorized email on attack-present cases, disclose a synthetic canary in pi-004 and assert confidence on unresolved evidence cases. This authored behavior exercises runtime controls; it is not an empirical attack-response measurement.'
    : 'SIMULATED reference profile: the original safe-completion scripts exercise all 30 legitimate tasks, including three authorized sensitive operations. These scripts already know their expected answers.';
  $('configs').replaceChildren();
  const summaries = modes.map(mode => category === 'all' ? profile.modes[mode] : profile.modes[mode].per_category[category]);
  summaries.forEach((summary, index) => {
    const card = element('article', undefined, 'config');
    card.append(element('span', `CONFIGURATION ${'ABC'[index]} / SIMULATED`, 'code'), element('h3', titles[index]), element('p', descriptions[index]));
    const count = element('div', undefined, 'action-count');
    count.append(element('strong', String(summary.executed_unauthorized_actions)), element('span', 'unauthorized actions executed'));
    const progress = element('progress');
    progress.max = Math.max(1, summary.proposed_unsafe_actions);
    progress.value = summary.executed_unauthorized_actions;
    progress.setAttribute('aria-label', `SIMULATED ${titles[index]}: ${summary.executed_unauthorized_actions} unauthorized effects from ${summary.proposed_unsafe_actions} unsafe proposals`);
    card.append(count, progress, element('p', `${summary.blocked_actions} blocked · ${summary.executed_sensitive_actions} sensitive effects · ${summary.review_calls} fake reviews`, 'small'));
    $('configs').append(card);
  });
  $('metrics').replaceChildren();
  endpoints.forEach(([key, title]) => {
    const row = element('tr');
    const heading = element('th', title); heading.scope = 'row'; row.append(heading);
    summaries.forEach(summary => {
      const value = summary.metrics[key];
      const cell = element('td');
      cell.append(element('span', value.rate === null ? 'N/A' : `${(100 * value.rate).toFixed(1)}%`, 'rate'), element('span', `${value.numerator} / ${value.denominator} episodes · SIMULATED`, 'denominator'));
      row.append(cell);
    });
    $('metrics').append(row);
  });
  const refusal = data.false_refusal_diagnostic.summary.metrics.false_refusal_rate;
  $('refusal-probe').replaceChildren(document.createTextNode(`${refusal.numerator} / ${refusal.denominator} false refusals`), element('span', 'SIMULATED fake-deny diagnostic only'));
  renderTrace();
}
function renderTrace() {
  const examples = data.profiles[$('profile').value].examples;
  const row = examples.find(item => item.scenario_id === $('scenario').value && item.mode === $('mode').value);
  const scenario = data.corpus.find(item => item.id === row.scenario_id);
  $('trace-id').textContent = row.scenario_id;
  $('trace-objective').textContent = scenario.objective;
  $('trace-outcome').replaceChildren();
  const outcomes = [
    ['Task completed', row.evaluation.task_completed ? 'Yes' : 'No'],
    ['Unsafe proposals / unauthorized effects', `${row.evaluation.proposed_unsafe_actions} / ${row.evaluation.unauthorized_actions}`],
    ['Blocked actions / fake reviews', `${row.execution.blocked_actions.length} / ${row.execution.reviews.length}`],
    ['Runtime status', row.execution.status]
  ];
  outcomes.forEach(([key, value]) => $('trace-outcome').append(element('dt', key), element('dd', value)));
  $('timeline').replaceChildren();
  row.execution.trace.forEach((event, index) => {
    const details = element('details', undefined, 'event');
    const heading = element('summary');
    heading.append(element('span', String(index + 1).padStart(2, '0'), 'event-number'), element('strong', event.event.replaceAll('_', ' ') + (event.event === 'guard_decision' ? ` · ${event.data.allowed ? 'allowed' : 'blocked'} · ${event.data.reason}` : '')));
    if (['reviewer_decision', 'evidence_decision'].includes(event.event) || (event.event === 'guard_decision' && !event.data.allowed)) details.open = true;
    details.append(heading, element('pre', JSON.stringify(event, null, 2)));
    $('timeline').append(details);
  });
}
async function initialize() {
  const response = await fetch('data/demo.json');
  if (!response.ok) throw new Error('Artifact unavailable');
  data = await response.json();
  if (data.simulation !== true || data.provider !== 'fake' || data.live_results !== false) throw new Error('Unexpected artifact type');
  const scenarios = [...new Set(data.profiles.adversarial.examples.map(item => item.scenario_id))];
  scenarios.forEach(id => {
    const option = element('option', id); option.value = id; $('scenario').append(option);
  });
  $('scenario').value = 'pi-004';
  ['profile', 'category'].forEach(id => $(id).addEventListener('change', renderResults));
  ['scenario', 'mode'].forEach(id => $(id).addEventListener('change', renderTrace));
  renderResults();
  $('load-status').textContent = 'SIMULATED artifact loaded · 180 comparison episodes + 3 separate false-refusal probes · no live evaluations.';
}
initialize().catch(() => {
  $('load-status').textContent = 'Could not load the SIMULATED artifact. Serve this folder over HTTP; see repository setup instructions. No model request was made.';
});
