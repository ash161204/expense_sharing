import { useCallback, useEffect, useState } from 'react'
import type { User } from './types'

// ---------- login (the token is kept in the browser) ----------

export type Login = { token: string; user: User }

export function savedLogin(): Login | null {
  return JSON.parse(localStorage.getItem('login') ?? 'null')
}

export function saveLogin(login: Login) {
  localStorage.setItem('login', JSON.stringify(login))
}

export function logout() {
  localStorage.removeItem('login')
  window.location.reload()
}

// ---------- calling the API ----------

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const isFile = body instanceof FormData // photos and voice recordings
  const token = savedLogin()?.token
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      ...(isFile ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : isFile ? body : JSON.stringify(body),
  })
  if (response.status === 401 && token) {
    logout() // the saved login expired
  }
  const data = await response.json().catch(() => ({ detail: `Server error (${response.status})` }))
  if (!response.ok) {
    throw new Error(errorMessages(data).join('\n'))
  }
  return data
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body: unknown) => request<T>('POST', path, body),
}

/** Loads a GET endpoint. Returns the data (undefined while loading) and a function to load it again. */
export function useApi<T>(path: string): [T | undefined, () => void] {
  const [data, setData] = useState<T>()
  const load = useCallback(() => {
    api.get<T>(path).then(setData)
  }, [path])
  useEffect(load, [load])
  return [data, load]
}

/** Turns Django errors like {"payers": ["Users [9] are not members of this group."]} into readable lines. */
export function errorMessages(data: unknown, field = ''): string[] {
  if (typeof data === 'string') {
    return [field ? `${field}: ${data}` : data]
  }
  if (Array.isArray(data)) {
    return data.flatMap((item) => errorMessages(item, field))
  }
  if (data && typeof data === 'object') {
    return Object.entries(data).flatMap(([key, value]) =>
      errorMessages(value, key === 'non_field_errors' || key === 'detail' ? field : key),
    )
  }
  return []
}

export function errorText(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}
