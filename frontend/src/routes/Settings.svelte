<script>
  import { onMount } from 'svelte';
  import { settingsApi } from '../lib/api.js';
  import { settings, notifications, theme } from '../lib/stores.js';

  let loading = true;
  let saving = false;
  let testing = false;
  let testResult = null;
  let providers = [];
  let showAdvanced = false;

  // Local form state
  let formData = {
    storytellerType: 'anthropic',
    storytellerModel: 'claude-sonnet-4-20250514',
    archivistType: 'anthropic',
    archivistModel: 'claude-sonnet-4-20250514',
    localUrl: 'http://localhost:11434',
    localType: 'ollama',
    debugEnabled: false,
    logPrompts: false,
    logResponses: false,
    theme: 'chronicle',
  };

  onMount(async () => {
    try {
      const [settingsData, providersData] = await Promise.all([
        settingsApi.get(),
        settingsApi.getProviders(),
      ]);

      settings.load(settingsData);
      providers = providersData;

      // Update form from loaded settings
      formData = {
        storytellerType: settingsData.providers.storyteller.type,
        storytellerModel: settingsData.providers.storyteller.model,
        archivistType: settingsData.providers.archivist.type,
        archivistModel: settingsData.providers.archivist.model,
        localUrl: settingsData.local.url,
        localType: settingsData.local.type,
        debugEnabled: settingsData.debug.enabled,
        logPrompts: settingsData.debug.log_prompts,
        logResponses: settingsData.debug.log_responses,
        theme: settingsData.ui.theme,
      };

      loading = false;
    } catch (error) {
      notifications.add(`Failed to load settings: ${error.message}`, 'error');
      loading = false;
    }
  });

  async function saveSettings() {
    saving = true;
    try {
      const updates = {
        providers: {
          storyteller: { type: formData.storytellerType, model: formData.storytellerModel },
          archivist: { type: formData.archivistType, model: formData.archivistModel },
        },
        local: { url: formData.localUrl, type: formData.localType },
        ui: { theme: formData.theme },
        debug: {
          enabled: formData.debugEnabled,
          log_prompts: formData.logPrompts,
          log_responses: formData.logResponses,
        },
      };

      const result = await settingsApi.update(updates);
      settings.load(result);
      theme.set(formData.theme);
      notifications.add('Settings saved successfully', 'success');
    } catch (error) {
      notifications.add(`Failed to save settings: ${error.message}`, 'error');
    }
    saving = false;
  }

  async function testConnection(role) {
    testing = true;
    testResult = null;

    const providerType = role === 'storyteller' ? formData.storytellerType : formData.archivistType;
    const model = role === 'storyteller' ? formData.storytellerModel : formData.archivistModel;

    try {
      const result = await settingsApi.testProvider({
        provider_type: providerType,
        model: model,
        api_base: ['ollama', 'local'].includes(providerType) ? formData.localUrl : null,
      });

      testResult = result;

      if (result.success) {
        notifications.add(`Connection successful (${result.latency_ms?.toFixed(0)}ms)`, 'success');
      } else {
        notifications.add(`Connection failed: ${result.message}`, 'error');
      }
    } catch (error) {
      testResult = { success: false, message: error.message };
      notifications.add(`Test failed: ${error.message}`, 'error');
    }
    testing = false;
  }

  function getModelsForProvider(providerType) {
    const provider = providers.find(p => p.type === providerType);
    return provider?.models || [];
  }

  $: storytellerModels = getModelsForProvider(formData.storytellerType);
  $: archivistModels = getModelsForProvider(formData.archivistType);
</script>

<div class="settings-page">
  <header class="page-header">
    <h1>Scribe's Settings</h1>
    <p class="subtitle">Configure your chronicle apparatus</p>
  </header>

  {#if loading}
    <div class="loading">Loading settings...</div>
  {:else}
    <form on:submit|preventDefault={saveSettings}>
      <!-- Provider Configuration -->
      <section class="settings-section">
        <h2>Provider Configuration</h2>
        <p class="section-desc">Configure the LLM providers for each agent role.</p>

        <!-- Storyteller -->
        <div class="provider-config">
          <h3>Storyteller</h3>
          <p class="role-desc">Generates narrative content and dialogue</p>

          <div class="form-row">
            <div class="form-group">
              <label for="storyteller-type">Provider</label>
              <select id="storyteller-type" bind:value={formData.storytellerType}>
                {#each providers as provider}
                  <option value={provider.type}>{provider.name}</option>
                {/each}
              </select>
            </div>

            <div class="form-group">
              <label for="storyteller-model">Model</label>
              {#if storytellerModels.length > 0}
                <select id="storyteller-model" bind:value={formData.storytellerModel}>
                  {#each storytellerModels as model}
                    <option value={model}>{model}</option>
                  {/each}
                </select>
              {:else}
                <input
                  type="text"
                  id="storyteller-model"
                  bind:value={formData.storytellerModel}
                  placeholder="Model name"
                />
              {/if}
            </div>

            <button
              type="button"
              class="test-btn"
              on:click={() => testConnection('storyteller')}
              disabled={testing}
            >
              {testing ? 'Testing...' : 'Test'}
            </button>
          </div>
        </div>

        <!-- Archivist -->
        <div class="provider-config">
          <h3>Archivist</h3>
          <p class="role-desc">Handles data extraction and logic</p>

          <div class="form-row">
            <div class="form-group">
              <label for="archivist-type">Provider</label>
              <select id="archivist-type" bind:value={formData.archivistType}>
                {#each providers as provider}
                  <option value={provider.type}>{provider.name}</option>
                {/each}
              </select>
            </div>

            <div class="form-group">
              <label for="archivist-model">Model</label>
              {#if archivistModels.length > 0}
                <select id="archivist-model" bind:value={formData.archivistModel}>
                  {#each archivistModels as model}
                    <option value={model}>{model}</option>
                  {/each}
                </select>
              {:else}
                <input
                  type="text"
                  id="archivist-model"
                  bind:value={formData.archivistModel}
                  placeholder="Model name"
                />
              {/if}
            </div>

            <button
              type="button"
              class="test-btn"
              on:click={() => testConnection('archivist')}
              disabled={testing}
            >
              {testing ? 'Testing...' : 'Test'}
            </button>
          </div>
        </div>

        <!-- API Key Notice -->
        <div class="notice">
          <strong>Note:</strong> API keys are stored in your <code>.env</code> file for security.
          Set <code>ANTHROPIC_API_KEY</code>, <code>OPENAI_API_KEY</code>, etc.
        </div>
      </section>

      <!-- Local Model Settings -->
      {#if formData.storytellerType === 'ollama' || formData.storytellerType === 'local' ||
           formData.archivistType === 'ollama' || formData.archivistType === 'local'}
        <section class="settings-section">
          <h2>Local Model Settings</h2>
          <p class="section-desc">Configure connection to local model servers.</p>

          <div class="form-row">
            <div class="form-group">
              <label for="local-url">Server URL</label>
              <input
                type="text"
                id="local-url"
                bind:value={formData.localUrl}
                placeholder="http://localhost:11434"
              />
            </div>

            <div class="form-group">
              <label for="local-type">Server Type</label>
              <select id="local-type" bind:value={formData.localType}>
                <option value="ollama">Ollama</option>
                <option value="llamacpp">llama.cpp</option>
                <option value="lmstudio">LM Studio</option>
                <option value="vllm">vLLM</option>
              </select>
            </div>
          </div>
        </section>
      {/if}

      <!-- UI Settings -->
      <section class="settings-section">
        <h2>Appearance</h2>

        <div class="form-group">
          <label for="theme">Theme</label>
          <select id="theme" bind:value={formData.theme}>
            <option value="chronicle">Chronicle (Default)</option>
            <option value="eldritch" disabled>Eldritch (Coming Soon)</option>
          </select>
        </div>
      </section>

      <!-- Advanced Settings -->
      <section class="settings-section">
        <button
          type="button"
          class="advanced-toggle"
          on:click={() => showAdvanced = !showAdvanced}
        >
          {showAdvanced ? '▼' : '▶'} Advanced Settings
        </button>

        {#if showAdvanced}
          <div class="advanced-content">
            <div class="form-group checkbox">
              <label>
                <input type="checkbox" bind:checked={formData.debugEnabled} />
                Enable Debug Mode
              </label>
            </div>

            <div class="form-group checkbox">
              <label>
                <input type="checkbox" bind:checked={formData.logPrompts} />
                Log Prompts (Debug)
              </label>
            </div>

            <div class="form-group checkbox">
              <label>
                <input type="checkbox" bind:checked={formData.logResponses} />
                Log Responses (Debug)
              </label>
            </div>
          </div>
        {/if}
      </section>

      <!-- Save Button -->
      <div class="form-actions">
        <button type="submit" class="primary" disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </form>
  {/if}

  {#if testResult}
    <div class="test-result" class:success={testResult.success} class:error={!testResult.success}>
      <strong>{testResult.success ? 'Success' : 'Failed'}:</strong>
      {testResult.message}
      {#if testResult.latency_ms}
        <span class="latency">({testResult.latency_ms.toFixed(0)}ms)</span>
      {/if}
    </div>
  {/if}
</div>

<style>
  .settings-page {
    max-width: 800px;
    margin: 0 auto;
  }

  .page-header {
    margin-bottom: var(--spacing-2xl);
  }

  .page-header h1 {
    margin-bottom: var(--spacing-sm);
  }

  .subtitle {
    color: var(--color-text-muted);
  }

  .settings-section {
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
    margin-bottom: var(--spacing-lg);
  }

  .settings-section h2 {
    font-size: var(--font-size-xl);
    margin-bottom: var(--spacing-sm);
  }

  .section-desc {
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
    margin-bottom: var(--spacing-lg);
  }

  .provider-config {
    padding: var(--spacing-md);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
  }

  .provider-config h3 {
    font-size: var(--font-size-lg);
    margin-bottom: var(--spacing-xs);
  }

  .role-desc {
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
    margin-bottom: var(--spacing-md);
  }

  .form-row {
    display: flex;
    gap: var(--spacing-md);
    align-items: flex-end;
    flex-wrap: wrap;
  }

  .form-group {
    flex: 1;
    min-width: 150px;
  }

  .form-group label {
    display: block;
    margin-bottom: var(--spacing-xs);
    color: var(--color-text-secondary);
    font-size: var(--font-size-sm);
  }

  .form-group input,
  .form-group select {
    width: 100%;
  }

  .form-group.checkbox label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
  }

  .form-group.checkbox input {
    width: auto;
  }

  .test-btn {
    padding: var(--spacing-sm) var(--spacing-lg);
    white-space: nowrap;
  }

  .notice {
    padding: var(--spacing-md);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-top: var(--spacing-md);
  }

  .notice code {
    background: var(--color-bg-primary);
    padding: var(--spacing-xs);
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
  }

  .advanced-toggle {
    background: none;
    border: none;
    color: var(--color-text-secondary);
    cursor: pointer;
    font-family: var(--font-body);
    padding: 0;
  }

  .advanced-toggle:hover {
    color: var(--color-text-primary);
  }

  .advanced-content {
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--color-border-primary);
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-md);
  }

  .form-actions button {
    padding: var(--spacing-md) var(--spacing-xl);
  }

  .test-result {
    margin-top: var(--spacing-lg);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
  }

  .test-result.success {
    background: rgba(90, 138, 90, 0.2);
    border: 1px solid var(--color-success);
    color: var(--color-success);
  }

  .test-result.error {
    background: rgba(168, 84, 84, 0.2);
    border: 1px solid var(--color-error);
    color: var(--color-error);
  }

  .latency {
    color: var(--color-text-muted);
    margin-left: var(--spacing-sm);
  }

  .loading {
    text-align: center;
    padding: var(--spacing-xl);
    color: var(--color-text-muted);
  }
</style>
