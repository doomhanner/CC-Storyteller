/**
 * Svelte stores for CC-Storyteller.
 */

import { writable, derived } from 'svelte/store';

// ==================== Theme Store ====================

function createThemeStore() {
  // Try to load from localStorage
  const stored = typeof localStorage !== 'undefined'
    ? localStorage.getItem('cc-storyteller-theme')
    : null;

  const { subscribe, set, update } = writable(stored || 'chronicle');

  return {
    subscribe,
    set: (value) => {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('cc-storyteller-theme', value);
      }
      set(value);
    },
    toggle: () => {
      update(current => {
        const next = current === 'chronicle' ? 'eldritch' : 'chronicle';
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem('cc-storyteller-theme', next);
        }
        return next;
      });
    },
  };
}

export const theme = createThemeStore();

// ==================== Settings Store ====================

function createSettingsStore() {
  const { subscribe, set, update } = writable({
    providers: {
      storyteller: { type: 'anthropic', model: 'claude-sonnet-4-20250514' },
      archivist: { type: 'anthropic', model: 'claude-sonnet-4-20250514' },
    },
    local: { url: 'http://localhost:11434', type: 'ollama' },
    paths: { data_dir: '~/.cc-storyteller', campaigns_dir: 'campaigns' },
    ui: { theme: 'chronicle' },
    debug: { enabled: false, log_prompts: false, log_responses: false },
    available_providers: [],
    loaded: false,
  });

  return {
    subscribe,
    set,
    update,
    load: (data) => {
      update(current => ({ ...current, ...data, loaded: true }));
    },
    updateProviders: (providers) => {
      update(current => ({ ...current, providers }));
    },
    updateLocal: (local) => {
      update(current => ({ ...current, local }));
    },
    updateDebug: (debug) => {
      update(current => ({ ...current, debug }));
    },
  };
}

export const settings = createSettingsStore();

// ==================== Campaigns Store ====================

function createCampaignsStore() {
  const { subscribe, set, update } = writable({
    campaigns: [],
    total: 0,
    loading: false,
    error: null,
  });

  return {
    subscribe,
    set,
    update,
    setLoading: (loading) => update(s => ({ ...s, loading, error: null })),
    setError: (error) => update(s => ({ ...s, error, loading: false })),
    setCampaigns: (campaigns, total) => update(s => ({
      ...s,
      campaigns,
      total,
      loading: false,
      error: null
    })),
    addCampaign: (campaign) => update(s => ({
      ...s,
      campaigns: [campaign, ...s.campaigns],
      total: s.total + 1,
    })),
    removeCampaign: (id) => update(s => ({
      ...s,
      campaigns: s.campaigns.filter(c => c.id !== id),
      total: s.total - 1,
    })),
  };
}

export const campaigns = createCampaignsStore();

// ==================== Session Store ====================

function createSessionStore() {
  const { subscribe, set, update } = writable({
    id: null,
    campaignId: null,
    currentTurn: 0,
    isActive: false,
    narrative: [],
    loading: false,
    error: null,
  });

  return {
    subscribe,
    set,
    update,
    start: (session, openingNarrative) => set({
      id: session.id,
      campaignId: session.campaign_id,
      currentTurn: session.current_turn,
      isActive: true,
      narrative: [{ type: 'narrator', text: openingNarrative }],
      loading: false,
      error: null,
    }),
    addNarrative: (text, type = 'narrator') => update(s => ({
      ...s,
      narrative: [...s.narrative, { type, text }],
    })),
    addPlayerInput: (text) => update(s => ({
      ...s,
      narrative: [...s.narrative, { type: 'player', text }],
    })),
    setTurn: (turn) => update(s => ({ ...s, currentTurn: turn })),
    setLoading: (loading) => update(s => ({ ...s, loading })),
    setError: (error) => update(s => ({ ...s, error, loading: false })),
    end: () => set({
      id: null,
      campaignId: null,
      currentTurn: 0,
      isActive: false,
      narrative: [],
      loading: false,
      error: null,
    }),
  };
}

export const session = createSessionStore();

// ==================== Notifications Store ====================

function createNotificationsStore() {
  const { subscribe, update } = writable([]);

  let nextId = 1;

  return {
    subscribe,
    add: (message, type = 'info', duration = 5000) => {
      const id = nextId++;
      const notification = { id, message, type };

      update(n => [...n, notification]);

      if (duration > 0) {
        setTimeout(() => {
          update(n => n.filter(item => item.id !== id));
        }, duration);
      }

      return id;
    },
    remove: (id) => {
      update(n => n.filter(item => item.id !== id));
    },
    success: (message, duration) => {
      return createNotificationsStore().add(message, 'success', duration);
    },
    error: (message, duration) => {
      return createNotificationsStore().add(message, 'error', duration);
    },
    warning: (message, duration) => {
      return createNotificationsStore().add(message, 'warning', duration);
    },
  };
}

export const notifications = createNotificationsStore();
