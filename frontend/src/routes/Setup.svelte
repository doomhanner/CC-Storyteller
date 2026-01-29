<script>
  import { onMount } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { settingsApi, setupApi } from '../lib/api.js';
  import { notifications } from '../lib/stores.js';

  let currentStep = 0;
  let loading = false;
  let testing = false;
  let testResult = null;

  // Form data
  let selectedProvider = 'anthropic';
  let apiKey = '';
  let storytellerModel = 'claude-sonnet-4-20250514';
  let archivistModel = 'claude-sonnet-4-20250514';

  // Provider info
  const providers = [
    {
      id: 'anthropic',
      name: 'Anthropic (Claude)',
      description: 'Recommended for best narrative quality',
      keyUrl: 'https://console.anthropic.com/settings/keys',
      keyPlaceholder: 'sk-ant-...',
      models: ['claude-sonnet-4-20250514', 'claude-opus-4-20250514', 'claude-3-5-sonnet-20241022'],
    },
    {
      id: 'openai',
      name: 'OpenAI (GPT)',
      description: 'Alternative with GPT-4 models',
      keyUrl: 'https://platform.openai.com/api-keys',
      keyPlaceholder: 'sk-...',
      models: ['gpt-4o', 'gpt-4-turbo', 'gpt-4'],
    },
    {
      id: 'ollama',
      name: 'Ollama (Local)',
      description: 'Run models locally - no API key needed',
      keyUrl: null,
      keyPlaceholder: '',
      models: ['llama3.1', 'mistral', 'mixtral'],
    },
  ];

  const steps = [
    { title: 'Welcome', icon: '📜' },
    { title: 'Provider', icon: '🔌' },
    { title: 'API Key', icon: '🔑' },
    { title: 'Test', icon: '✓' },
    { title: 'Models', icon: '🤖' },
    { title: 'Complete', icon: '🎉' },
  ];

  $: currentProvider = providers.find(p => p.id === selectedProvider);
  $: needsApiKey = selectedProvider !== 'ollama';

  onMount(async () => {
    // Check if already configured
    try {
      const status = await setupApi.getStatus();
      if (status.is_configured) {
        // Already set up, redirect to home
        navigate('/', { replace: true });
      }
    } catch (error) {
      // Continue with setup
    }
  });

  function nextStep() {
    if (currentStep < steps.length - 1) {
      currentStep++;
    }
  }

  function prevStep() {
    if (currentStep > 0) {
      currentStep--;
    }
  }

  async function testConnection() {
    testing = true;
    testResult = null;

    try {
      const result = await settingsApi.testProvider({
        provider_type: selectedProvider,
        model: storytellerModel,
        api_key: apiKey || undefined,
      });

      testResult = result;

      if (result.success) {
        notifications.add('Connection successful!', 'success');
      }
    } catch (error) {
      testResult = { success: false, message: error.message };
    }

    testing = false;
  }

  async function completeSetup() {
    loading = true;

    try {
      // Save API key to .env via API
      if (needsApiKey && apiKey) {
        await setupApi.saveApiKey(selectedProvider, apiKey);
      }

      // Save settings to config.yaml
      await settingsApi.update({
        providers: {
          storyteller: { type: selectedProvider, model: storytellerModel },
          archivist: { type: selectedProvider, model: archivistModel },
        },
      });

      notifications.add('Setup complete! Welcome to CC-Storyteller.', 'success');

      // Redirect to home
      setTimeout(() => {
        navigate('/', { replace: true });
      }, 1000);
    } catch (error) {
      notifications.add(`Setup failed: ${error.message}`, 'error');
    }

    loading = false;
  }

  function skipSetup() {
    navigate('/', { replace: true });
  }
</script>

<div class="setup-page">
  <div class="setup-container">
    <!-- Progress indicator -->
    <div class="progress-bar">
      {#each steps as step, i}
        <div
          class="progress-step"
          class:active={i === currentStep}
          class:completed={i < currentStep}
        >
          <span class="step-icon">{step.icon}</span>
          <span class="step-title">{step.title}</span>
        </div>
        {#if i < steps.length - 1}
          <div class="progress-line" class:completed={i < currentStep}></div>
        {/if}
      {/each}
    </div>

    <!-- Step content -->
    <div class="step-content">
      {#if currentStep === 0}
        <!-- Welcome -->
        <div class="welcome-step">
          <h1>Welcome to CC-Storyteller</h1>
          <p class="tagline">Your Chronicle Awaits</p>

          <div class="welcome-text">
            <p>
              CC-Storyteller is an LLM-powered narrative simulation engine that brings
              your stories to life. Create immersive campaigns with intelligent NPCs,
              dynamic worlds, and emergent storytelling.
            </p>
            <p>
              Let's set up your connection to an AI provider. This will only take a minute.
            </p>
          </div>

          <div class="features">
            <div class="feature">
              <span class="feature-icon">📖</span>
              <span>Deep narrative simulation</span>
            </div>
            <div class="feature">
              <span class="feature-icon">🎭</span>
              <span>Intelligent NPCs with memory</span>
            </div>
            <div class="feature">
              <span class="feature-icon">🗺️</span>
              <span>Dynamic world tracking</span>
            </div>
          </div>
        </div>

      {:else if currentStep === 1}
        <!-- Provider Selection -->
        <div class="provider-step">
          <h2>Choose Your Provider</h2>
          <p>Select which AI service you'd like to use for generating narratives.</p>

          <div class="provider-options">
            {#each providers as provider}
              <button
                class="provider-option"
                class:selected={selectedProvider === provider.id}
                on:click={() => selectedProvider = provider.id}
              >
                <span class="provider-name">{provider.name}</span>
                <span class="provider-desc">{provider.description}</span>
              </button>
            {/each}
          </div>
        </div>

      {:else if currentStep === 2}
        <!-- API Key -->
        <div class="apikey-step">
          <h2>Enter API Key</h2>

          {#if needsApiKey}
            <p>Enter your {currentProvider.name} API key to connect.</p>

            <div class="apikey-form">
              <label for="apikey">API Key</label>
              <input
                id="apikey"
                type="password"
                bind:value={apiKey}
                placeholder={currentProvider.keyPlaceholder}
              />

              <a
                href={currentProvider.keyUrl}
                target="_blank"
                rel="noopener noreferrer"
                class="get-key-link"
              >
                Get an API key from {currentProvider.name} →
              </a>
            </div>

            <div class="security-note">
              <strong>Security:</strong> Your API key is stored locally in your .env file
              and never sent anywhere except to the AI provider.
            </div>
          {:else}
            <p>Ollama runs locally - no API key needed!</p>
            <p class="ollama-note">
              Make sure Ollama is running on your machine. If not installed,
              <a href="https://ollama.ai" target="_blank" rel="noopener noreferrer">
                download it here
              </a>.
            </p>
          {/if}
        </div>

      {:else if currentStep === 3}
        <!-- Test Connection -->
        <div class="test-step">
          <h2>Test Connection</h2>
          <p>Let's verify your connection works before continuing.</p>

          <button
            class="test-button"
            on:click={testConnection}
            disabled={testing || (needsApiKey && !apiKey)}
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </button>

          {#if testResult}
            <div class="test-result" class:success={testResult.success} class:error={!testResult.success}>
              {#if testResult.success}
                <span class="result-icon">✓</span>
                <span>Connection successful!</span>
                {#if testResult.latency_ms}
                  <span class="latency">({testResult.latency_ms.toFixed(0)}ms)</span>
                {/if}
              {:else}
                <span class="result-icon">✗</span>
                <span>{testResult.message}</span>
              {/if}
            </div>
          {/if}
        </div>

      {:else if currentStep === 4}
        <!-- Model Selection -->
        <div class="models-step">
          <h2>Choose Models</h2>
          <p>Select which models to use for each role. You can change these later.</p>

          <div class="model-config">
            <div class="model-role">
              <h3>Storyteller</h3>
              <p class="role-desc">Generates narrative content and dialogue</p>
              <select bind:value={storytellerModel}>
                {#each currentProvider.models as model}
                  <option value={model}>{model}</option>
                {/each}
              </select>
            </div>

            <div class="model-role">
              <h3>Archivist</h3>
              <p class="role-desc">Handles data extraction and world tracking</p>
              <select bind:value={archivistModel}>
                {#each currentProvider.models as model}
                  <option value={model}>{model}</option>
                {/each}
              </select>
            </div>
          </div>

          <p class="models-tip">
            <strong>Tip:</strong> Using the same model for both roles is recommended for most users.
          </p>
        </div>

      {:else if currentStep === 5}
        <!-- Complete -->
        <div class="complete-step">
          <h2>Setup Complete!</h2>

          <div class="complete-icon">🎉</div>

          <p>You're all set to begin your chronicles.</p>

          <div class="summary">
            <div class="summary-item">
              <span class="label">Provider:</span>
              <span class="value">{currentProvider.name}</span>
            </div>
            <div class="summary-item">
              <span class="label">Storyteller:</span>
              <span class="value">{storytellerModel}</span>
            </div>
            <div class="summary-item">
              <span class="label">Archivist:</span>
              <span class="value">{archivistModel}</span>
            </div>
          </div>
        </div>
      {/if}
    </div>

    <!-- Navigation -->
    <div class="step-navigation">
      {#if currentStep > 0 && currentStep < 5}
        <button class="nav-btn secondary" on:click={prevStep}>Back</button>
      {:else}
        <div></div>
      {/if}

      {#if currentStep === 0}
        <div class="nav-right">
          <button class="nav-btn text" on:click={skipSetup}>Skip for now</button>
          <button class="nav-btn primary" on:click={nextStep}>Get Started</button>
        </div>
      {:else if currentStep === 2 && needsApiKey && !apiKey}
        <button class="nav-btn primary" disabled>Next</button>
      {:else if currentStep === 3}
        <button
          class="nav-btn primary"
          on:click={nextStep}
          disabled={!testResult?.success}
        >
          {testResult?.success ? 'Next' : 'Test First'}
        </button>
      {:else if currentStep === 5}
        <button class="nav-btn primary" on:click={completeSetup} disabled={loading}>
          {loading ? 'Saving...' : 'Start Your Chronicle'}
        </button>
      {:else}
        <button class="nav-btn primary" on:click={nextStep}>Next</button>
      {/if}
    </div>
  </div>
</div>

<style>
  .setup-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-xl);
    background: var(--color-bg-primary);
  }

  .setup-container {
    max-width: 600px;
    width: 100%;
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-lg);
    padding: var(--spacing-2xl);
  }

  /* Progress bar */
  .progress-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--spacing-2xl);
    flex-wrap: wrap;
    gap: var(--spacing-xs);
  }

  .progress-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-xs);
    opacity: 0.4;
    transition: opacity var(--transition-normal);
  }

  .progress-step.active,
  .progress-step.completed {
    opacity: 1;
  }

  .step-icon {
    font-size: var(--font-size-xl);
  }

  .step-title {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
  }

  .progress-line {
    width: 30px;
    height: 2px;
    background: var(--color-border-primary);
    margin: 0 var(--spacing-xs);
  }

  .progress-line.completed {
    background: var(--color-accent-highlight);
  }

  /* Step content */
  .step-content {
    min-height: 300px;
    margin-bottom: var(--spacing-xl);
  }

  .step-content h1 {
    font-size: var(--font-size-3xl);
    margin-bottom: var(--spacing-sm);
    text-align: center;
  }

  .step-content h2 {
    font-size: var(--font-size-2xl);
    margin-bottom: var(--spacing-md);
  }

  .tagline {
    text-align: center;
    color: var(--color-text-muted);
    font-style: italic;
    margin-bottom: var(--spacing-xl);
  }

  .welcome-text {
    margin-bottom: var(--spacing-xl);
    line-height: 1.8;
  }

  .features {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .feature {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-sm);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
  }

  .feature-icon {
    font-size: var(--font-size-xl);
  }

  /* Provider selection */
  .provider-options {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
  }

  .provider-option {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: var(--spacing-lg);
    background: var(--color-bg-tertiary);
    border: 2px solid var(--color-border-primary);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    text-align: left;
  }

  .provider-option:hover {
    border-color: var(--color-accent-primary);
  }

  .provider-option.selected {
    border-color: var(--color-accent-highlight);
    background: var(--color-bg-elevated);
  }

  .provider-name {
    font-family: var(--font-display);
    font-size: var(--font-size-lg);
    color: var(--color-text-accent);
  }

  .provider-desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    margin-top: var(--spacing-xs);
  }

  /* API Key */
  .apikey-form {
    margin-top: var(--spacing-lg);
  }

  .apikey-form label {
    display: block;
    margin-bottom: var(--spacing-sm);
    color: var(--color-text-secondary);
  }

  .apikey-form input {
    width: 100%;
    margin-bottom: var(--spacing-md);
  }

  .get-key-link {
    display: inline-block;
    font-size: var(--font-size-sm);
  }

  .security-note {
    margin-top: var(--spacing-xl);
    padding: var(--spacing-md);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  .ollama-note {
    margin-top: var(--spacing-lg);
    padding: var(--spacing-md);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
  }

  /* Test connection */
  .test-button {
    display: block;
    width: 100%;
    padding: var(--spacing-lg);
    margin-top: var(--spacing-lg);
    font-size: var(--font-size-lg);
  }

  .test-result {
    margin-top: var(--spacing-lg);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
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

  .result-icon {
    font-size: var(--font-size-xl);
  }

  .latency {
    color: var(--color-text-muted);
  }

  /* Model selection */
  .model-config {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
    margin-top: var(--spacing-lg);
  }

  .model-role {
    padding: var(--spacing-lg);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
  }

  .model-role h3 {
    font-size: var(--font-size-lg);
    margin-bottom: var(--spacing-xs);
  }

  .role-desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    margin-bottom: var(--spacing-md);
  }

  .model-role select {
    width: 100%;
  }

  .models-tip {
    margin-top: var(--spacing-lg);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  /* Complete */
  .complete-step {
    text-align: center;
  }

  .complete-icon {
    font-size: 4rem;
    margin: var(--spacing-xl) 0;
  }

  .summary {
    margin-top: var(--spacing-xl);
    padding: var(--spacing-lg);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-md);
    text-align: left;
  }

  .summary-item {
    display: flex;
    justify-content: space-between;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--color-border-primary);
  }

  .summary-item:last-child {
    border-bottom: none;
  }

  .summary-item .label {
    color: var(--color-text-secondary);
  }

  .summary-item .value {
    color: var(--color-text-accent);
  }

  /* Navigation */
  .step-navigation {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: var(--spacing-lg);
    border-top: 1px solid var(--color-border-primary);
  }

  .nav-right {
    display: flex;
    gap: var(--spacing-md);
  }

  .nav-btn {
    padding: var(--spacing-sm) var(--spacing-xl);
  }

  .nav-btn.primary {
    background: var(--color-accent-highlight);
    color: var(--color-bg-primary);
  }

  .nav-btn.secondary {
    background: var(--color-bg-tertiary);
  }

  .nav-btn.text {
    background: none;
    border: none;
    color: var(--color-text-muted);
  }

  .nav-btn.text:hover {
    color: var(--color-text-primary);
  }
</style>
