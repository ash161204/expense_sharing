import { useState, type FormEvent } from 'react'
import { api, errorText } from '../api'
import type { Draft, User } from '../types'
import PeoplePicker from './PeoplePicker'

type Payer = { userId: number; amount: string }
type Item = { name: string; amount: string; sharedBy: number[] }

// `initial` pre-fills the form with the AI assistant's draft (its Edit button).
type Props = { groupId: number; members: User[]; onSaved: () => void; initial?: Draft }

export default function ExpenseForm({ groupId, members, onSaved, initial }: Props) {
  const everyone = members.map((member) => member.id)
  const draftPayers = initial?.payers.map((payer) => ({ userId: payer.user_id, amount: payer.amount })) ?? []
  const draftItems = initial?.items?.map((item) => ({ name: item.name, amount: item.amount, sharedBy: item.shared_by })) ?? []

  const [description, setDescription] = useState(initial?.description ?? '')
  const [amount, setAmount] = useState(initial?.amount ?? '')
  const [payers, setPayers] = useState<Payer[]>(draftPayers.length ? draftPayers : [{ userId: everyone[0], amount: '' }])
  const [splitType, setSplitType] = useState<'equal' | 'itemized'>(draftItems.length ? 'itemized' : 'equal')
  const [participants, setParticipants] = useState(initial?.participant_ids ?? everyone)
  const [items, setItems] = useState<Item[]>(draftItems.length ? draftItems : [{ name: '', amount: '', sharedBy: everyone }])
  const [error, setError] = useState('')

  function updatePayer(index: number, changes: Partial<Payer>) {
    setPayers(payers.map((payer, i) => (i === index ? { ...payer, ...changes } : payer)))
  }

  function updateItem(index: number, changes: Partial<Item>) {
    setItems(items.map((item, i) => (i === index ? { ...item, ...changes } : item)))
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    const body = {
      description,
      amount,
      split_type: splitType,
      // With one payer, they paid the whole amount.
      payers: payers.map((payer) => ({ user_id: payer.userId, amount: payers.length === 1 ? amount : payer.amount })),
      ...(splitType === 'equal'
        ? { participant_ids: participants }
        : { items: items.map((item) => ({ name: item.name, amount: item.amount, shared_by: item.sharedBy })) }),
    }
    try {
      await api.post(`/groups/${groupId}/expenses`, body)
      setDescription('')
      setAmount('')
      setPayers([{ userId: everyone[0], amount: '' }])
      setItems([{ name: '', amount: '', sharedBy: everyone }])
      setError('')
      onSaved()
    } catch (failure) {
      setError(errorText(failure))
    }
  }

  return (
    <form className="card" onSubmit={save}>
      <h2>{initial ? 'Edit the draft' : 'Add an expense'}</h2>
      <div className="row">
        <input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What was it? e.g. Dinner" />
        <input value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="₹ Amount" inputMode="decimal" className="money" />
      </div>

      <h3>Paid by</h3>
      {payers.map((payer, index) => (
        <div className="row" key={index}>
          <select value={payer.userId} onChange={(event) => updatePayer(index, { userId: Number(event.target.value) })}>
            {members.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
          </select>
          {payers.length > 1 && (
            <input value={payer.amount} onChange={(event) => updatePayer(index, { amount: event.target.value })} placeholder="₹ Paid" inputMode="decimal" className="money" />
          )}
        </div>
      ))}
      <button type="button" className="link" onClick={() => setPayers([...payers, { userId: everyone[0], amount: '' }])}>
        + Someone else also paid
      </button>

      <h3>Split</h3>
      <div className="toggle">
        <button type="button" className={splitType === 'equal' ? 'on' : ''} onClick={() => setSplitType('equal')}>Equally</button>
        <button type="button" className={splitType === 'itemized' ? 'on' : ''} onClick={() => setSplitType('itemized')}>By item</button>
      </div>

      {splitType === 'equal' ? (
        <PeoplePicker members={members} selected={participants} onChange={setParticipants} />
      ) : (
        <>
          {items.map((item, index) => (
            <div className="item" key={index}>
              <div className="row">
                <input value={item.name} onChange={(event) => updateItem(index, { name: event.target.value })} placeholder="Item, e.g. Pizza" />
                <input value={item.amount} onChange={(event) => updateItem(index, { amount: event.target.value })} placeholder="₹" inputMode="decimal" className="money" />
              </div>
              <PeoplePicker members={members} selected={item.sharedBy} onChange={(sharedBy) => updateItem(index, { sharedBy })} />
            </div>
          ))}
          <button type="button" className="link" onClick={() => setItems([...items, { name: '', amount: '', sharedBy: everyone }])}>
            + Add item
          </button>
        </>
      )}

      {error && <p className="error">{error}</p>}
      <button className="primary">Save expense</button>
    </form>
  )
}
