<script>
  import { onMount, onDestroy } from 'svelte';
  import { link } from 'svelte-routing';
  import { sessionsApi, campaignsApi } from '../lib/api.js';
  import { session, notifications } from '../lib/stores.js';

  export let campaignId;

  let campaign = null;
  let loading = true;
  let playerInput = '';
  let narrativeContainer;
  let ws = null;

  onMount(async () => {
    try {
      // Load campaign info
      campaign = await campaignsApi.get(campaignId);

      // Start session
      const result = await sessionsApi.start(campaignId);
      session.start(result.session, result.opening_narrative);

      // Set up WebSocket for streaming
      setupWebSocket(result.session.id);

      loading = false;
    } catch (error) {
      notifications.add(`Failed to start session: ${error.message}`, 'error');
      loading = false;
    }
  });

  onDestroy(() => {
    if (ws) {
      ws.close();
    }
  });

  function setupWebSocket(sessionId) {
    ws = sessionsApi.createStream(sessionId);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      switch (msg.type) {
        case 'chunk':
          // Append to current narrative
          session.update(s => {
            const lastEntry = s.narrative[s.narrative.length - 1];
            if (lastEntry && lastEntry.type === 'narrator' && lastEntry.streaming) {
              lastEntry.text += msg.data.text;
            }
            return s;
          });
          scrollToBottom();
          break;

        case 'done':
          session.update(s => {
            const lastEntry = s.narrative[s.narrative.length - 1];
            if (lastEntry) {
              lastEntry.streaming = false;
            }
            return s;
          });
          session.setTurn(msg.data.turn);
          session.setLoading(false);
          break;

        case 'error':
          notifications.add(`Error: ${msg.data.message}`, 'error');
          session.setLoading(false);
          break;
      }
    };

    ws.onerror = () => {
      notifications.add('WebSocket connection error', 'error');
    };
  }

  async function submitTurn() {
    if (!playerInput.trim() || $session.loading) return;

    const input = playerInput.trim();
    playerInput = '';

    // Add player input to narrative
    session.addPlayerInput(input);

    // Add placeholder for streaming response
    session.update(s => ({
      ...s,
      narrative: [...s.narrative, { type: 'narrator', text: '', streaming: true }],
      loading: true,
    }));

    scrollToBottom();

    // Send via WebSocket if connected
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'turn', input }));
    } else {
      // Fallback to REST API
      try {
        const result = await sessionsApi.processTurn($session.id, input);
        session.update(s => {
          const lastEntry = s.narrative[s.narrative.length - 1];
          if (lastEntry && lastEntry.streaming) {
            lastEntry.text = result.narrative;
            lastEntry.streaming = false;
          }
          return s;
        });
        session.setTurn(result.turn_number);
        session.setLoading(false);
        scrollToBottom();
      } catch (error) {
        notifications.add(`Failed to process turn: ${error.message}`, 'error');
        session.setLoading(false);
      }
    }
  }

  function scrollToBottom() {
    if (narrativeContainer) {
      setTimeout(() => {
        narrativeContainer.scrollTop = narrativeContainer.scrollHeight;
      }, 10);
    }
  }

  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitTurn();
    }
  }

  async function saveAndExit() {
    try {
      await sessionsApi.save($session.id);
      await sessionsApi.end($session.id);
      session.end();
      notifications.add('Session saved', 'success');
    } catch (error) {
      notifications.add(`Failed to save: ${error.message}`, 'error');
    }
  }
</script>

<div class="chronicle-page">
  {#if loading}
    <div class="loading">
      <h2>Opening the Chronicle...</h2>
      <p>Preparing your adventure</p>
    </div>
  {:else}
    <header class="chronicle-header">
      <div class="campaign-info">
        <h1>{campaign?.name || 'Chronicle'}</h1>
        <span class="turn-indicator">Turn {$session.currentTurn}</span>
      </div>
      <div class="header-actions">
        <a href="/codex/{campaignId}" use:link class="btn">Codex</a>
        <button class="btn" on:click={saveAndExit}>Save & Exit</button>
      </div>
    </header>

    <div class="narrative-container" bind:this={narrativeContainer}>
      {#each $session.narrative as entry}
        <div class="narrative-entry {entry.type}" class:streaming={entry.streaming}>
          {#if entry.type === 'player'}
            <div class="player-action">
              <span class="label">You</span>
              <p>{entry.text}</p>
            </div>
          {:else}
            <div class="narrator-text">
              {entry.text}
              {#if entry.streaming}
                <span class="cursor">▌</span>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <div class="input-area">
      <textarea
        bind:value={playerInput}
        on:keydown={handleKeydown}
        placeholder="What do you do? (Press Enter to submit)"
        disabled={$session.loading}
        rows="2"
      ></textarea>
      <button
        class="submit-btn primary"
        on:click={submitTurn}
        disabled={$session.loading || !playerInput.trim()}
      >
        {$session.loading ? '...' : 'Send'}
      </button>
    </div>

    <div class="input-help">
      <span>"dialogue"</span>
      <span>*thoughts*</span>
      <span>actions</span>
      <span>((OOC))</span>
    </div>
  {/if}
</div>

<style>
  .chronicle-page {
    display: flex;
    flex-direction: column;
    height: calc(100vh - var(--spacing-xl) * 2);
  }

  .chronicle-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--color-border-primary);
    margin-bottom: var(--spacing-md);
  }

  .campaign-info {
    display: flex;
    align-items: baseline;
    gap: var(--spacing-md);
  }

  .campaign-info h1 {
    font-size: var(--font-size-2xl);
  }

  .turn-indicator {
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
  }

  .header-actions {
    display: flex;
    gap: var(--spacing-sm);
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
    cursor: pointer;
  }

  .narrative-container {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-lg);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-lg);
    margin-bottom: var(--spacing-md);
  }

  .narrative-entry {
    margin-bottom: var(--spacing-lg);
  }

  .narrative-entry.player {
    padding-left: var(--spacing-lg);
    border-left: 3px solid var(--color-accent-highlight);
  }

  .player-action .label {
    display: block;
    font-family: var(--font-display);
    font-size: var(--font-size-sm);
    color: var(--color-accent-highlight);
    margin-bottom: var(--spacing-xs);
  }

  .player-action p {
    color: var(--color-text-secondary);
    font-style: italic;
  }

  .narrator-text {
    line-height: 1.8;
    white-space: pre-wrap;
  }

  .cursor {
    animation: blink 1s infinite;
    color: var(--color-accent-highlight);
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }

  .input-area {
    display: flex;
    gap: var(--spacing-md);
  }

  .input-area textarea {
    flex: 1;
    resize: none;
    font-family: var(--font-body);
  }

  .submit-btn {
    padding: var(--spacing-md) var(--spacing-xl);
    align-self: stretch;
  }

  .submit-btn.primary {
    background: var(--color-accent-highlight);
    color: var(--color-bg-primary);
  }

  .input-help {
    display: flex;
    gap: var(--spacing-lg);
    justify-content: center;
    margin-top: var(--spacing-sm);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
  }

  .input-help span {
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-bg-tertiary);
    border-radius: var(--radius-sm);
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
  }

  .loading h2 {
    margin-bottom: var(--spacing-sm);
  }

  .loading p {
    color: var(--color-text-muted);
  }
</style>
