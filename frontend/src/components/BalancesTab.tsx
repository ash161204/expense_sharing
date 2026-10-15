import { useState, type FormEvent } from 'react'
import { api, errorText, useApi } from '../api'
import type { Balances, Settlement, User } from '../types'

type Props = { groupId: number; members: User[] }

/** "-400.00" -> "-₹400.00", "400.00" -> "₹400.00" */
function rupees(amount: string) {
  return amount.startsWith('-') ? `-₹${amount.slice(1)}` : `₹${amount}`
}

export default function BalancesTab({ groupId, members }: Props) {
  const [balances, reloadBalances] = useApi<Balances>(`/groups/${groupId}/balances`)
  const [settlements, reloadSettlements] = useApi<Settlement[]>(`/groups/${groupId}/settlements`)
  const [form, setForm] = useState({ from: '', to: '', amount: '' })
  const [error, setError] = useState('')

  const idOf = (name: string) => members.find((member) => member.name === name)?.id

  async function settle(fromUserId: number | undefined, toUserId: number | undefined, amount: string) {
    try {
      await api.post(`/groups/${groupId}/settlements`, { from_user_id: fromUserId, to_user_id: toUserId, amount })
      setForm({ from: '', to: '', amount: '' })
      setError('')
      reloadBalances()
      reloadSettlements()
    } catch (failure) {
      setError(errorText(failure))
    }
  }

  function recordPayment(event: FormEvent) {
    event.preventDefault()
    settle(Number(form.from), Number(form.to), form.amount)
  }

  if (!balances) {
    return <p className="muted">Loading…</p>
  }

  // {"Rahul": {"owes": {"Mohit": "400.00"}}} -> [["Rahul", "Mohit", "400.00"]]
  const payments = Object.entries(balances.owes).flatMap(([debtor, { owes }]) =>
    Object.entries(owes).map(([creditor, amount]) => [debtor, creditor, amount]),
  )

  return (
    <>
      <section className="card">
        <h2>Who owes whom</h2>
        {payments.length === 0 && <p className="muted">Everyone is settled up.</p>}
        {payments.map(([debtor, creditor, amount]) => (
          <div className="row owe" key={debtor + creditor}>
            <span><strong>{debtor}</strong> owes <strong>{creditor}</strong> ₹{amount}</span>
            <button onClick={() => settle(idOf(debtor), idOf(creditor), amount)}>Settle</button>
          </div>
        ))}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <h2>Everyone's balance</h2>
        <table>
          <thead>
            <tr><th>Name</th><th>Paid</th><th>Share</th><th>Net</th></tr>
          </thead>
          <tbody>
            {balances.members.map((member) => (
              <tr key={member.user_id}>
                <td>{member.name}</td>
                <td>₹{member.paid}</td>
                <td>₹{member.share}</td>
                <td className={Number(member.net) < 0 ? 'negative' : Number(member.net) > 0 ? 'positive' : ''}>{rupees(member.net)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">Net above 0: gets money back. Below 0: owes money.</p>
      </section>

      <form className="card" onSubmit={recordPayment}>
        <h2>Record a payment</h2>
        <div className="row">
          <select value={form.from} onChange={(event) => setForm({ ...form, from: event.target.value })}>
            <option value="">Who paid?</option>
            {members.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
          </select>
          <select value={form.to} onChange={(event) => setForm({ ...form, to: event.target.value })}>
            <option value="">To whom?</option>
            {members.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
          </select>
        </div>
        <div className="row">
          <input value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} placeholder="₹ Amount" inputMode="decimal" />
          <button disabled={!form.from || !form.to}>Record</button>
        </div>
      </form>

      <section className="card">
        <h2>Payments made</h2>
        {settlements?.length === 0 && <p className="muted">No payments yet.</p>}
        <ul className="list">
          {settlements?.map((settlement) => (
            <li key={settlement.id}>
              {settlement.from_user} paid {settlement.to_user} ₹{settlement.amount}
              <span className="muted"> · {new Date(settlement.created_at).toLocaleDateString()}</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
