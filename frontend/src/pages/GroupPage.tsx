import { useApi } from '../api'
import AssistantTab from '../components/AssistantTab'
import BalancesTab from '../components/BalancesTab'
import ExpensesTab from '../components/ExpensesTab'
import MembersTab from '../components/MembersTab'
import type { Group, User } from '../types'

const TABS = [['assistant', '✦ AI'], ['expenses', 'Expenses'], ['balances', 'Balances'], ['members', 'Members']]

type Props = { groupId: number; tab: string; me: User }

export default function GroupPage({ groupId, tab, me }: Props) {
  const [group] = useApi<Group>(`/groups/${groupId}`)
  const [members, reloadMembers] = useApi<User[]>(`/groups/${groupId}/members`)

  if (!group || !members) {
    return <main><p className="muted">Loading…</p></main>
  }

  return (
    <main>
      <a href="#/" className="back">← All groups</a>
      <div className="title">
        <h1>{group.name}</h1>
        <a href={`/api/groups/${groupId}/pdf`} download>⬇ PDF</a>
      </div>
      <nav className="tabs">
        {TABS.map(([name, label]) => (
          <a key={name} href={`#/groups/${groupId}/${name}`} className={name === tab ? 'active' : ''}>
            {label}
          </a>
        ))}
      </nav>

      {tab === 'assistant' && <AssistantTab groupId={groupId} members={members} me={me} />}
      {tab === 'expenses' && <ExpensesTab groupId={groupId} members={members} />}
      {tab === 'balances' && <BalancesTab groupId={groupId} members={members} />}
      {tab === 'members' && <MembersTab groupId={groupId} members={members} onChange={reloadMembers} />}
    </main>
  )
}
