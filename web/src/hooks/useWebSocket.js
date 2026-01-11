import { useEffect, useRef, useState, useCallback } from 'react';

export function useWebSocket(url) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);

  // WebSocket statistics tracking
  const statsRef = useRef({
    connectedSince: null,
    messagesSent: 0,
    messagesReceived: 0,
    reconnectCount: 0,
    lastMessageTime: null
  });
  const [stats, setStats] = useState(statsRef.current);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;

        // Track connection time
        statsRef.current.connectedSince = Date.now();
        setStats({ ...statsRef.current });
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);

          // Track received messages
          statsRef.current.messagesReceived++;
          statsRef.current.lastMessageTime = Date.now();
          setStats({ ...statsRef.current });
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Track reconnect count
        if (statsRef.current.connectedSince !== null) {
          statsRef.current.reconnectCount++;
          setStats({ ...statsRef.current });
        }

        // Reset connection time
        statsRef.current.connectedSince = null;

        // Exponential backoff for reconnection
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current++;

        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})...`);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));

      // Track sent messages
      statsRef.current.messagesSent++;
      setStats({ ...statsRef.current });

      return true;
    }
    console.warn('WebSocket not connected, message not sent:', message);
    return false;
  }, []);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    stats
  };
}
