export interface JarvisSocket {
  send(data: Record<string, unknown>): void;
  onMessage(handler: (msg: Record<string, unknown>) => void): void;
  onConnectionChange(handler: (connected: boolean) => void): void;
  close(): void;
  isConnected(): boolean;
}

const THROTTLE_TYPES = new Set([
  'process_update',
  'build_log',
  'code_stream_chunk',
  'builder_status',
]);

const BATCH_MS = 32;
const MAX_QUEUE = 64;

export function createSocket(url: string): JarvisSocket {
  let ws: WebSocket | null = null;
  let connecting = false;
  let connected = false;
  let reconnectDelay = 1000;
  const maxDelay = 30000;

  const messageHandlers: ((msg: Record<string, unknown>) => void)[] = [];
  const connectionHandlers: ((c: boolean) => void)[] = [];

  let inboundQueue: Record<string, unknown>[] = [];
  let flushScheduled = false;
  let lastProcessUpdate = '';

  const flushQueue = () => {
    flushScheduled = false;
    if (inboundQueue.length === 0) return;

    const batch = inboundQueue;
    inboundQueue = [];

    for (const msg of batch) {
      messageHandlers.forEach((h) => h(msg));
    }
  };

  const scheduleFlush = () => {
    if (flushScheduled) return;
    flushScheduled = true;
    setTimeout(flushQueue, BATCH_MS);
  };

  const enqueue = (msg: Record<string, unknown>) => {
    const type = String(msg.type || '');

    if (type === 'process_update' && typeof msg.message === 'string') {
      const text = msg.message as string;
      if (text === lastProcessUpdate) return;
      lastProcessUpdate = text;
    }

    if (THROTTLE_TYPES.has(type)) {
      if (inboundQueue.length >= MAX_QUEUE) {
        inboundQueue = inboundQueue.filter((m) => !THROTTLE_TYPES.has(String(m.type || '')));
      }
      inboundQueue.push(msg);
      scheduleFlush();
      return;
    }

    messageHandlers.forEach((h) => h(msg));
  };

  const connect = () => {
    if (connecting || connected) return;
    connecting = true;

    const token = localStorage.getItem('jarvis_token') || '';
    let finalUrl = url;
    if (token && !finalUrl.includes('token=')) {
      finalUrl += (finalUrl.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(token);
    }

    try {
      ws = token ? new WebSocket(finalUrl, [`bearer.${token}`]) : new WebSocket(finalUrl);
    } catch {
      ws = new WebSocket(finalUrl);
    }

    ws.onopen = () => {
      connecting = false;
      connected = true;
      reconnectDelay = 1000;
      connectionHandlers.forEach((h) => h(true));
    };

    ws.onclose = (event) => {
      connecting = false;
      if (connected) {
        connected = false;
        connectionHandlers.forEach((h) => h(false));
      }
      if (event.code === 4001 || event.code === 1008) {
        console.warn("[WS Auth] Connection rejected (Unauthorized Token)");
        window.dispatchEvent(new CustomEvent("jarvis_auth_failed"));
        return;
      }
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, maxDelay);
    };

    ws.onerror = () => {
      ws?.close();
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        enqueue(msg);
      } catch {
        /* ignore malformed */
      }
    };
  };

  connect();

  return {
    send: (data) => {
      if (connected && ws) ws.send(JSON.stringify(data));
    },
    onMessage: (h) => messageHandlers.push(h),
    onConnectionChange: (h) => connectionHandlers.push(h),
    close: () => {
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    },
    isConnected: () => connected,
  };
}
