<script lang="ts">
  import { page } from '$app/stores';
</script>

<nav>
  <div class="brand">CREWSOUL</div>
  <div class="links">
    <a href="/dashboard" class:active={$page.url.pathname === '/dashboard'}>Dashboard</a>
    <a href="/queue" class:active={$page.url.pathname === '/queue'}>Queue</a>
    <a href="/settings" class:active={$page.url.pathname === '/settings'}>Settings</a>
  </div>
</nav>

<style>
  nav { display: flex; align-items: center; justify-content: space-between; padding: 0 1.5rem; height: 3rem; border-bottom: 1px solid var(--border); background: var(--bg-surface); }
  .brand { font-weight: 700; font-size: 0.875rem; letter-spacing: 0.1em; color: var(--text-primary); }
  .links { display: flex; gap: 1.5rem; }
  a { color: var(--text-secondary); text-decoration: none; font-size: 0.8125rem; }
  a:hover, a.active { color: var(--text-primary); }
</style>
