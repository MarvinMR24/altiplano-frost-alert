import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';

interface AsyncState<T> {
  data: T | undefined;
  error: unknown;
  loading: boolean;
  reload: () => void;
  setData: (data: T) => void;
}

// Loads `fn` on mount and whenever `deps` change; optionally again when the screen gains focus.
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], options?: { refetchOnFocus?: boolean }): AsyncState<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const callId = useRef(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const run = useCallback(() => {
    const id = ++callId.current;
    setLoading(true);
    setError(null);
    fnRef
      .current()
      .then((result) => {
        if (id === callId.current) setData(result);
      })
      .catch((err: unknown) => {
        if (id === callId.current) setError(err);
      })
      .finally(() => {
        if (id === callId.current) setLoading(false);
      });
  }, []);

  useEffect(run, deps);

  const firstFocus = useRef(true);
  useFocusEffect(
    useCallback(() => {
      if (firstFocus.current) {
        firstFocus.current = false;
        return;
      }
      if (options?.refetchOnFocus) run();
    }, [options?.refetchOnFocus, run]),
  );

  return { data, error, loading, reload: run, setData };
}
