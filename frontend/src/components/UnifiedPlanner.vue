<script setup>
import { computed, ref, onMounted } from "vue";

const activeTab = ref("scenarios");
const now = ref(new Date());
const nowText = computed(() =>
  now.value.toLocaleString(undefined, {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
);
const scenarios = ref([]);
const selectedScenarioId = ref("discrete_manufacturing");
const model = ref(null);
const planResult = ref(null);
const loading = ref(false);
const errorText = ref("");

// ── Editing state ──

/** Currently-open entity for inline editing (index into model.entities raw list) */
const editEntityRawIdx = ref(-1);
/** Currently-open rule index */
const editRuleIdx = ref(-1);
/** Currently-open order index */
const editOrderIdx = ref(-1);
/** Sub-panel within rule editing: which selector group is being added */
const addSelGroup = ref("");

onMounted(async () => {
  await loadScenarios();
  now.value = new Date();
  const timer = setInterval(() => { now.value = new Date(); }, 60_000);
  return () => clearInterval(timer);
});

async function loadScenarios() {
  try {
    const resp = await fetch("/api/unified/scenarios");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    scenarios.value = await resp.json();
    errorText.value = "";
  } catch (err) {
    errorText.value = `Failed to load scenarios: ${err.message}`;
  }
}

async function loadScenario() {
  if (!selectedScenarioId.value) return;
  loading.value = true;
  errorText.value = "";
  try {
    const resp = await fetch(`/api/unified/scenarios/${selectedScenarioId.value}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    model.value = await resp.json();
    activeTab.value = "model";
  } catch (err) {
    errorText.value = `Failed to load scenario: ${err.message}`;
  } finally {
    loading.value = false;
  }
}

async function runPlan() {
  if (!model.value) return;
  loading.value = true;
  errorText.value = "";
  planResult.value = null;
  try {
    const resp = await fetch("/api/unified/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(model.value),
    });
    if (!resp.ok) {
      const data = await resp.json();
      throw new Error(data.detail || `HTTP ${resp.status}`);
    }
    planResult.value = await resp.json();
    activeTab.value = "results";
  } catch (err) {
    errorText.value = `Plan failed: ${err.message}`;
  } finally {
    loading.value = false;
  }
}

// ═══════════════════════════════════════════════════════════════════════
//  ENTITIES
// ═══════════════════════════════════════════════════════════════════════

/** Group entities by identical fields, merging counts. */
const groupedEntities = computed(() => {
  if (!model.value?.entities) return [];
  const groups = [];
  const seen = new Map();
  for (const e of model.value.entities) {
    const key = JSON.stringify(e.fields || {});
    if (seen.has(key)) {
      groups[seen.get(key)].count += e.count || 1;
    } else {
      seen.set(key, groups.length);
      groups.push({ fields: { ...(e.fields || {}) }, count: e.count || 1, _key: key, rawIdx: seen.get(key) ?? groups.length });
    }
  }
  // Map rawIdx to the first raw index for each group
  const rawIdxMap = new Map();
  for (let i = 0; i < (model.value?.entities || []).length; i++) {
    const key = JSON.stringify(model.value.entities[i].fields || {});
    if (!rawIdxMap.has(key)) rawIdxMap.set(key, i);
  }
  for (const g of groups) {
    g.rawIdx = rawIdxMap.get(g._key) ?? 0;
  }
  return groups;
});

const entityTotalCount = computed(() => {
  let total = 0;
  for (const g of groupedEntities.value) total += g.count;
  return total;
});

function addEntity() {
  model.value.entities.push({ fields: { type: "new_entity" }, count: 1 });
  editEntityRawIdx.value = model.value.entities.length - 1;
}

function removeRawEntity(idx) {
  model.value.entities.splice(idx, 1);
  if (editEntityRawIdx.value === idx) editEntityRawIdx.value = -1;
}

function bumpEntityCount(idx, delta) {
  const e = model.value.entities[idx];
  const newCount = (e.count || 1) + delta;
  if (newCount < 1) { removeRawEntity(idx); return; }
  e.count = newCount;
}

function openEntityEdit(gIdx) {
  const grp = groupedEntities.value[gIdx];
  if (!grp) return;
  editEntityRawIdx.value = grp.rawIdx;
}

function closeEntityEdit() {
  editEntityRawIdx.value = -1;
}

function updateEntityField(rawIdx, oldKey, newKey, newVal) {
  const e = model.value.entities[rawIdx];
  if (!e) return;
  if (newKey !== oldKey) delete e.fields[oldKey];
  e.fields[newKey] = newVal;
  // If editing a grouped entity with count > 1, split it off
  if (e.count > 1) {
    e.count -= 1;
    model.value.entities.push({ fields: { ...e.fields }, count: 1 });
    editEntityRawIdx.value = model.value.entities.length - 1;
  }
}

function addEntityField(rawIdx) {
  const e = model.value.entities[rawIdx];
  if (!e) return;
  const key = `field_${Object.keys(e.fields).length}`;
  e.fields[key] = "";
}

function removeEntityField(rawIdx, key) {
  const e = model.value.entities[rawIdx];
  if (!e) return;
  delete e.fields[key];
}

function _findRawIndex(grp) {
  return model.value.entities.findIndex(e => JSON.stringify(e.fields || {}) === grp._key);
}

function bumpEntityCountByGroup(gIdx, delta) {
  const grp = groupedEntities.value[gIdx];
  if (!grp) return;
  const rawIdx = _findRawIndex(grp);
  if (rawIdx === -1) return;
  bumpEntityCount(rawIdx, delta);
}

function removeEntityGroup(gIdx) {
  const grp = groupedEntities.value[gIdx];
  if (!grp) return;
  const rawIdx = _findRawIndex(grp);
  if (rawIdx === -1) return;
  removeRawEntity(rawIdx);
}

// ═══════════════════════════════════════════════════════════════════════
//  RULES
// ═══════════════════════════════════════════════════════════════════════

function addRule() {
  const n = (model.value.rules || []).length + 1;
  model.value.rules.push({
    rule_id: `RULE-${n}`,
    batch_min: 1,
    batch_max: 10,
    consume: {},
    consume_batch: {},
    produce: {},
    produce_batch: {},
    duration_s: 60,
    duration_batch_s: 0,
  });
  editRuleIdx.value = model.value.rules.length - 1;
}

function removeRule(idx) {
  model.value.rules.splice(idx, 1);
  if (editRuleIdx.value === idx) editRuleIdx.value = -1;
}

function addSelectorStart(rIdx, group) {
  addSelGroup.value = `${rIdx}:${group}`;
}

function addSelectorCommit(rIdx, group) {
  const name = document.getElementById(`sel-name-${rIdx}-${group}`)?.value;
  const type = document.getElementById(`sel-type-${rIdx}-${group}`)?.value;
  const num = parseFloat(document.getElementById(`sel-num-${rIdx}-${group}`)?.value || "1");
  if (!name || !type) return;
  model.value.rules[rIdx][group][name] = { conditions: { type }, num };
  addSelGroup.value = "";
}

function removeSelectorFromRule(rIdx, group, name) {
  delete model.value.rules[rIdx][group][name];
}

function updateRuleField(rIdx, field, value) {
  model.value.rules[rIdx][field] = value;
}

// ═══════════════════════════════════════════════════════════════════════
//  ORDERS
// ═══════════════════════════════════════════════════════════════════════

function addOrder() {
  const n = (model.value.orders || []).length + 1;
  model.value.orders.push({
    order_id: `ORD-${n}`,
    consume: {},
    deadline: null,
    release_at: null,
    early_delivery_bonus_per_s: 0,
    late_delivery_penalty_per_s: 0,
  });
  editOrderIdx.value = model.value.orders.length - 1;
}

function removeOrder(idx) {
  model.value.orders.splice(idx, 1);
  if (editOrderIdx.value === idx) editOrderIdx.value = -1;
}

function addOrderSelectorStart(oIdx) {
  addSelGroup.value = `order:${oIdx}`;
}

function addOrderSelectorCommit(oIdx) {
  const name = document.getElementById(`osel-name-${oIdx}`)?.value;
  const type = document.getElementById(`osel-type-${oIdx}`)?.value;
  const num = parseFloat(document.getElementById(`osel-num-${oIdx}`)?.value || "1");
  if (!name || !type) return;
  model.value.orders[oIdx].consume[name] = { conditions: { type }, num };
  addSelGroup.value = "";
}

function removeSelectorFromOrder(oIdx, name) {
  delete model.value.orders[oIdx].consume[name];
}

function updateOrderField(oIdx, field, value) {
  model.value.orders[oIdx][field] = value;
}

// ═══════════════════════════════════════════════════════════════════════
//  GANTT CHART
// ═══════════════════════════════════════════════════════════════════════

const ganttData = computed(() => {
  const blocks = planResult.value?.scheduled_blocks;
  if (!blocks || !blocks.length) return null;
  const equipmentRows = {};
  for (const b of blocks) {
    const eq = b.equipment_entity_id;
    if (!equipmentRows[eq]) equipmentRows[eq] = [];
    equipmentRows[eq].push(b);
  }
  const equipmentList = Object.keys(equipmentRows).sort();
  const maxTick = Math.max(...blocks.map(b => b.end_tick), 1);
  const minTick = Math.min(...blocks.map(b => b.start_tick), 0);
  const ruleColors = {};
  const palette = ["#5b8def", "#34d399", "#f59e0b", "#ef4444", "#a78bfa", "#ec4899", "#14b8a6", "#f97316", "#84cc16", "#06b6d4"];
  let colorIdx = 0;
  for (const b of blocks) {
    if (!ruleColors[b.rule_id]) ruleColors[b.rule_id] = palette[colorIdx++ % palette.length];
  }
  return {
    equipmentList, maxTick, minTick, ruleColors,
    rows: equipmentList.map(eq => ({ equipmentId: eq, blocks: (equipmentRows[eq] || []).sort((a, b) => a.start_tick - b.start_tick) })),
    totalBlocks: blocks.length,
  };
});

const ganttChartWidth = computed(() => {
  if (!ganttData.value) return 600;
  return Math.max(800, Math.min(2000, (ganttData.value.maxTick - ganttData.value.minTick) * 15));
});
const ganttChartHeight = computed(() => {
  if (!ganttData.value) return 200;
  return 40 + ganttData.value.equipmentList.length * 40;
});
function ganttBarX(block) {
  if (!ganttData.value) return 0;
  const range = ganttData.value.maxTick - ganttData.value.minTick || 1;
  return ((block.start_tick - ganttData.value.minTick) / range) * ganttChartWidth.value;
}
function ganttBarWidth(block) {
  if (!ganttData.value) return 0;
  const range = ganttData.value.maxTick - ganttData.value.minTick || 1;
  return ((block.end_tick - block.start_tick) / range) * ganttChartWidth.value;
}
function ganttEquipmentY(index) { return 40 + index * 40 + 5; }
function formatTick(tick) {
  if (tick >= 1440) return `${Math.round(tick / 1440)}d`;
  if (tick >= 60) return `${Math.round(tick / 60)}h`;
  return `${tick}m`;
}
const ganttXTicks = computed(() => {
  if (!ganttData.value) return [];
  const max = ganttData.value.maxTick;
  const step = Math.max(1, Math.round(max / 10));
  return Array.from({ length: Math.floor(max / step) + 1 }, (_, i) => i * step);
});

// ═══════════════════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════════════════

function selectorKeys(s) { return Object.keys(s || {}); }
function selectorRowSummary(s) {
  return Object.entries(s || {}).map(([k, v]) => `${k} → ${v.conditions?.type || "?"} ×${v.num}`).join(", ") || "none";
}
</script>

<template>
  <div class="unified-planner">
    <header class="unified-header">
      <div class="title-block">
        <h2>Unified APS Planner</h2>
        <span class="pro-badge">PRO</span>
      </div>
      <div class="unified-tabs">
        <button type="button" :class="{ active: activeTab === 'scenarios' }" @click="activeTab = 'scenarios'">Scenarios</button>
        <button type="button" :class="{ active: activeTab === 'model' }" :disabled="!model" @click="activeTab = 'model'">Model</button>
        <button type="button" :class="{ active: activeTab === 'results' }" :disabled="!planResult" @click="activeTab = 'results'">Results</button>
      </div>
    </header>

    <div v-if="errorText" class="error-banner">{{ errorText }}</div>

    <!-- ═══════════════════════════════════════════════════════════════════════
         SCENARIO SELECTION
         ═══════════════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'scenarios'" class="unified-section">
      <div class="scenario-section-header">
        <h3>Select Scenario</h3>
        <div class="user-greeting">Hello user, it’s {{ nowText }}</div>
      </div>
      <div class="scenario-grid">
        <div
          v-for="s in scenarios"
          :key="s.scenario_id"
          class="scenario-card"
          :class="{ selected: selectedScenarioId === s.scenario_id }"
          @click="selectedScenarioId = s.scenario_id"
        >
          <h4>{{ s.name }}</h4>
          <p>{{ s.description }}</p>
        </div>
      </div>
      <button type="button" class="btn-primary" :disabled="loading" @click="loadScenario">
        {{ loading ? "Loading…" : "Load Scenario" }}
      </button>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════════════
         MODEL EDITOR
         ═══════════════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'model' && model" class="unified-section">
      <div class="model-header">
        <h3>Planning Model</h3>
        <div class="model-summary">
          <span class="chips">{{ entityTotalCount }} entities</span>
          <span class="chips">{{ (model.rules || []).length }} rules</span>
          <span class="chips">{{ (model.orders || []).length }} orders</span>
          <span class="chips">{{ model.planning_horizon_s }}s horizon</span>
        </div>
      </div>

      <!-- Meta section -->
      <div class="model-meta">
        <div class="meta-row">
          <span class="meta-label">Objective:</span>
          <code>{{ model.objective?.expression || "none" }}</code>
          <span class="meta-label">Planning start:</span>
          <code>{{ model.planning_start ? new Date(model.planning_start).toLocaleString() : "—" }}</code>
          <span class="meta-label">Horizon:</span>
          <code>{{ model.planning_horizon_s }}s ({{ Math.round(model.planning_horizon_s / 86400) }}d)</code>
        </div>
        <div class="meta-row" v-if="model.holding_rules?.length">
          <span class="meta-label">Holding rules:</span>
          <code>{{ model.holding_rules.length }} defined</code>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════════
           ENTITIES
           ═══════════════════════════════════════════════════════════════════════ -->
      <details open class="section-details">
        <summary>
          <span class="summary-title">Entities</span>
          <span class="summary-badge">{{ entityTotalCount }}</span>
          <span class="summary-extra">{{ groupedEntities.map(g => `${g.fields.type || "?"}×${g.count}`).join(", ") }}</span>
        </summary>
        <div class="section-toolbar">
          <button type="button" class="btn-sm" @click="addEntity">+ Add Entity</button>
        </div>
        <div class="entity-list">
          <!-- Grouped entity cards -->
          <div
            v-for="(grp, gIdx) in groupedEntities"
            :key="gIdx"
            class="entity-card"
            :class="{ editing: editEntityRawIdx === grp.rawIdx }"
          >
            <div class="card-head">
              <span class="type-tag">{{ grp.fields.type || "unknown" }}</span>
              <span class="count-badge">{{ grp.count }}</span>
              <button type="button" class="btn-xs" @click.stop="bumpEntityCountByGroup(gIdx, -1)">−</button>
              <button type="button" class="btn-xs" @click.stop="bumpEntityCountByGroup(gIdx, 1)">+</button>
              <button type="button" class="btn-xs ghost" @click.stop="openEntityEdit(gIdx)">✎</button>
              <button type="button" class="btn-xs danger" @click.stop="removeEntityGroup(gIdx)">✕</button>
            </div>
            <div v-if="editEntityRawIdx !== grp.rawIdx" class="card-body">
              <div v-for="(val, key) in grp.fields" :key="key" class="field-row">
                <span class="field-key">{{ key }}</span>
                <span class="field-val">{{ val }}</span>
              </div>
            </div>
            <!-- Inline entity editor -->
            <div v-else class="card-body edit-body">
              <div class="field-row" v-for="(val, key) in grp.fields" :key="key">
                <input
                  class="inline-input key-input"
                  :value="key"
                  @input="e => { const old = key; const v = e.target.value; if (v !== old) { updateEntityField(grp.rawIdx, old, v, model.value.entities[grp.rawIdx].fields[old]); } }"
                  placeholder="key"
                />
                <span class="field-sep">=</span>
                <input
                  class="inline-input val-input"
                  :value="val"
                  @input="e => updateEntityField(grp.rawIdx, key, key, e.target.value)"
                  placeholder="value"
                />
                <button type="button" class="btn-xs" @click.stop="removeEntityField(grp.rawIdx, key)">✕</button>
              </div>
              <div class="edit-actions">
                <button type="button" class="btn-xs" @click.stop="addEntityField(grp.rawIdx)">+ field</button>
                <button type="button" class="btn-xs" @click.stop="closeEntityEdit">done</button>
              </div>
            </div>
          </div>
          <!-- Dashed add placeholder -->
          <div class="add-entity-placeholder">
            <button type="button" class="btn-sm" @click="addEntity">+ Add Entity</button>
          </div>
        </div>
      </details>

      <!-- ═══════════════════════════════════════════════════════════════════════
           RULES
           ═══════════════════════════════════════════════════════════════════════ -->
      <details open class="section-details">
        <summary>
          <span class="summary-title">Rules</span>
          <span class="summary-badge">{{ (model.rules || []).length }}</span>
        </summary>
        <div class="section-toolbar">
          <button type="button" class="btn-sm" @click="addRule">+ Add Rule</button>
        </div>
        <div class="rule-list">
          <div
            v-for="(r, idx) in model.rules"
            :key="idx"
            class="rule-card"
            :class="{ editing: editRuleIdx === idx }"
          >
            <div class="card-head" :class="{ active: editRuleIdx === idx }" @click="editRuleIdx = editRuleIdx === idx ? -1 : idx">
              <span class="rule-id">{{ r.rule_id }}</span>
              <input
                v-if="editRuleIdx === idx"
                class="inline-input rule-id-input"
                :value="r.rule_id"
                @input="e => updateRuleField(idx, 'rule_id', e.target.value)"
                @click.stop
                placeholder="rule_id"
              />
              <span class="card-idx">#{{ idx + 1 }}</span>
              <button type="button" class="btn-xs danger" @click.stop="removeRule(idx)">✕</button>
            </div>
            <div v-if="editRuleIdx === idx" class="card-body">
              <!-- Batch & duration controls -->
              <div class="rule-meta-controls">
                <label>batch
                  <input class="inline-input num-input" :value="r.batch_min" @input="e => updateRuleField(idx, 'batch_min', parseInt(e.target.value) || 1)" />
                  –
                  <input class="inline-input num-input" :value="r.batch_max" @input="e => updateRuleField(idx, 'batch_max', parseInt(e.target.value) || 1)" />
                </label>
                <label>duration
                  <input class="inline-input num-input" :value="r.duration_s" @input="e => updateRuleField(idx, 'duration_s', parseFloat(e.target.value) || 0)" /> s/unit
                </label>
                <label>setup
                  <input class="inline-input num-input" :value="r.duration_batch_s" @input="e => updateRuleField(idx, 'duration_batch_s', parseFloat(e.target.value) || 0)" /> s/run
                </label>
              </div>

              <!-- Selector groups -->
              <div v-for="group in ['consume', 'consume_batch', 'produce', 'produce_batch']" :key="group" class="rule-dim">
                <div class="dim-label-row">
                  <span class="dim-label">{{ group }} {{ group.includes('batch') ? '(× 1/run)' : '(× batch qty)' }}</span>
                  <button type="button" class="btn-xs" @click.stop="addSelectorStart(idx, group)">+</button>
                </div>
                <div v-for="(sel, sname) in r[group]" :key="sname" class="sel-edit-row">
                  <input class="inline-input name-input" :value="sname" disabled />
                  <span class="field-sep">→</span>
                  <input class="inline-input type-input" :value="sel.conditions?.type || ''"
                    @input="e => { const v = e.target.value; model.value.rules[idx][group][sname].conditions.type = v; }"
                  />
                  <span class="field-sep">×</span>
                  <input class="inline-input num-input" :value="sel.num"
                    @input="e => { const v = parseFloat(e.target.value) || 1; model.value.rules[idx][group][sname].num = v; }"
                  />
                  <button type="button" class="btn-xs" @click.stop="removeSelectorFromRule(idx, group, sname)">✕</button>
                </div>
                <!-- Add-selector form -->
                <div v-if="addSelGroup === `${idx}:${group}`" class="sel-add-form" @click.stop>
                  <input :id="`sel-name-${idx}-${group}`" class="inline-input name-input" placeholder="name" @keydown.enter="addSelectorCommit(idx, group)" />
                  <span class="field-sep">→</span>
                  <input :id="`sel-type-${idx}-${group}`" class="inline-input type-input" placeholder="type" @keydown.enter="addSelectorCommit(idx, group)" />
                  <span class="field-sep">×</span>
                  <input :id="`sel-num-${idx}-${group}`" class="inline-input num-input" placeholder="1" value="1" @keydown.enter="addSelectorCommit(idx, group)" />
                  <button type="button" class="btn-xs" @click="addSelectorCommit(idx, group)">add</button>
                  <button type="button" class="btn-xs" @click="addSelGroup = ''">cancel</button>
                </div>
                <div v-if="!selectorKeys(r[group]).length && addSelGroup !== `${idx}:${group}`" class="dim-empty">none</div>
              </div>
            </div>
            <!-- Collapsed read-only view -->
            <div v-else class="card-body compact">
              <div class="rule-dim">
                <div class="dim-label">consume</div>
                <span class="dim-val">{{ selectorRowSummary(r.consume) }}</span>
              </div>
              <div class="rule-dim">
                <div class="dim-label">consume_batch</div>
                <span class="dim-val">{{ selectorRowSummary(r.consume_batch) }}</span>
              </div>
              <div class="rule-dim">
                <div class="dim-label">produce</div>
                <span class="dim-val">{{ selectorRowSummary(r.produce) }}</span>
              </div>
              <div class="rule-dim">
                <div class="dim-label">produce_batch</div>
                <span class="dim-val">{{ selectorRowSummary(r.produce_batch) }}</span>
              </div>
              <div class="rule-meta-compact">
                batch {{ r.batch_min }}–{{ r.batch_max }} · {{ r.duration_s }}s/unit + {{ r.duration_batch_s }}s/run
              </div>
            </div>
          </div>
        </div>
      </details>

      <!-- ═══════════════════════════════════════════════════════════════════════
           ORDERS
           ═══════════════════════════════════════════════════════════════════════ -->
      <details open class="section-details">
        <summary>
          <span class="summary-title">Orders</span>
          <span class="summary-badge">{{ (model.orders || []).length }}</span>
        </summary>
        <div class="section-toolbar">
          <button type="button" class="btn-sm" @click="addOrder">+ Add Order</button>
        </div>
        <div class="order-list">
          <div
            v-for="(o, idx) in model.orders"
            :key="idx"
            class="order-card"
            :class="{ editing: editOrderIdx === idx }"
          >
            <div class="card-head" :class="{ active: editOrderIdx === idx }" @click="editOrderIdx = editOrderIdx === idx ? -1 : idx">
              <span class="order-id">{{ o.order_id }}</span>
              <input
                v-if="editOrderIdx === idx"
                class="inline-input rule-id-input"
                :value="o.order_id"
                @input="e => updateOrderField(idx, 'order_id', e.target.value)"
                @click.stop
                placeholder="order_id"
              />
              <span class="card-idx">#{{ idx + 1 }}</span>
              <button type="button" class="btn-xs danger" @click.stop="removeOrder(idx)">✕</button>
            </div>
            <div v-if="editOrderIdx === idx" class="card-body">
              <div class="order-meta-controls">
                <label>deadline
                  <input class="inline-input" :value="o.deadline ? o.deadline.slice(0, 16) : ''"
                    type="datetime-local"
                    @input="e => updateOrderField(idx, 'deadline', e.target.value ? new Date(e.target.value).toISOString() : null)"
                  />
                </label>
                <label>release
                  <input class="inline-input" :value="o.release_at ? o.release_at.slice(0, 16) : ''"
                    type="datetime-local"
                    @input="e => updateOrderField(idx, 'release_at', e.target.value ? new Date(e.target.value).toISOString() : null)"
                  />
                </label>
                <label>early bonus
                  <input class="inline-input num-input" :value="o.early_delivery_bonus_per_s"
                    @input="e => updateOrderField(idx, 'early_delivery_bonus_per_s', parseFloat(e.target.value) || 0)"
                  /> /s
                </label>
                <label>late penalty
                  <input class="inline-input num-input" :value="o.late_delivery_penalty_per_s"
                    @input="e => updateOrderField(idx, 'late_delivery_penalty_per_s', parseFloat(e.target.value) || 0)"
                  /> /s
                </label>
              </div>
              <div class="rule-dim">
                <div class="dim-label-row">
                  <span class="dim-label">Consume</span>
                  <button type="button" class="btn-xs" @click.stop="addOrderSelectorStart(idx)">+</button>
                </div>
                <div v-for="(sel, sname) in o.consume" :key="sname" class="sel-edit-row">
                  <input class="inline-input name-input" :value="sname" disabled />
                  <span class="field-sep">→</span>
                  <input class="inline-input type-input" :value="sel.conditions?.type || ''"
                    @input="e => { const v = e.target.value; model.value.orders[idx].consume[sname].conditions.type = v; }"
                  />
                  <span class="field-sep">×</span>
                  <input class="inline-input num-input" :value="sel.num"
                    @input="e => { const v = parseFloat(e.target.value) || 1; model.value.orders[idx].consume[sname].num = v; }"
                  />
                  <button type="button" class="btn-xs" @click.stop="removeSelectorFromOrder(idx, sname)">✕</button>
                </div>
                <div v-if="addSelGroup === `order:${idx}`" class="sel-add-form" @click.stop>
                  <input :id="`osel-name-${idx}`" class="inline-input name-input" placeholder="name" @keydown.enter="addOrderSelectorCommit(idx)" />
                  <span class="field-sep">→</span>
                  <input :id="`osel-type-${idx}`" class="inline-input type-input" placeholder="type" @keydown.enter="addOrderSelectorCommit(idx)" />
                  <span class="field-sep">×</span>
                  <input :id="`osel-num-${idx}`" class="inline-input num-input" placeholder="1" value="1" @keydown.enter="addOrderSelectorCommit(idx)" />
                  <button type="button" class="btn-xs" @click="addOrderSelectorCommit(idx)">add</button>
                  <button type="button" class="btn-xs" @click="addSelGroup = ''">cancel</button>
                </div>
                <div v-if="!selectorKeys(o.consume).length && addSelGroup !== `order:${idx}`" class="dim-empty">none</div>
              </div>
            </div>
            <div v-else class="card-body compact">
              <div class="order-meta-compact">
                deadline: <code>{{ o.deadline ? new Date(o.deadline).toLocaleDateString() : "none" }}</code> ·
                release: <code>{{ o.release_at ? new Date(o.release_at).toLocaleDateString() : "immediate" }}</code>
              </div>
              <div class="rule-dim">
                <span class="dim-val">{{ selectorRowSummary(o.consume) }}</span>
              </div>
            </div>
          </div>
        </div>
      </details>

      <div class="action-bar">
        <button type="button" class="btn-primary" :disabled="loading" @click="runPlan">
          {{ loading ? "Planning…" : "Run Plan" }}
        </button>
      </div>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════════════
         PLAN RESULTS
         ═══════════════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'results' && planResult" class="unified-section">
      <h3>Plan Results</h3>
      <div class="result-header">
        <div class="result-stat">
          <span class="result-stat-label">Status</span>
          <span class="result-stat-value" :class="planResult.status === 'feasible' ? 'color-ok' : ''">{{ planResult.status }}</span>
        </div>
        <div class="result-stat">
          <span class="result-stat-label">Makespan</span>
          <span class="result-stat-value">{{ planResult.makespan_s }}s</span>
        </div>
        <div class="result-stat">
          <span class="result-stat-label">Blocks</span>
          <span class="result-stat-value">{{ (planResult.scheduled_blocks || []).length }}</span>
        </div>
        <div class="result-stat">
          <span class="result-stat-label">Solver time</span>
          <span class="result-stat-value">{{ planResult.solver_time_s.toFixed(4) }}s</span>
        </div>
      </div>

      <details open class="section-details">
        <summary>
          <span class="summary-title">Order Outcomes</span>
          <span class="summary-badge">{{ (planResult.order_outcomes || []).length }}</span>
        </summary>
        <table class="result-table">
          <thead><tr><th>Order ID</th><th>Fulfilled</th><th>Completion</th><th>Lateness</th></tr></thead>
          <tbody>
            <tr v-for="o in planResult.order_outcomes" :key="o.order_id">
              <td class="cell-id">{{ o.order_id }}</td>
              <td :class="o.fulfilled ? 'cell-ok' : 'cell-fail'">{{ o.fulfilled ? "Yes" : "No" }}</td>
              <td>{{ o.completion_tick ?? "N/A" }}</td>
              <td :class="o.lateness_ticks > 0 ? 'cell-fail' : ''">{{ o.lateness_ticks }}</td>
            </tr>
          </tbody>
        </table>
      </details>

      <details open class="section-details">
        <summary>
          <span class="summary-title">Scheduled Blocks</span>
          <span class="summary-badge">{{ (planResult.scheduled_blocks || []).length }}</span>
        </summary>
        <table class="result-table">
          <thead><tr><th>Rule</th><th>Start</th><th>End</th><th>Qty</th><th>Equipment</th><th>Consumed</th><th>Produced</th></tr></thead>
          <tbody>
            <tr v-for="b in planResult.scheduled_blocks" :key="`${b.rule_id}-${b.start_tick}`">
              <td class="cell-id">{{ b.rule_id }}</td>
              <td>{{ b.start_tick }}</td>
              <td>{{ b.end_tick }}</td>
              <td>{{ b.batch_qty }}</td>
              <td>{{ b.equipment_entity_id }}</td>
              <td class="cell-detail">{{ b.consumed?.map(c => `${c.entity_type}×${c.num}`).join(", ") }}</td>
              <td class="cell-detail">{{ b.produced?.map(c => `${c.entity_type}×${c.num}`).join(", ") }}</td>
            </tr>
          </tbody>
        </table>
      </details>

      <details open class="section-details" v-if="ganttData">
        <summary>
          <span class="summary-title">Gantt Chart</span>
          <span class="summary-badge">{{ ganttData.totalBlocks }} blocks</span>
          <span class="summary-extra">{{ ganttData.equipmentList.length }} equipment</span>
        </summary>
        <div class="gantt-container">
          <svg :width="ganttChartWidth + 160" :height="ganttChartHeight" class="gantt-svg">
            <text v-for="(eq, idx) in ganttData.equipmentList" :key="'label-'+eq" :x="155" :y="ganttEquipmentY(idx)+14" text-anchor="end" class="gantt-label">{{ eq }}</text>
            <line v-for="t in ganttXTicks" :key="'grid-'+t" :x1="ganttBarX({start_tick: t, end_tick: t})+160" :y1="30" :x2="ganttBarX({start_tick: t, end_tick: t})+160" :y2="ganttChartHeight" stroke="#2a2e3a" stroke-width="1" stroke-dasharray="4,4"/>
            <text v-for="t in ganttXTicks" :key="'tick-'+t" :x="ganttBarX({start_tick: t, end_tick: t})+160" :y="22" text-anchor="middle" class="gantt-tick">{{ formatTick(t) }}</text>
            <rect v-for="(eq, idx) in ganttData.equipmentList" :key="'bg-'+eq" :x="160" :y="ganttEquipmentY(idx)-5" :width="ganttChartWidth" height="30" :fill="idx % 2 === 0 ? '#0f172a' : '#1a2332'" rx="3"/>
            <g v-for="(row, rowIdx) in ganttData.rows" :key="'row-'+row.equipmentId">
              <rect v-for="block in row.blocks" :key="block.rule_id+'-'+block.start_tick" :x="ganttBarX(block)+160" :y="ganttEquipmentY(rowIdx)" :width="Math.max(ganttBarWidth(block), 3)" height="20" :fill="ganttData.ruleColors[block.rule_id]" rx="4" class="gantt-bar">
                <title>{{ block.rule_id }}: qty={{ block.batch_qty }}, {{ block.start_tick }}→{{ block.end_tick }} ({{ formatTick(block.end_tick - block.start_tick) }})</title>
              </rect>
            </g>
          </svg>
        </div>
      </details>

      <div class="action-bar">
        <button type="button" class="btn-secondary" @click="activeTab = 'model'">Back to Model</button>
        <button type="button" class="btn-secondary" @click="activeTab = 'scenarios'">Change Scenario</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.unified-planner {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
  color: #e2e8f0;
}

/* ── Header ── */
.unified-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}
.unified-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}
.title-block {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.pro-badge {
  background: linear-gradient(135deg, #f59e0b, #ef4444);
  color: #fff;
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.35);
}
.unified-tabs {
  display: flex;
  gap: 0.25rem;
  background: #1e293b;
  padding: 3px;
  border-radius: 10px;
}
.unified-tabs button {
  padding: 0.5rem 1.2rem;
  border: none;
  background: transparent;
  color: #94a3b8;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.15s;
}
.unified-tabs button.active {
  background: #334155;
  color: #f1f5f9;
}
.unified-tabs button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.unified-section {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 14px;
  padding: 1.5rem;
}
.unified-section h3 {
  margin: 0 0 1rem;
  font-size: 1.2rem;
  font-weight: 600;
  color: #f1f5f9;
}
.scenario-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.scenario-section-header h3 {
  margin: 0;
}
.user-greeting {
  font-size: 0.95rem;
  color: #f87171;
  font-weight: 600;
}

.error-banner {
  background: #7f1d1d;
  color: #fca5a5;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

/* ── Scenario Grid ── */
.scenario-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.scenario-card {
  background: #0f172a;
  border: 2px solid #334155;
  border-radius: 12px;
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.15s;
}
.scenario-card:hover {
  border-color: #475569;
  transform: translateY(-1px);
}
.scenario-card.selected {
  border-color: #3b82f6;
  background: #1e3a5f;
}
.scenario-card h4 { margin: 0 0 0.5rem; font-size: 1rem; color: #f1f5f9; }
.scenario-card p { margin: 0; font-size: 0.85rem; color: #64748b; }

/* ── Model ── */
.model-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.model-header h3 { margin: 0; }
.model-summary { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.chips {
  background: #334155;
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #94a3b8;
  font-family: monospace;
}
.model-meta {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}
.model-meta .meta-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}
.model-meta code {
  background: #1e293b;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #7dd3fc;
}

/* ── Section Details ── */
.section-details {
  margin-bottom: 0.75rem;
  border: 1px solid #334155;
  border-radius: 10px;
  overflow: hidden;
}
.section-details summary {
  cursor: pointer;
  padding: 0.65rem 1rem;
  background: #0f172a;
  font-weight: 600;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  user-select: none;
}
.section-details summary:hover { background: #1a2332; }
.summary-badge {
  background: #334155;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #94a3b8;
}
.summary-extra {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 400;
  margin-left: 0.5rem;
}
.section-toolbar {
  padding: 0.5rem 1rem;
  background: #0f172a;
  border-bottom: 1px solid #334155;
}

/* ── Inline Inputs ── */
.inline-input {
  background: transparent;
  border: 1px solid transparent;
  border-bottom-color: #475569;
  color: #e2e8f0;
  font-family: monospace;
  font-size: 0.8rem;
  padding: 0.1rem 0.3rem;
  outline: none;
  transition: border-color 0.12s;
}
.inline-input:focus {
  border-bottom-color: #3b82f6;
  background: #1e293b;
}
.inline-input:disabled {
  opacity: 0.6;
  border-bottom-color: transparent;
}
.key-input { min-width: 80px; color: #7dd3fc; }
.val-input { min-width: 100px; color: #cbd5e1; }
.name-input { min-width: 70px; color: #67e8f9; }
.type-input { min-width: 90px; color: #94a3b8; }
.num-input { min-width: 50px; text-align: right; color: #f1f5f9; }
.rule-id-input { min-width: 120px; font-weight: 600; }
.field-sep { color: #475569; font-family: monospace; font-size: 0.85rem; }

/* ── Entity Cards ── */
.entity-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.5rem;
  padding: 0.75rem;
}
.entity-card {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  transition: all 0.12s;
}
.entity-card:hover { border-color: #475569; }
.entity-card.editing { border-color: #3b82f6; box-shadow: 0 0 0 1px #3b82f6; }

.card-head {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid #1e293b;
}
.card-head.active {
  background: #1a2332;
}
.card-idx {
  font-size: 0.7rem;
  color: #475569;
  font-family: monospace;
  margin-right: auto;
}
.type-tag {
  background: #1e3a5f;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-family: monospace;
  color: #93c5fd;
}
.count-badge {
  background: #2563eb;
  color: #fff;
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  font-family: monospace;
  margin-right: auto;
}
.add-entity-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80px;
  border: 2px dashed #334155;
  border-radius: 8px;
  background: transparent;
}
.add-entity-placeholder:hover { border-color: #475569; }

.card-body { padding: 0.5rem 0.6rem; }
.card-body.compact { padding: 0.4rem 0.6rem; }
.edit-body { background: #1a2332; }

.field-row {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8rem;
  padding: 0.15rem 0;
  font-family: monospace;
}
.field-row .field-key { color: #7dd3fc; min-width: 5em; }
.field-row .field-val { color: #cbd5e1; }

.edit-actions {
  display: flex;
  gap: 0.3rem;
  padding-top: 0.3rem;
  margin-top: 0.3rem;
  border-top: 1px solid #334155;
}

/* ── Rule Cards ── */
.rule-list { display: grid; gap: 0.5rem; padding: 0.75rem; }
.rule-card {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  transition: all 0.12s;
}
.rule-card:hover { border-color: #475569; }
.rule-card.editing { border-color: #3b82f6; box-shadow: 0 0 0 1px #3b82f6; }
.rule-id { color: #fbbf24; font-weight: 600; font-size: 0.85rem; font-family: monospace; }

.rule-meta-controls {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.6rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #1e293b;
  font-size: 0.8rem;
  color: #94a3b8;
}
.rule-meta-controls label { display: flex; align-items: center; gap: 0.3rem; }
.rule-meta-compact {
  font-size: 0.75rem;
  color: #64748b;
  padding-top: 0.2rem;
  border-top: 1px solid #1e293b;
}

.rule-dim { margin-bottom: 0.3rem; }
.dim-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.dim-label-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.15rem;
}
.dim-empty { font-size: 0.75rem; color: #475569; font-style: italic; }
.dim-val { font-size: 0.78rem; color: #94a3b8; font-family: monospace; }

.sel-edit-row {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  font-family: monospace;
  padding: 0.12rem 0;
}
.sel-add-form {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.3rem 0;
  margin-top: 0.15rem;
  border-top: 1px solid #334155;
}

/* ── Order Cards ── */
.order-list { display: grid; gap: 0.5rem; padding: 0.75rem; }
.order-card {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  transition: all 0.12s;
}
.order-card:hover { border-color: #475569; }
.order-card.editing { border-color: #3b82f6; box-shadow: 0 0 0 1px #3b82f6; }
.order-id { color: #a78bfa; font-weight: 600; font-size: 0.85rem; font-family: monospace; }

.order-meta-controls {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #1e293b;
  font-size: 0.8rem;
  color: #94a3b8;
}
.order-meta-controls label { display: flex; align-items: center; gap: 0.3rem; }
.order-meta-compact {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 0.2rem;
}
.order-meta-compact code {
  background: #1e293b;
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
  font-size: 0.75rem;
  color: #7dd3fc;
}

/* ── Buttons ── */
.btn-primary {
  padding: 0.6rem 1.5rem;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: background 0.12s;
}
.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-secondary {
  padding: 0.6rem 1.5rem;
  background: #334155;
  color: #cbd5e1;
  border: 1px solid #475569;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.12s;
}
.btn-secondary:hover { background: #475569; }

.btn-sm {
  padding: 0.3rem 0.7rem;
  background: #334155;
  color: #cbd5e1;
  border: 1px solid #475569;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background 0.12s;
}
.btn-sm:hover { background: #475569; }

.btn-xs {
  padding: 0.1rem 0.4rem;
  background: #334155;
  color: #94a3b8;
  border: 1px solid #475569;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.7rem;
  line-height: 1.2;
  transition: all 0.12s;
}
.btn-xs:hover { background: #475569; color: #f1f5f9; }
.btn-xs.danger { color: #fca5a5; border-color: #7f1d1d; }
.btn-xs.danger:hover { background: #7f1d1d; color: #fecaca; }
.btn-xs.ghost { color: #64748b; border-color: transparent; }
.btn-xs.ghost:hover { color: #94a3b8; background: #1e293b; }

.action-bar {
  margin-top: 1.5rem;
  display: flex;
  gap: 0.75rem;
}

/* ── Results ── */
.result-header {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.result-stat {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  text-align: center;
}
.color-ok { color: #4ade80; }
.result-stat-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}
.result-stat-value {
  display: block;
  font-size: 1.3rem;
  font-weight: 700;
  color: #f1f5f9;
  font-family: monospace;
}
.result-stat.feasible .result-stat-value,
.result-stat.optimal .result-stat-value { color: #4ade80; }
.result-stat.infeasible .result-stat-value { color: #f87171; }

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.result-table th, .result-table td {
  padding: 0.5rem 0.6rem;
  text-align: left;
  border-bottom: 1px solid #1e293b;
}
.result-table th {
  background: #0f172a;
  font-weight: 600;
  color: #94a3b8;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.result-table tbody tr:hover { background: #1a2332; }
.cell-id { font-family: monospace; font-weight: 600; color: #f1f5f9; }
.cell-ok { color: #4ade80; font-weight: 600; }
.cell-fail { color: #f87171; font-weight: 600; }
.cell-detail {
  font-size: 0.75rem;
  color: #94a3b8;
  font-family: monospace;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Gantt ── */
.gantt-container {
  overflow-x: auto;
  padding: 0.75rem;
  background: #0f172a;
}
.gantt-svg { display: block; min-width: 600px; }
.gantt-label { font-size: 11px; font-family: monospace; fill: #94a3b8; }
.gantt-tick { font-size: 9px; font-family: monospace; fill: #64748b; }
.gantt-bar { cursor: pointer; transition: opacity 0.12s; }
.gantt-bar:hover { opacity: 0.8; stroke: #fff; stroke-width: 1; }
</style>
