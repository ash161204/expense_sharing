import { errorMessages } from '../api'
import type { AssistantReply, Draft, User } from '../types'
import PeoplePicker from './PeoplePicker'

type Props = {
  reply: AssistantReply
  members: User[]
  onChange: (draft: Draft) => void // a tap or a typed amount: the server re-checks the draft (no AI call)
  onEdit: () => void
  onConfirm: () => void
}

/** The draft so far, shown at every step. Tap names to say who had what and who paid, or answer in the chat. */
export default function DraftCard({ reply, members, onChange, onEdit, onConfirm }: Props) {
  const { draft, question, shares } = reply
  const ready = question === null && shares.length > 0
  const problems = errorMessages(reply.errors)
  const items = draft.items ?? []
  const nameOf = (userId: number) => members.find((member) => member.id === userId)?.name

  function setItemPeople(index: number, sharedBy: number[]) {
    onChange({ ...draft, items: items.map((item, i) => (i === index ? { ...item, shared_by: sharedBy } : item)) })
  }

  function setPayers(userIds: number[]) {
    const amountOf = (userId: number) => draft.payers.find((payer) => payer.user_id === userId)?.amount ?? ''
    onChange({ ...draft, payers: userIds.map((userId) => ({ user_id: userId, amount: amountOf(userId) })) })
  }

  function setPayerAmount(userId: number, amount: string) {
    onChange({ ...draft, payers: draft.payers.map((payer) => (payer.user_id === userId ? { ...payer, amount } : payer)) })
  }

  return (
    <div className="draft">
      <p className="ai-label">{ready ? '✦ AI detected' : '✦ Draft so far'}</p>
      <div className="expense-head">
        <strong>{draft.description || 'Untitled'}</strong>
        <strong>{draft.amount && `₹${draft.amount}`}</strong>
      </div>

      {items.length > 0 ? (
        <>
          <h3>Who had what</h3>
          {items.map((item, index) => (
            <div key={index} className="draft-item">
              <div className="share">
                <span>{item.name}</span>
                <span>₹{item.amount}</span>
              </div>
              <PeoplePicker members={members} selected={item.shared_by} onChange={(sharedBy) => setItemPeople(index, sharedBy)} />
            </div>
          ))}
        </>
      ) : (
        <>
          <h3>Split between</h3>
          <PeoplePicker members={members} selected={draft.participant_ids} onChange={(ids) => onChange({ ...draft, participant_ids: ids })} />
        </>
      )}

      <h3>Paid by</h3>
      <div className="payers">
        <PeoplePicker members={members} selected={draft.payers.map((payer) => payer.user_id)} onChange={setPayers} />
      </div>
      {draft.payers.length > 1 &&
        draft.payers.map((payer) => (
          <div className="row" key={payer.user_id}>
            <span>{nameOf(payer.user_id)} paid</span>
            <input
              key={payer.amount} // refreshes when the server fills it in (e.g. "the rest")
              defaultValue={payer.amount}
              onBlur={(event) => event.target.value !== payer.amount && setPayerAmount(payer.user_id, event.target.value)}
              placeholder="₹ Amount"
              inputMode="decimal"
              className="money"
            />
          </div>
        ))}

      {ready && (
        <>
          <h3>Each person's share</h3>
          {shares.map((share) => (
            <div key={share.user_id} className="share">
              <span>{share.name}</span>
              <span>₹{share.amount}</span>
            </div>
          ))}
        </>
      )}
      {question && <p className="muted">Still needed: {question}</p>}
      {problems.length > 0 && <p className="error">{problems.join('\n')}</p>}

      <div className="row">
        <button className="secondary" onClick={onEdit}>Edit</button>
        <button onClick={onConfirm} disabled={!ready}>✓ Confirm & add</button>
      </div>
    </div>
  )
}
