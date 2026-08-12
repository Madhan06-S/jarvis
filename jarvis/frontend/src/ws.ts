export interface JarvisSocket {
  send(data: Record<string, unknown>): void;
  onMessage(handler: (msg: Record<string, unknown>) => void): void;
  onConnectionChange(handler: (connected: boolean) => void): void;
  close(): void;
  isConnected(): boolean;
}

export function createSocket(url: string): JarvisSocket {
  let ws: WebSocket | null = null;
  let connecting = false;
  let connected = false;
  let reconnectDelay = 1000;
  const maxDelay = 30000;
  
  const messageHandlers: ((msg: Record<string, unknown>) => void)[] = [];
  const connectionHandlers: ((c: boolean) => void)[] = [];

  const connect = () => {
    if (connecting || connected) return;
    connecting = true;
    
    ws = new WebSocket(url);
    
    ws.onopen = () => {
      connecting = false;
      connected = true;
      reconnectDelay = 1000;
      connectionHandlers.forEach(h => h(true));
    };
    
    ws.onclose = () => {
      connecting = false;
      if (connected) {
        connected = false;
        connectionHandlers.forEach(h => h(false));
      }
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, maxDelay);
    };
    
    ws.onerror = (err) => {
      console.error("WebSocket error", err);
      ws?.close();
    };
    
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        messageHandlers.forEach(h => h(msg));
      } catch (err) {}
    };
  };
  
  connect();
  
  return {
    send: (data) => {
      if (connected && ws) ws.send(JSON.stringify(data));
    },
    onMessage: (h) => messageHandlers.push(h),
    onConnectionChange: (h) => connectionHandlers.push(h),
    close: () => { if (ws) { ws.onclose = null; ws.close(); } },
    isConnected: () => connected
  };
}
