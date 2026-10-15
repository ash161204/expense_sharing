import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, errorMessages, errorText } from '../api'
import type { AssistantReply, Draft, User } from '../types'
import DraftCard from './DraftCard'
import ExpenseForm from './ExpenseForm'

type Message = { from: 'bot' | 'me'; text: string }

/** What the bot says about a reply: the next question, a problem to fix, or "ready". */
function replyText(reply: AssistantReply | null) {
  if (!reply) return ''
  const problems = errorMessages(reply.errors)
  if (reply.question) return reply.question
  if (problems.length) return `Almost there: ${problems.join(' ')} Tap "Edit" to fix it.`
  return "Here's the draft. Check it and add."
}

type Props = { groupId: number; members: User[]; me: User }

export default function AssistantTab({ groupId, members, me }: Props) {
  const greeting = `Hi ${me.name}! Tell me about an expense, like "I paid 1200 for dinner with everyone". You can also 📷 scan a bill or 🎤 speak.`
  const [messages, setMessages] = useState<Message[]>([{ from: 'bot', text: greeting }])
  const [reply, setReply] = useState<AssistantReply | null>(null) // the latest draft and question
  const [text, setText] = useState('')
  const [busy, setBusy] = useState('') // "Thinking…", "Reading the bill…"
  const [editing, setEditing] = useState(false)
  const [recording, setRecording] = useState<MediaRecorder | null>(null)
  const photoInput = useRef<HTMLInputElement>(null)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' }) // braces matter: an effect must not return a value
  }, [messages, busy])

  if (!members.some((member) => member.id === me.id)) {
    return <p className="card muted">Join this group first (Members tab) to use the assistant.</p>
  }

  const hasDraft = reply !== null && (reply.draft.amount !== '' || (reply.draft.items ?? []).length > 0)

  function say(from: Message['from'], text: string) {
    setMessages((current) => [...current, { from, text }])
  }

  /** One chat turn: the server updates the draft and tells us what to ask next. */
  async function send(message: string, shownAs = message) {
    say('me', shownAs)
    setBusy('Thinking…')
    try {
      const body = { draft: reply?.draft ?? null, message, question: reply?.question ?? '' }
      const next = await api.post<AssistantReply>(`/groups/${groupId}/assistant`, body)
      setReply(next)
      say('bot', replyText(next))
    } catch (failure) {
      say('bot', errorText(failure))
    }
    setBusy('')
  }

  /** A tap in the draft card: the server re-checks the draft without a message, so there is no AI call. */
  async function update(draft: Draft) {
    try {
      const next = await api.post<AssistantReply>(`/groups/${groupId}/assistant`, { draft, message: '' })
      const step = (r: AssistantReply | null) => replyText(r).split('?')[0] // "Who had what", "Who paid"...
      if (step(next) !== step(reply)) say('bot', replyText(next)) // speak only when the step changes, not on every tap
      setReply(next)
    } catch (failure) {
      say('bot', errorText(failure))
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (text.trim()) {
      send(text.trim())
      setText('')
    }
  }

  async function scanBill(file: File) {
    const form = new FormData()
    form.append('image', file)
    setBusy('Reading the bill…')
    try {
      const scanned = await api.post<{ text: string }>('/assistant/scan', form)
      await send(scanned.text, '📷 Scanned a bill')
    } catch (failure) {
      say('bot', errorText(failure))
      setBusy('')
    }
  }

  /** Tap once to record, tap again to stop. The words land in the text box so you can fix them before sending. */
  async function toggleRecording() {
    if (recording) {
      recording.stop()
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      const chunks: Blob[] = []
      recorder.ondataavailable = (event) => chunks.push(event.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop())
        setRecording(null)
        setBusy('Listening…')
        const form = new FormData()
        form.append('audio', new Blob(chunks, { type: recorder.mimeType }), 'voice.webm')
        try {
          setText((await api.post<{ text: string }>(`/groups/${groupId}/assistant/transcribe`, form)).text)
        } catch (failure) {
          say('bot', errorText(failure))
        }
        setBusy('')
      }
      recorder.start()
      setRecording(recorder)
    } catch {
      say('bot', 'The microphone is not available here. You can type instead.')
    }
  }

  async function confirm() {
    try {
      await api.post(`/groups/${groupId}/expenses`, reply!.draft)
      say('bot', '✓ Added! You can see it in the Expenses tab. Tell me about the next one.')
      setReply(null)
    } catch (failure) {
      say('bot', errorText(failure))
    }
  }

  function savedFromForm() {
    setEditing(false)
    setReply(null)
    say('bot', '✓ Saved! Tell me about the next one.')
  }

  return (
    <section className="card chat">
      <div className="messages">
        {messages.map((message, index) => (
          <p key={index} className={`bubble ${message.from}`}>{message.text}</p>
        ))}
        {busy && <p className="bubble bot muted">{busy}</p>}

        {hasDraft && !editing && (
          <DraftCard reply={reply!} members={members} onChange={update} onEdit={() => setEditing(true)} onConfirm={confirm} />
        )}
        {editing && reply && (
          <ExpenseForm groupId={groupId} members={members} initial={reply.draft} onSaved={savedFromForm} />
        )}
        <div ref={bottom} />
      </div>

      <form className="row composer" onSubmit={submit}>
        <button type="button" className="icon" title="Scan a bill" onClick={() => photoInput.current?.click()}>📷</button>
        <input value={text} onChange={(event) => setText(event.target.value)} placeholder={reply?.question ? 'Your answer…' : 'Describe an expense…'} />
        <button type="button" className={recording ? 'icon recording' : 'icon'} title="Speak" onClick={toggleRecording}>
          {recording ? '⏹' : '🎤'}
        </button>
        <button disabled={!!busy}>Send</button>
        <input
          ref={photoInput}
          type="file"
          accept="image/*"
          capture="environment"
          hidden
          onChange={(event) => event.target.files?.[0] && scanBill(event.target.files[0])}
        />
      </form>
    </section>
  )
}
