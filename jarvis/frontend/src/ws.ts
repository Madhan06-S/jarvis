export interface JarvisSocket {
  send(data: Record<string, unknown>): void;
  onMessage(handler: (msg: Record<string, unknown>) => void): void;
  onConnectionChange(handler: (connected: boolean) => void): void;
  close(): void;
  isConnected(): boolean;
  getUrl(): string;
  getReadyState(): number;
  getReadyStateText(): string;
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
  let activeUrl = url;
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
    activeUrl = url.split('?')[0];

    console.log(`[WS Init] Connecting WebSocket to: ${activeUrl}`);

    try {
      ws = token ? new WebSocket(activeUrl, ['bearer', token]) : new WebSocket(activeUrl);
    } catch {
      ws = new WebSocket(activeUrl);
    }

    ws.onopen = () => {
      connecting = false;
      connected = true;
      reconnectDelay = 1000;
      console.log(`[WS Open] Connected to ${activeUrl}. readyState: ${ws?.readyState}`);
      connectionHandlers.forEach((h) => h(true));
    };

    ws.onclose = (event) => {
      connecting = false;
      if (connected) {
        connected = false;
        connectionHandlers.forEach((h) => h(false));
      }
      console.warn(`[WS Close] Socket closed (code: ${event.code}, reason: '${event.reason}')`);
      if (event.code === 4001 || event.code === 1008) {
        console.warn("[WS Auth] Connection rejected (Unauthorized Token)");
        window.dispatchEvent(new CustomEvent("jarvis_auth_failed"));
        return;
      }
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, maxDelay);
    };

    ws.onerror = (e) => {
      console.error("[WS Error] Socket error occurred:", e);
      ws?.close();
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        console.log(`[WS Inbound] Received message (type: '${msg.type || 'unknown'}')`);
        enqueue(msg);
      } catch {
        /* ignore malformed */
      }
    };
  };

  connect();

  return {
    send: (data) => {
      const readyStateCode = ws ? ws.readyState : 3;
      const stateStr = ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][readyStateCode] || String(readyStateCode);
      const sizeInfo = data.type === 'audio_input' && typeof data.data === 'string'
        ? ` | Payload: ${data.data.length} b64 chars`
        : '';
      console.log(`[WS Outbound] Sending '${data.type}'${sizeInfo} | readyState: ${stateStr} (${readyStateCode}) | URL: ${activeUrl}`);
      if (connected && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
      } else {
        console.warn(`[WS Outbound] Dropped '${data.type}' — Socket not in OPEN state (current state: ${stateStr})`);
      }
    },
    onMessage: (h) => messageHandlers.push(h),
    onConnectionChange: (h) => connectionHandlers.push(h),
    close: () => {
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    },
    isConnected: () => connected && ws?.readyState === WebSocket.OPEN,
    getUrl: () => activeUrl,
    getReadyState: () => ws ? ws.readyState : 3,
    getReadyStateText: () => ws ? (['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][ws.readyState] || String(ws.readyState)) : 'CLOSED',
  };
}
