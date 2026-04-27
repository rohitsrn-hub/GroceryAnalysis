const API_KEY = process.env.REACT_APP_API_KEY;

export const apiFetch = (url, options = {}) => {
  if (!API_KEY) return fetch(url, options);
  const { headers = {}, ...rest } = options;
  return fetch(url, { ...rest, headers: { ...headers, 'X-API-Key': API_KEY } });
};
