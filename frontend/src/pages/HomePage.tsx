import { api, useApi } from '../api'
import AddForm from '../components/AddForm'
import type { Group, User } from '../types'

export default function HomePage() {
  const [users, reloadUsers] = useApi<User[]>('/users')
  const [groups, reloadGroups] = useApi<Group[]>('/groups')

  async function addUser(name: string) {
    await api.post('/users', { name })
    reloadUsers()
  }

  async function addGroup(name: string) {
    const group = await api.post<Group>('/groups', { name })
    reloadGroups()
    window.location.hash = `#/groups/${group.id}/members` // next step: add people to it
  }

  return (
    <main>
      <section className="card">
        <h2>Groups</h2>
        {groups?.length === 0 && <p className="muted">No groups yet.</p>}
        <ul className="list">
          {groups?.map((group) => (
            <li key={group.id}>
              <a href={`#/groups/${group.id}`}>{group.name}</a>
            </li>
          ))}
        </ul>
        <AddForm placeholder="New group, e.g. Goa Trip" onAdd={addGroup} />
      </section>

      <section className="card">
        <h2>People</h2>
        {users?.length === 0 && <p className="muted">No people yet. Add everyone who shares expenses.</p>}
        <ul className="list">
          {users?.map((user) => <li key={user.id}>{user.name}</li>)}
        </ul>
        <AddForm placeholder="New person, e.g. Mohit" onAdd={addUser} />
      </section>
    </main>
  )
}
