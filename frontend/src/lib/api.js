/**
 * API client for CC-Storyteller backend.
 */

const API_BASE = '/api';

/**
 * Make an API request.
 * @param {string} endpoint - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<any>} Response data
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'API request failed');
  }

  return response.json();
}

// ==================== Settings API ====================

export const settingsApi = {
  /**
   * Get current settings.
   * @returns {Promise<object>} Settings object
   */
  async get() {
    return request('/settings');
  },

  /**
   * Update settings.
   * @param {object} updates - Partial settings to update
   * @returns {Promise<object>} Updated settings
   */
  async update(updates) {
    return request('/settings', {
      method: 'POST',
      body: updates,
    });
  },

  /**
   * Test a provider connection.
   * @param {object} params - Test parameters
   * @returns {Promise<object>} Test result
   */
  async testProvider(params) {
    return request('/settings/test', {
      method: 'POST',
      body: params,
    });
  },

  /**
   * Get list of available providers.
   * @returns {Promise<array>} Provider list
   */
  async getProviders() {
    return request('/settings/providers');
  },

  /**
   * Get models for a provider.
   * @param {string} providerType - Provider type
   * @returns {Promise<array>} Model list
   */
  async getModels(providerType) {
    return request(`/settings/providers/${providerType}/models`);
  },
};

// ==================== Campaigns API ====================

export const campaignsApi = {
  /**
   * List all campaigns.
   * @returns {Promise<object>} Campaign list
   */
  async list() {
    return request('/campaigns');
  },

  /**
   * Get campaign details.
   * @param {string} id - Campaign ID
   * @returns {Promise<object>} Campaign details
   */
  async get(id) {
    return request(`/campaigns/${id}`);
  },

  /**
   * Create a new campaign.
   * @param {object} data - Campaign creation data
   * @returns {Promise<object>} Created campaign
   */
  async create(data) {
    return request('/campaigns', {
      method: 'POST',
      body: data,
    });
  },

  /**
   * Delete a campaign.
   * @param {string} id - Campaign ID
   * @returns {Promise<object>} Deletion result
   */
  async delete(id) {
    return request(`/campaigns/${id}`, {
      method: 'DELETE',
    });
  },
};

// ==================== Sessions API ====================

export const sessionsApi = {
  /**
   * Start a new session.
   * @param {string} campaignId - Campaign ID
   * @returns {Promise<object>} Session info and opening narrative
   */
  async start(campaignId) {
    return request('/sessions', {
      method: 'POST',
      body: { campaign_id: campaignId },
    });
  },

  /**
   * Get session info.
   * @param {string} id - Session ID
   * @returns {Promise<object>} Session info
   */
  async get(id) {
    return request(`/sessions/${id}`);
  },

  /**
   * Process a turn (non-streaming).
   * @param {string} sessionId - Session ID
   * @param {string} input - Player input
   * @returns {Promise<object>} Turn result
   */
  async processTurn(sessionId, input) {
    return request(`/sessions/${sessionId}/turn`, {
      method: 'POST',
      body: { player_input: input },
    });
  },

  /**
   * Save session.
   * @param {string} id - Session ID
   * @returns {Promise<object>} Save result
   */
  async save(id) {
    return request(`/sessions/${id}/save`, {
      method: 'POST',
    });
  },

  /**
   * End session.
   * @param {string} id - Session ID
   * @returns {Promise<object>} End result
   */
  async end(id) {
    return request(`/sessions/${id}`, {
      method: 'DELETE',
    });
  },

  /**
   * Create WebSocket connection for streaming.
   * @param {string} sessionId - Session ID
   * @returns {WebSocket} WebSocket connection
   */
  createStream(sessionId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return new WebSocket(`${protocol}//${host}/api/sessions/${sessionId}/stream`);
  },
};

// ==================== Setup API ====================

export const setupApi = {
  /**
   * Get setup status.
   * @returns {Promise<object>} Setup status
   */
  async getStatus() {
    return request('/setup/status');
  },

  /**
   * Save API key during setup.
   * @param {string} provider - Provider type
   * @param {string} apiKey - API key
   * @returns {Promise<object>} Save result
   */
  async saveApiKey(provider, apiKey) {
    return request('/setup/api-key', {
      method: 'POST',
      body: { provider, api_key: apiKey },
    });
  },
};

// ==================== Codex API ====================

export const codexApi = {
  /**
   * List entities in a campaign.
   * @param {string} campaignId - Campaign ID
   * @param {string} entityType - Optional entity type filter
   * @returns {Promise<object>} Entity list
   */
  async listEntities(campaignId, entityType = null) {
    const params = entityType ? `?entity_type=${entityType}` : '';
    return request(`/codex/${campaignId}/entities${params}`);
  },

  /**
   * Get entity details.
   * @param {string} campaignId - Campaign ID
   * @param {string} entityId - Entity ID
   * @returns {Promise<object>} Entity details
   */
  async getEntity(campaignId, entityId) {
    return request(`/codex/${campaignId}/entities/${entityId}`);
  },

  /**
   * Get relationship graph.
   * @param {string} campaignId - Campaign ID
   * @returns {Promise<object>} Graph data
   */
  async getRelationships(campaignId) {
    return request(`/codex/${campaignId}/relationships`);
  },

  /**
   * Get bible statistics.
   * @param {string} campaignId - Campaign ID
   * @returns {Promise<object>} Stats
   */
  async getStats(campaignId) {
    return request(`/codex/${campaignId}/stats`);
  },
};
