<script>
  import { onMount } from 'svelte';
  import { link } from 'svelte-routing';
  import { campaignsApi } from '../lib/api.js';
  import { campaigns } from '../lib/stores.js';

  onMount(async () => {
    campaigns.setLoading(true);
    try {
      const data = await campaignsApi.list();
      campaigns.setCampaigns(data.campaigns, data.total);
    } catch (error) {
      campaigns.setError(error.message);
    }
  });
</script>

<div class="home">
  <header class="page-header">
    <h1>Hall of Chronicles</h1>
    <p class="subtitle">Welcome, traveler. Your tales await.</p>
  </header>

  <section class="quick-actions">
    <a href="/campaigns" use:link class="action-card">
      <h3>Begin New Chronicle</h3>
      <p>Create a new campaign and embark on a fresh adventure</p>
    </a>

    <a href="/settings" use:link class="action-card">
      <h3>Scribe's Settings</h3>
      <p>Configure your storytelling apparatus</p>
    </a>
  </section>

  {#if $campaigns.loading}
    <div class="loading">Loading chronicles...</div>
  {:else if $campaigns.error}
    <div class="error">Error: {$campaigns.error}</div>
  {:else if $campaigns.campaigns.length > 0}
    <section class="recent-campaigns">
      <h2>Recent Chronicles</h2>
      <div class="campaign-grid">
        {#each $campaigns.campaigns.slice(0, 4) as campaign}
          <div class="campaign-card">
            <h3>{campaign.name}</h3>
            <p class="summary">{campaign.setting_summary || 'No description'}</p>
            <div class="meta">
              <span class="turn">Turn {campaign.current_turn}</span>
              <span class="status">{campaign.status}</span>
            </div>
            <div class="actions">
              <a href="/chronicle/{campaign.id}" use:link class="btn">Continue</a>
              <a href="/codex/{campaign.id}" use:link class="btn secondary">Codex</a>
            </div>
          </div>
        {/each}
      </div>
    </section>
  {:else}
    <section class="empty-state">
      <h2>No Chronicles Yet</h2>
      <p>Your journey begins with a single step. Create your first campaign to start weaving tales.</p>
      <a href="/campaigns" use:link class="btn primary">Create Campaign</a>
    </section>
  {/if}
</div>

<style>
  .home {
    max-width: 1000px;
    margin: 0 auto;
  }

  .page-header {
    text-align: center;
    margin-bottom: var(--spacing-2xl);
  }

  .page-header h1 {
    font-size: var(--font-size-4xl);
    margin-bottom: var(--spacing-sm);
  }

  .subtitle {
    color: var(--color-text-muted);
    font-style: italic;
  }

  .quick-actions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-2xl);
  }

  .action-card {
    display: block;
    padding: var(--spacing-xl);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-lg);
    text-decoration: none;
    transition: all var(--transition-normal);
  }

  .action-card:hover {
    border-color: var(--color-accent-highlight);
    transform: translateY(-2px);
  }

  .action-card h3 {
    margin-bottom: var(--spacing-sm);
  }

  .action-card p {
    color: var(--color-text-secondary);
    font-size: var(--font-size-sm);
  }

  .recent-campaigns h2 {
    margin-bottom: var(--spacing-lg);
  }

  .campaign-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: var(--spacing-lg);
  }

  .campaign-card {
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
  }

  .campaign-card h3 {
    margin-bottom: var(--spacing-sm);
    font-size: var(--font-size-lg);
  }

  .campaign-card .summary {
    color: var(--color-text-secondary);
    font-size: var(--font-size-sm);
    margin-bottom: var(--spacing-md);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .campaign-card .meta {
    display: flex;
    justify-content: space-between;
    color: var(--color-text-muted);
    font-size: var(--font-size-xs);
    margin-bottom: var(--spacing-md);
  }

  .campaign-card .actions {
    display: flex;
    gap: var(--spacing-sm);
  }

  .btn {
    display: inline-block;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-accent-primary);
    color: var(--color-text-primary);
    border: 1px solid var(--color-border-accent);
    border-radius: var(--radius-md);
    font-family: var(--font-display);
    font-size: var(--font-size-sm);
    text-decoration: none;
    transition: all var(--transition-fast);
  }

  .btn:hover {
    background: var(--color-accent-secondary);
  }

  .btn.primary {
    background: var(--color-accent-highlight);
    color: var(--color-bg-primary);
  }

  .btn.secondary {
    background: transparent;
    border-color: var(--color-border-primary);
  }

  .empty-state {
    text-align: center;
    padding: var(--spacing-2xl);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-lg);
  }

  .empty-state h2 {
    margin-bottom: var(--spacing-sm);
  }

  .empty-state p {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-lg);
  }

  .loading, .error {
    text-align: center;
    padding: var(--spacing-xl);
    color: var(--color-text-muted);
  }

  .error {
    color: var(--color-error);
  }
</style>
