"""One LLM call: turn a chat message (or receipt text) into strict JSON. The LLM never decides or calculates anything."""
import json
import os

from groq import Groq, RateLimitError

MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
FALLBACK_MODEL = "openai/gpt-oss-120b"  # used only when MODEL's free daily quota is used up

INSTRUCTIONS = """You fill in JSON about ONE shared expense from the user's message. Rules:
- People: use only these names: {names}. "I", "me" or "my" means {me}. "everyone", "all" or "all of us" means everyone.
  Voice input can misspell names: use the closest name from the list (for example "Unket" is "Ankit").
- Write amounts as digits: "a thousand" is "1000", "1.5k" is "1500", "twelve hundred" is "1200". Never add, subtract or split amounts yourself.
- If someone paid "the rest", "the remaining" or "the balance", write "rest" as their amount (the app works it out).
- Receipt text comes from OCR, so letters can be misread. Correct item names to the real words (for example "UEG LUNCH" is "VEG LUNCH", "BUTTER M1LK" is "BUTTER MILK"), but copy amounts exactly.
- description: always give a short title, like "Dinner" or "Beach shack lunch". For a receipt, use the shop or hotel name.
- total: the amount for the whole bill (on a receipt, the TOTAL line). subtotal: the SUBTOTAL line on a receipt, if there is one.
- items: only when separate things are listed with their own prices. One amount for the whole bill is the total, not an item.
  Use clean item names and the line amount: for "2 x PARKING (DAILY) @ $25.00 $50.00" the item is "PARKING (DAILY)" and the amount is "50.00".
  Never list subtotal, tax, service charge, VAT, total, cash or change as items.
  On a receipt the item amounts add up to the SUBTOTAL: if yours don't, you probably took a unit price instead of a line total.
- who_had_what: which people had which item. Items already on this bill: {items}.
  If everyone had everything, return one entry with item "everything" and people ["everyone"]; add more entries for any exceptions.
- split_between: only when the user says who shares the bill ("split with Rahul", "for me and Ankit"). People who paid are not automatically sharing, so leave it empty otherwise.
- payers: only people the user says paid, with an amount only if it is said.
- A receipt always belongs to this group, whatever name is printed on it. It never says who paid or who had what, so leave payers and who_had_what empty for a receipt.
- Anything not mentioned: null or [].
The user is answering this question: "{question}"."""


def schema(names):
    """Strict JSON schema. People can only be group members (or "everyone"), so the model can't invent names."""
    person = {"type": "string", "enum": names + ["everyone"]}

    def obj(**properties):
        return {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}

    def list_of(item):  # null is allowed too: the model sometimes writes null for "nothing"
        return {"type": ["array", "null"], "items": item}

    return obj(
        description={"type": ["string", "null"]},
        total={"type": ["string", "null"]},
        subtotal={"type": ["string", "null"]},
        items=list_of(obj(name={"type": "string"}, amount={"type": "string"})),
        who_had_what=list_of(obj(item={"type": "string"}, people={"type": "array", "items": person})),
        split_between=list_of(person),
        payers=list_of(obj(person=person, amount={"type": ["string", "null"]})),
    )


def extract(message, names, me, question, items):
    """Returns the expense details found in the message, e.g. {"total": "1200", "payers": [{"person": "Mohit", ...}], ...}."""
    instructions = INSTRUCTIONS.format(names=", ".join(names), me=me, question=question, items=", ".join(items) or "none yet")
    request = {
        "temperature": 0,
        "reasoning_effort": "medium",  # "low" was measured dropping items (3 of 3 runs); "medium" got them all
        "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": message}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "expense", "strict": True, "schema": schema(names)}},
    }
    try:
        # reads GROQ_API_KEY from the environment; no automatic retries, so a used-up quota falls back at once
        response = Groq(max_retries=0).chat.completions.create(model=MODEL, **request)
    except RateLimitError:  # free quota used up: the other model has its own quota on the same key
        response = Groq().chat.completions.create(model=FALLBACK_MODEL, **request)
    return json.loads(response.choices[0].message.content)
