import { useState, useEffect, useCallback } from 'react';
import visitorsService from '../services/visitorsService';

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function useWebPush() {
  const [isSupported, setIsSupported] = useState(false);
  const [permission, setPermission] = useState('default');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [loading, setLoading] = useState(true);

  // Check support on mount
  useEffect(() => {
    const supported =
      typeof window !== 'undefined' &&
      'serviceWorker' in navigator &&
      'PushManager' in window;
    setIsSupported(supported);
    if (supported) {
      setPermission(Notification.permission);
      checkSubscription();
    } else {
      setLoading(false);
    }
  }, []);

  const checkSubscription = async () => {
    try {
      const registration = await navigator.serviceWorker.ready;
      const sub = await registration.pushManager.getSubscription();
      setIsSubscribed(!!sub);
    } catch (err) {
      console.warn('Error checking push subscription:', err);
    } finally {
      setLoading(false);
    }
  };

  const subscribe = useCallback(async (flatNumber) => {
    if (!isSupported) throw new Error('Web Push is not supported in this browser.');
    if (!flatNumber) throw new Error('Flat number is required to subscribe to visitor alerts.');

    setLoading(true);
    try {
      // 1. Request permission
      const permResult = await Notification.requestPermission();
      setPermission(permResult);
      if (permResult !== 'granted') {
        throw new Error('Notification permission denied.');
      }

      // 2. Fetch VAPID key
      const { public_key: vapidKey } = await visitorsService.getVapidPublicKey();
      if (!vapidKey) {
        throw new Error('VAPID public key not configured on backend.');
      }

      // 3. Register subscription on SW
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      });

      // 4. Send subscription to backend
      await visitorsService.subscribeWebPush({
        flat_number: flatNumber,
        subscription: subscription.toJSON(),
      });

      setIsSubscribed(true);
      return true;
    } catch (err) {
      console.error('Failed to subscribe to push notifications:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [isSupported]);

  const unsubscribe = useCallback(async () => {
    if (!isSupported) return;
    setLoading(true);
    try {
      const registration = await navigator.serviceWorker.ready;
      const sub = await registration.pushManager.getSubscription();
      if (sub) {
        // 1. Send unsubscribe to backend
        await visitorsService.unsubscribeWebPush(sub.endpoint);
        // 2. Unsubscribe on browser
        await sub.unsubscribe();
      }
      setIsSubscribed(false);
      return true;
    } catch (err) {
      console.error('Failed to unsubscribe from push notifications:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [isSupported]);

  return {
    isSupported,
    permission,
    isSubscribed,
    subscribe,
    unsubscribe,
    loading,
  };
}
