import { useEffect, useState } from 'react'
import { logout, savedLogin } from './api'
import GroupPage from './pages/GroupPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'

/** The page is chosen from the URL hash: "#/" is home, "#/groups/1/balances" is a group tab. */
function useHash() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return hash
}

export default function App() {
  const hash = useHash()
  const login = savedLogin()
  const groupPage = hash.match(/^#\/groups\/(\d+)\/?(\w*)/) // [whole match, group id, tab]

  return (
    <div className="app">
      <header>
        <a href="#/" className="logo">Split</a>
        <nav>
          <a href="/api/docs" target="_blank">API docs</a>
          <a href="/admin/" target="_blank">Admin</a>
          {login && <button className="link" onClick={logout} title={`Logged in as ${login.user.name}`}>Log out</button>}
        </nav>
      </header>
      {!login ? (
        <LoginPage />
      ) : groupPage ? (
        <GroupPage groupId={Number(groupPage[1])} tab={groupPage[2] || 'expenses'} me={login.user} />
      ) : (
        <HomePage />
      )}
    </div>
  )
}
