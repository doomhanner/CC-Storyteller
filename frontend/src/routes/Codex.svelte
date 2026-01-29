<script>
  import { onMount } from 'svelte';
  import { link } from 'svelte-routing';
  import { codexApi, campaignsApi } from '../lib/api.js';
  import { notifications } from '../lib/stores.js';

  export let campaignId;

  let campaign = null;
  let entities = [];
  let stats = {};
  let loading = true;
  let selectedType = null;
  let selectedEntity = null;
  let entityDetail = null;
  let loadingDetail = false;

  const entityTypes = [
    { value: 'character', label: 'Characters', icon: '👤' },
    { value: 'location', label: 'Locations', icon: '🏰' },
    { value: 'item', label: 'Items', icon: '⚔️' },
    { value: 'faction', label: 'Factions', icon: '🏛️' },
    { value: 'lore', label: 'Lore', icon: '📜' },
  ];

  onMount(async () => {
    try {
      const [campaignData, statsData, entitiesData] = await Promise.all([
        campaignsApi.get(campaignId),
        codexApi.getStats(campaignId),
        codexApi.listEntities(campaignId),
      ]);

      campaign = campaignData;
      stats = statsData;
      entities = entitiesData.entities;
      loading = false;
    } catch (error) {
      notifications.add(`Failed to load codex: ${error.message}`, 'error');
      loading = false;
    }
  });

  async function filterByType(type) {
    selectedType = type === selectedType ? null : type;
    selectedEntity = null;
    entityDetail = null;

    try {
      const data = await codexApi.listEntities(campaignId, selectedType);
      entities = data.entities;
    } catch (error) {
      notifications.add(`Failed to filter entities: ${error.message}`, 'error');
    }
  }

  async function selectEntity(entity) {
    if (selectedEntity?.id === entity.id) {
      selectedEntity = null;
      entityDetail = null;
      return;
    }

    selectedEntity = entity;
    loadingDetail = true;

    try {
      entityDetail = await codexApi.getEntity(campaignId, entity.id);
    } catch (error) {
      notifications.add(`Failed to load entity: ${error.message}`, 'error');
    }
    loadingDetail = false;
  }

  function getEntityIcon(type) {
    const found = entityTypes.find(t => t.value === type);
    return found?.icon || '📄';
  }
</script>

<div class="codex-page">
  {#if loading}
    <div class="loading">Loading the Codex...</div>
  {:else}
    <header class="codex-header">
      <div class="header-info">
        <h1>The Codex</h1>
        <p class="subtitle">{campaign?.name || 'Campaign'} - Entity Bible</p>
      </div>
      <a href="/chronicle/{campaignId}" use:link class="btn">Return to Chronicle</a>
    </header>

    <div class="codex-stats">
      {#each entityTypes as type}
        <button
          class="stat-card"
          class:active={selectedType === type.value}
          on:click={() => filterByType(type.value)}
        >
          <span class="icon">{type.icon}</span>
          <span class="count">{stats[type.value + 's'] || 0}</span>
          <span class="label">{type.label}</span>
        </button>
      {/each}
    </div>

    <div class="codex-content">
      <div class="entity-list">
        <h2>
          {selectedType ? entityTypes.find(t => t.value === selectedType)?.label : 'All Entities'}
          <span class="count">({entities.length})</span>
        </h2>

        {#if entities.length === 0}
          <p class="empty">No entities found</p>
        {:else}
          <ul>
            {#each entities as entity}
              <li>
                <button
                  class="entity-item"
                  class:selected={selectedEntity?.id === entity.id}
                  on:click={() => selectEntity(entity)}
                >
                  <span class="icon">{getEntityIcon(entity.type)}</span>
                  <div class="entity-info">
                    <span class="name">{entity.name}</span>
                    <span class="desc">{entity.description || 'No description'}</span>
                  </div>
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>

      <div class="entity-detail">
        {#if loadingDetail}
          <div class="loading-detail">Loading...</div>
        {:else if entityDetail}
          <div class="detail-card">
            <header class="detail-header">
              <span class="icon">{getEntityIcon(entityDetail.type)}</span>
              <div>
                <h2>{entityDetail.name}</h2>
                <span class="type">{entityDetail.type}</span>
              </div>
            </header>

            {#if entityDetail.description}
              <section class="detail-section">
                <h3>Description</h3>
                <p>{entityDetail.description}</p>
              </section>
            {/if}

            {#if entityDetail.tags.length > 0}
              <section class="detail-section">
                <h3>Tags</h3>
                <div class="tags">
                  {#each entityDetail.tags as tag}
                    <span class="tag">{tag}</span>
                  {/each}
                </div>
              </section>
            {/if}

            {#if Object.keys(entityDetail.attributes).length > 0}
              <section class="detail-section">
                <h3>Attributes</h3>
                <dl class="attributes">
                  {#each Object.entries(entityDetail.attributes) as [key, value]}
                    <div class="attribute">
                      <dt>{key}</dt>
                      <dd>{typeof value === 'object' ? JSON.stringify(value) : value}</dd>
                    </div>
                  {/each}
                </dl>
              </section>
            {/if}

            {#if entityDetail.relationships.length > 0}
              <section class="detail-section">
                <h3>Relationships</h3>
                <ul class="relationships">
                  {#each entityDetail.relationships as rel}
                    <li class="relationship">
                      <span class="rel-type">{rel.relationship_type}</span>
                      <span class="rel-target">
                        {rel.source_id === entityDetail.id ? rel.target_name : rel.source_name}
                      </span>
                      {#if rel.description}
                        <span class="rel-desc">{rel.description}</span>
                      {/if}
                    </li>
                  {/each}
                </ul>
              </section>
            {/if}

            <footer class="detail-footer">
              <span>Created: Turn {entityDetail.turn_created}</span>
              <span>Modified: Turn {entityDetail.turn_modified}</span>
            </footer>
          </div>
        {:else}
          <div class="no-selection">
            <p>Select an entity to view details</p>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .codex-page {
    display: flex;
    flex-direction: column;
    height: calc(100vh - var(--spacing-xl) * 2);
  }

  .codex-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-lg);
  }

  .header-info h1 {
    margin-bottom: var(--spacing-xs);
  }

  .subtitle {
    color: var(--color-text-muted);
  }

  .btn {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-accent-primary);
    color: var(--color-text-primary);
    border: 1px solid var(--color-border-accent);
    border-radius: var(--radius-md);
    font-family: var(--font-display);
    font-size: var(--font-size-sm);
    text-decoration: none;
  }

  .codex-stats {
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
    flex-wrap: wrap;
  }

  .stat-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    min-width: 100px;
  }

  .stat-card:hover {
    border-color: var(--color-accent-highlight);
  }

  .stat-card.active {
    background: var(--color-bg-elevated);
    border-color: var(--color-accent-highlight);
  }

  .stat-card .icon {
    font-size: var(--font-size-2xl);
    margin-bottom: var(--spacing-xs);
  }

  .stat-card .count {
    font-family: var(--font-display);
    font-size: var(--font-size-xl);
    color: var(--color-accent-highlight);
  }

  .stat-card .label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
  }

  .codex-content {
    display: grid;
    grid-template-columns: 350px 1fr;
    gap: var(--spacing-lg);
    flex: 1;
    overflow: hidden;
  }

  .entity-list {
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    overflow-y: auto;
  }

  .entity-list h2 {
    font-size: var(--font-size-lg);
    margin-bottom: var(--spacing-md);
    display: flex;
    align-items: baseline;
    gap: var(--spacing-sm);
  }

  .entity-list h2 .count {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    font-weight: normal;
  }

  .entity-list ul {
    list-style: none;
    padding: 0;
  }

  .entity-list li {
    margin-bottom: var(--spacing-sm);
  }

  .entity-item {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    width: 100%;
    padding: var(--spacing-sm);
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    text-align: left;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .entity-item:hover {
    background: var(--color-bg-tertiary);
  }

  .entity-item.selected {
    background: var(--color-bg-elevated);
    border-color: var(--color-accent-highlight);
  }

  .entity-item .icon {
    font-size: var(--font-size-lg);
    flex-shrink: 0;
  }

  .entity-info {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .entity-info .name {
    font-family: var(--font-display);
    color: var(--color-text-accent);
  }

  .entity-info .desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .entity-detail {
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    overflow-y: auto;
  }

  .detail-card {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .detail-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--color-border-primary);
    margin-bottom: var(--spacing-lg);
  }

  .detail-header .icon {
    font-size: var(--font-size-3xl);
  }

  .detail-header h2 {
    margin-bottom: var(--spacing-xs);
  }

  .detail-header .type {
    color: var(--color-text-muted);
    text-transform: capitalize;
  }

  .detail-section {
    margin-bottom: var(--spacing-lg);
  }

  .detail-section h3 {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
  }

  .tag {
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-sm);
  }

  .attributes {
    display: grid;
    gap: var(--spacing-sm);
  }

  .attribute {
    display: flex;
    gap: var(--spacing-md);
  }

  .attribute dt {
    color: var(--color-text-secondary);
    min-width: 100px;
  }

  .attribute dd {
    color: var(--color-text-primary);
  }

  .relationships {
    list-style: none;
    padding: 0;
  }

  .relationship {
    padding: var(--spacing-sm);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-sm);
  }

  .rel-type {
    display: inline-block;
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-accent-secondary);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-xs);
    margin-right: var(--spacing-sm);
  }

  .rel-target {
    color: var(--color-accent-highlight);
  }

  .rel-desc {
    display: block;
    margin-top: var(--spacing-xs);
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
  }

  .detail-footer {
    margin-top: auto;
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--color-border-primary);
    display: flex;
    justify-content: space-between;
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
  }

  .no-selection, .loading-detail {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--color-text-muted);
  }

  .empty {
    color: var(--color-text-muted);
    text-align: center;
    padding: var(--spacing-lg);
  }

  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--color-text-muted);
  }
</style>
