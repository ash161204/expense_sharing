import type { User } from '../types'

type Props = { members: User[]; selected: number[]; onChange: (selected: number[]) => void }

/** Tap names to choose who shares something. */
export default function PeoplePicker({ members, selected, onChange }: Props) {
  function toggle(userId: number) {
    onChange(selected.includes(userId) ? selected.filter((id) => id !== userId) : [...selected, userId])
  }

  return (
    <div className="chips">
      {members.map((member) => (
        <label key={member.id} className={selected.includes(member.id) ? 'chip on' : 'chip'}>
          <input type="checkbox" checked={selected.includes(member.id)} onChange={() => toggle(member.id)} />
          {member.name}
        </label>
      ))}
    </div>
  )
}
