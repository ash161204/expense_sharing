import { useState, type FormEvent } from 'react'
import { errorText } from '../api'

type Props = { placeholder: string; onAdd: (name: string) => Promise<void> }

/** A one-field form ("New person", "New group") that shows the API's error message if it fails. */
export default function AddForm({ placeholder, onAdd }: Props) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    try {
      await onAdd(name)
      setName('')
      setError('')
    } catch (failure) {
      setError(errorText(failure))
    }
  }

  return (
    <form onSubmit={submit}>
      <div className="row">
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder={placeholder} />
        <button>Add</button>
      </div>
      {error && <p className="error">{error}</p>}
    </form>
  )
}
