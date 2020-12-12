import { useState, useEffect } from "react";

export const useLocalStorageState = (key, defaultValue) => {
  const [state, setState] = useState(
    () => JSON.parse(localStorage.getItem(key)) || defaultValue
  );
  useEffect(() => {
    state
      ? localStorage.setItem(key, JSON.stringify(state))
      : localStorage.removeItem(key);
  }, [key, state]);

  return [state, setState];
};
