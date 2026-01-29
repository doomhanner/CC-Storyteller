<script>
  import { onMount } from 'svelte';
  import { link, navigate } from 'svelte-routing';
  import { campaignsApi } from '../lib/api.js';
  import { campaigns, notifications } from '../lib/stores.js';

  let showCreateForm = false;
  let creating = false;

  // Create form data
  let newCampaign = {
    name: '',
    setting_description: '',
    pc_description: '',
    starting_situation: '',
    additional_notes: '',
    creativity: 0.5,
  };

  onMount(async () => {
    await loadCampaigns();
  });

  async function loadCampaigns() {
    campaigns.setLoading(true);
    try {
      const data = await campaignsApi.list();
      campaigns.setCampaigns(data.campaigns, data.total);
    } catch (error) {
      campaigns.setError(error.message);
      notifications.add(`Failed to load campaigns: ${error.message}`, 'error');
    }
  }

  async function createCampaign() {
    if (!newCampaign.name.trim()) {
      notifications.add('Please enter a campaign name', 'warning');
      return;
    }

    creating = true;
    try {
      const result = await campaignsApi.create(newCampaign);
      campaigns.addCampaign(result.campaign);
      notifications.add(`Campaign "${result.campaign.name}" created!`, 'success');

      // Reset form
      showCreateForm = false;
      newCampaign = {
        name: '',
        setting_description: '',
        pc_description: '',
        starting_situation: '',
        additional_notes: '',
        creativity: 0.5,
      };

      // Navigate to the new campaign
      navigate(`/chronicle/${result.campaign.id}`);
    } catch (error) {
      notifications.add(`Failed to create campaign: ${error.message}`, 'error');
    }
    creating = false;
  }

  async function deleteCampaign(id, name) {
    if (!confirm(`Are you sure you want to delete "${name}"? This cannot be undone.`)) {
      return;
    }

    try {
      await campaignsApi.delete(id);
      campaigns.removeCampaign(id);
      notifications.add(`Campaign "${name}" deleted`, 'success');
    } catch (error) {
      notifications.add(`Failed to delete campaign: ${error.message}`, 'error');
    }
  }
</script>

<div class="campaigns-page">
  <header class="page-header">
    <div class="header-content">
      <h1>The Scriptorium</h1>
      <p class="subtitle">Manage your chronicles and begin new adventures</p>
    </div>
    <button class="primary" on:click={() => showCreateForm = !showCreateForm}>
      {showCreateForm ? 'Cancel' : 'New Chronicle'}
    </button>
  </header>

  {#if showCreateForm}
    <section class="create-form card">
      <h2>Create New Chronicle</h2>

      <form on:submit|preventDefault={createCampaign}>
        <div class="form-group">
          <label for="name">Campaign Name *</label>
          <input
            type="text"
            id="name"
            bind:value={newCampaign.name}
            placeholder="e.g., The Crimson Throne"
            required
          />
        </div>

        <div class="form-group">
          <label for="setting">Setting Description</label>
          <textarea
            id="setting"
            bind:value={newCampaign.setting_description}
            placeholder="Describe your world: genre, tone, key elements..."
            rows="3"
          ></textarea>
        </div>

        <div class="form-group">
          <label for="pc">Player Character</label>
          <textarea
            id="pc"
            bind:value={newCampaign.pc_description}
            placeholder="Describe your character: name, background, abilities..."
            rows="3"
          ></textarea>
        </div>

        <div class="form-group">
          <label for="start">Starting Situation</label>
          <textarea
            id="start"
            bind:value={newCampaign.starting_situation}
            placeholder="Where does your story begin?"
            rows="2"
          ></textarea>
        </div>

        <div class="form-group">
          <label for="notes">Additional Notes</label>
          <textarea
            id="notes"
            bind:value={newCampaign.additional_notes}
            placeholder="Any other details, themes, or constraints..."
            rows="2"
          ></textarea>
        </div>

        <div class="form-group">
          <label for="creativity">
            Creativity Level: {(newCampaign.creativity * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            id="creativity"
            bind:value={newCampaign.creativity}
            min="0"
            max="1"
            step="0.1"
          />
          <div class="range-labels">
            <span>Minimal</span>
            <span>Expansive</span>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" on:click={() => showCreateForm = false}>Cancel</button>
          <button type="submit" class="primary" disabled={creating}>
            {creating ? 'Creating...' : 'Create Chronicle'}
          </button>
        </div>
      </form>
    </section>
  {/if}

  {#if $campaigns.loading}
    <div class="loading">Loading chronicles...</div>
  {:else if $campaigns.error}
    <div class="error">Error: {$campaigns.error}</div>
  {:else if $campaigns.campaigns.length > 0}
    <section class="campaign-list">
      {#each $campaigns.campaigns as campaign}
        <div class="campaign-card">
          <div class="campaign-info">
            <h3>{campaign.name}</h3>
            <p class="summary">{campaign.setting_summary || 'No description available'}</p>
            <div class="meta">
              <span class="turn">Turn {campaign.current_turn}</span>
              <span class="sessions">{campaign.total_sessions} sessions</span>
              <span class="status" class:ready={campaign.status === 'ready'}>{campaign.status}</span>
            </div>
          </div>
          <div class="campaign-actions">
            <a href="/chronicle/{campaign.id}" use:link class="btn primary">Play</a>
            <a href="/codex/{campaign.id}" use:link class="btn">Codex</a>
            <button class="btn danger" on:click={() => deleteCampaign(campaign.id, campaign.name)}>
              Delete
            </button>
          </div>
        </div>
      {/each}
    </section>
  {:else}
    <div class="empty-state">
      <h2>No Chronicles Found</h2>
      <p>Create your first chronicle to begin your adventures.</p>
      <button class="primary" on:click={() => showCreateForm = true}>Create Chronicle</button>
    </div>
  {/if}
</div>

<style>
  .campaigns-page {
    max-width: 900px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-xl);
  }

  .header-content h1 {
    margin-bottom: var(--spacing-sm);
  }

  .subtitle {
    color: var(--color-text-muted);
  }

  .create-form {
    margin-bottom: var(--spacing-xl);
  }

  .create-form h2 {
    margin-bottom: var(--spacing-lg);
  }

  .form-group {
    margin-bottom: var(--spacing-md);
  }

  .form-group label {
    display: block;
    margin-bottom: var(--spacing-xs);
    color: var(--color-text-secondary);
  }

  .form-group input,
  .form-group textarea,
  .form-group select {
    width: 100%;
  }

  .form-group input[type="range"] {
    padding: 0;
    background: transparent;
    border: none;
  }

  .range-labels {
    display: flex;
    justify-content: space-between;
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    margin-top: var(--spacing-xs);
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
  }

  .campaign-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .campaign-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    gap: var(--spacing-lg);
  }

  .campaign-info {
    flex: 1;
  }

  .campaign-info h3 {
    margin-bottom: var(--spacing-sm);
  }

  .campaign-info .summary {
    color: var(--color-text-secondary);
    font-size: var(--font-size-sm);
    margin-bottom: var(--spacing-sm);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .meta {
    display: flex;
    gap: var(--spacing-md);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
  }

  .status {
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-sm);
  }

  .status.ready {
    background: rgba(90, 138, 90, 0.2);
    color: var(--color-success);
  }

  .campaign-actions {
    display: flex;
    gap: var(--spacing-sm);
    flex-shrink: 0;
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
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .btn:hover {
    background: var(--color-accent-secondary);
  }

  .btn.primary {
    background: var(--color-accent-highlight);
    color: var(--color-bg-primary);
  }

  .btn.danger {
    background: transparent;
    border-color: var(--color-error);
    color: var(--color-error);
  }

  .btn.danger:hover {
    background: rgba(168, 84, 84, 0.2);
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
