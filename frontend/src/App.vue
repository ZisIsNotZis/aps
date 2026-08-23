<script setup>
import { onMounted, ref } from "vue";
import UnifiedPlanner from "./components/UnifiedPlanner.vue";

const backendStatus = ref("Loading…");

onMounted(async () => {
  try {
    const resp = await fetch("/api/health");
    const data = await resp.json();
    backendStatus.value = `${data.status} (${data.service})`;
  } catch {
    backendStatus.value = "unreachable";
  }
});
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <span class="brand-icon">◆</span>
        <span class="brand-text">APS</span>
      </div>
      <span class="health-badge" :class="{ ok: backendStatus.includes('ok'), err: !backendStatus.includes('ok') }">
        {{ backendStatus }}
      </span>
    </header>
    <main class="main">
      <UnifiedPlanner />
    </main>
  </div>
</template>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  --bg-base: #0f1117;
  --bg-surface: #181b23;
  --bg-elevated: #20232d;
  --bg-hover: #282b36;
  --border: #2a2e3a;
  --text-primary: #e8eaed;
  --text-secondary: #9aa0a9;
  --text-muted: #5f6570;
  --accent: #5b8def;
  --accent-dim: #3b6ac8;
  --green: #34d399;
  --red: #ef4444;
  --radius: 8px;
  --radius-sm: 4px;
  font-family: "SF Mono", "Fira Code", "Cascadia Code", "JetBrains Mono", ui-monospace, monospace;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  background: var(--bg-base);
}

body {
  min-height: 100vh;
  background: var(--bg-base);
}
#app {
  background: var(--bg-base);
  min-height: 100vh;
}

.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 48px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-icon {
  font-size: 18px;
  color: var(--accent);
}

.brand-text {
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.5px;
  color: var(--text-primary);
}

.health-badge {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 99px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text-muted);
}

.health-badge.ok {
  color: var(--green);
  border-color: color-mix(in srgb, var(--green) 30%, transparent);
}

.health-badge.err {
  color: var(--red);
  border-color: color-mix(in srgb, var(--red) 30%, transparent);
}

.main {
  flex: 1;
  padding: 24px 32px;
  width: 100%;
  min-width: 0;
}
</style>
