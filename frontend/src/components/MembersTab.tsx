import { useState, type FormEvent } from 'react'
import { api, errorText, useApi } from '../api'
import type { User } from '../types'

type Props = { groupId: number; members: User[]; onChange: () => void }

export default function MembersTab({ groupId, members, onChange }: Props) {
  const [users] = useApi<User[]>('/users')
  const [userId, setUserId] = useState('')
  const [error, setError] = useState('')

  const notInGroup = (users ?? []).filter((user) => !members.some((member) => member.id === user.id))

  async function addMember(event: FormEvent) {
    event.preventDefault()
    try {
      await api.post(`/groups/${groupId}/members`, { user_id: Number(userId) })
      setUserId('')
      setError('')
      onChange()
    } catch (failure) {
      setError(errorText(failure))
    }
  }

  return (
    <section className="card">
      <h2>Members</h2>
      {members.length === 0 && <p className="muted">No members yet.</p>}
      <ul className="list">
        {members.map((member) => <li key={member.id}>{member.name}</li>)}
      </ul>

      <form onSubmit={addMember}>
        <div className="row">
          <select value={userId} onChange={(event) => setUserId(event.target.value)}>
            <option value="">Choose a person…</option>
            {notInGroup.map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}
          </select>
          <button disabled={!userId}>Add</button>
        </div>
        {error && <p className="error">{error}</p>}
      </form>
      {users && notInGroup.length === 0 && (
        <p className="muted">Everyone is already in this group. Add new people on the <a href="#/">home page</a>.</p>
      )}
    </section>
  )
}
