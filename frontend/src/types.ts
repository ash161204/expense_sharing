// The JSON shapes returned by the Django API. Money is always a string like "400.00".

export type User = { id: number; name: string }

export type Group = { id: number; name: string }

export type Share = { user_id: number; name: string; amount: string }

export type Expense = {
  id: number
  description: string
  amount: string
  split_type: 'equal' | 'itemized'
  payers: Share[]
  splits: Share[]
  items: { name: string; amount: string; shared_by: Share[] }[]
  created_at: string
}

export type Balance = { user_id: number; name: string; paid: string; share: string; net: string }

export type Balances = {
  members: Balance[]
  owes: Record<string, { owes: Record<string, string> }>
}

export type Settlement = { id: number; from_user: string; to_user: string; amount: string; created_at: string }

/** The AI assistant's draft: the same shape as a new-expense request. */
export type Draft = {
  description: string
  amount: string
  payers: { user_id: number; amount: string }[]
  participant_ids: number[]
  items?: { name: string; amount: string; shared_by: number[] }[]
  split_type?: 'equal' | 'itemized'
}

export type AssistantReply = {
  draft: Draft
  question: string | null
  errors: Record<string, unknown>
  shares: { user_id: number; name: string; amount: string }[]
}
