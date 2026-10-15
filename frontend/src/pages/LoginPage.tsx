import { useState, type FormEvent } from 'react'
import { api, errorText, saveLogin, type Login } from '../api'

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    try {
      saveLogin(await api.post<Login>(`/auth/${mode}`, { name, password }))
      window.location.reload()
    } catch (failure) {
      setError(errorText(failure))
    }
  }

  return (
    <main>
      <form className="card login" onSubmit={submit}>
        <h1>{mode === 'login' ? 'Log in' : 'Create your account'}</h1>
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name, e.g. Mohit" />
        <input value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" />
        {error && <p className="error">{error}</p>}
        <button className="primary">{mode === 'login' ? 'Log in' : 'Sign up'}</button>
        <button type="button" className="link" onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}>
          {mode === 'login' ? 'New here? Create an account' : 'Already have an account? Log in'}
        </button>
        {mode === 'login' && <p className="muted">Trying the demo? Log in as Mohit / demo1234.</p>}
        {mode === 'signup' && (
          <p className="muted">If a friend already added you by name, sign up with that same name to use it.</p>
        )}
      </form>
    </main>
  )
}
