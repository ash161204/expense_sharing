import { useApi } from '../api'
import type { Expense, Share, User } from '../types'
import ExpenseForm from './ExpenseForm'

type Props = { groupId: number; members: User[] }

function people(shares: Share[]) {
  return shares.map((share) => `${share.name} ₹${share.amount}`).join(' · ')
}

export default function ExpensesTab({ groupId, members }: Props) {
  const [expenses, reload] = useApi<Expense[]>(`/groups/${groupId}/expenses`)

  if (members.length === 0) {
    return <p className="card muted">Add members first (Members tab), then you can add expenses.</p>
  }

  return (
    <>
      <ExpenseForm groupId={groupId} members={members} onSaved={reload} />

      <section className="card">
        <h2>History</h2>
        {expenses?.length === 0 && <p className="muted">No expenses yet.</p>}
        {expenses?.map((expense) => (
          <article key={expense.id} className="expense">
            <div className="expense-head">
              <strong>{expense.description}</strong>
              <strong>₹{expense.amount}</strong>
            </div>
            <p className="muted">
              {new Date(expense.created_at).toLocaleString()} · {expense.split_type === 'equal' ? 'split equally' : 'split by item'}
            </p>
            <p>Paid by: {people(expense.payers)}</p>
            <p>Shares: {people(expense.splits)}</p>
            {expense.items.map((item, index) => (
              <p key={index} className="muted">
                {item.name} ₹{item.amount}: {item.shared_by.map((share) => share.name).join(', ')}
              </p>
            ))}
          </article>
        ))}
      </section>
    </>
  )
}
