<script>
  import { Router, Route, Link } from 'svelte-routing';
  import { theme } from './lib/stores.js';

  // Route components
  import Home from './routes/Home.svelte';
  import Settings from './routes/Settings.svelte';
  import Campaigns from './routes/Campaigns.svelte';
  import Chronicle from './routes/Chronicle.svelte';
  import Codex from './routes/Codex.svelte';
  import Setup from './routes/Setup.svelte';

  export let url = '';

  // Track current path for conditional layout
  let currentPath = typeof window !== 'undefined' ? window.location.pathname : '/';

  // Update path on navigation
  function handleNavigation() {
    currentPath = window.location.pathname;
  }

  // Listen for navigation events
  if (typeof window !== 'undefined') {
    window.addEventListener('popstate', handleNavigation);
  }

  // Apply theme
  $: document.documentElement.setAttribute('data-theme', $theme);

  // Check if we're on the setup page (full-page layout, no sidebar)
  $: isSetupPage = currentPath === '/setup';
</script>

<Router {url} on:routeLoaded={handleNavigation}>
  {#if isSetupPage}
    <!-- Setup page has its own full-page layout -->
    <Route path="/setup" component={Setup} />
  {:else}
    <div class="app-layout">
      <nav class="sidebar">
        <div class="sidebar-header">
          <h1 class="logo">Chronicle</h1>
          <p class="tagline">CC-Storyteller</p>
        </div>

        <ul class="nav-links">
          <li>
            <Link to="/">Hall of Chronicles</Link>
          </li>
          <li>
            <Link to="/campaigns">Campaigns</Link>
          </li>
          <li>
            <Link to="/settings">Settings</Link>
          </li>
        </ul>

        <div class="sidebar-footer">
          <p class="version">v0.1.0</p>
        </div>
      </nav>

      <main class="main-content">
        <Route path="/" component={Home} />
        <Route path="/setup" component={Setup} />
        <Route path="/settings" component={Settings} />
        <Route path="/campaigns" component={Campaigns} />
        <Route path="/chronicle/:campaignId" let:params>
          <Chronicle campaignId={params.campaignId} />
        </Route>
        <Route path="/codex/:campaignId" let:params>
          <Codex campaignId={params.campaignId} />
        </Route>
      </main>
    </div>
  {/if}
</Router>

<style>
  .app-layout {
    display: flex;
    height: 100vh;
  }

  .sidebar {
    width: 250px;
    background: var(--color-bg-secondary);
    border-right: 1px solid var(--color-border-primary);
    display: flex;
    flex-direction: column;
    padding: var(--spacing-lg);
  }

  .sidebar-header {
    text-align: center;
    padding-bottom: var(--spacing-lg);
    border-bottom: 1px solid var(--color-border-primary);
    margin-bottom: var(--spacing-lg);
  }

  .logo {
    font-size: var(--font-size-2xl);
    margin-bottom: var(--spacing-xs);
  }

  .tagline {
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
  }

  .nav-links {
    list-style: none;
    padding: 0;
    flex: 1;
  }

  .nav-links li {
    margin-bottom: var(--spacing-sm);
  }

  .nav-links :global(a) {
    display: block;
    padding: var(--spacing-sm) var(--spacing-md);
    color: var(--color-text-secondary);
    border-radius: var(--radius-md);
    transition: all var(--transition-fast);
  }

  .nav-links :global(a:hover) {
    background: var(--color-bg-tertiary);
    color: var(--color-text-primary);
  }

  .sidebar-footer {
    padding-top: var(--spacing-lg);
    border-top: 1px solid var(--color-border-primary);
    text-align: center;
  }

  .version {
    color: var(--color-text-muted);
    font-size: var(--font-size-xs);
  }

  .main-content {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-xl);
  }
</style>
