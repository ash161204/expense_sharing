from django.shortcuts import get_object_or_404
from groq import BadRequestError, GroqError, RateLimitError
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.models import Group
from ledger.serializers import ExpenseInput

from .draft import finish, items_match_subtotal, items_total, merge, next_question, preview_shares, start_draft
from .llm import extract
from .ocr import RECEIPT_INTRO, read_receipt
from .stt import transcribe

UNAVAILABLE = "The assistant is not available right now. You can still add the expense in the Expenses tab."
NOT_UNDERSTOOD = "Sorry, I couldn't understand that. Please say it another way, using the names in this group."
QUOTA_USED_UP = "The free AI quota is used up for now. Try again later, or add the expense in the Expenses tab."


def understand(draft, message, members, me, question):
    """Asks the LLM about one message and merges its answer into the draft.

    A receipt whose items don't add up to its printed subtotal gets one second look
    (the model is told the numbers); if it still doesn't match, next_question asks the user.
    """
    from_receipt = message.startswith(RECEIPT_INTRO)
    context = {"names": [m.name for m in members], "me": me, "question": question, "items": [i["name"] for i in draft["items"]]}
    draft = merge(draft, extract(message, **context), members, from_receipt)
    if from_receipt and not items_match_subtotal(draft):
        hint = f"\n\nCheck: your items add up to {items_total(draft)} but the SUBTOTAL is {draft['subtotal']}."
        draft = merge(draft, extract(message + hint, **context), members, from_receipt)
    return draft


class ChatInput(serializers.Serializer):
    draft = serializers.DictField(required=False, allow_null=True)  # null on the first message
    message = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    question = serializers.CharField(required=False, allow_blank=True)


class Assistant(APIView):
    """One chat turn: read the message, update the draft, ask the next question (or show the preview)."""
    permission_classes = [IsAuthenticated]
    serializer_class = ChatInput

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        members = list(group.members.all())
        if request.user not in members:
            raise serializers.ValidationError("Join this group first to use the assistant.")
        serializer = ChatInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        draft = start_draft(data.get("draft"), members)
        if data.get("message", "").strip():
            try:
                draft = understand(draft, data["message"], members, request.user.name, data.get("question", ""))
            except BadRequestError:  # the model's answer didn't fit the schema
                return Response({"detail": NOT_UNDERSTOOD}, status=400)
            except RateLimitError:  # Groq's free daily/minute limits
                return Response({"detail": QUOTA_USED_UP}, status=503)
            except GroqError:  # no key, network
                return Response({"detail": UNAVAILABLE}, status=503)

        question = next_question(draft)
        if question:
            return Response({"draft": draft, "question": question, "errors": {}, "shares": []})

        finish(draft)
        check = ExpenseInput(data=draft, context={"group": group})  # the same rules as the Expenses form
        if not check.is_valid():
            return Response({"draft": draft, "question": None, "errors": check.errors, "shares": []})
        return Response({"draft": draft, "question": None, "errors": {}, "shares": preview_shares(check.validated_data, members)})


class ScanInput(serializers.Serializer):
    image = serializers.ImageField()


class Scan(APIView):
    """Receipt photo -> text (local OCR), ready to send as a chat message."""
    permission_classes = [IsAuthenticated]
    serializer_class = ScanInput

    def post(self, request):
        serializer = ScanInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"text": RECEIPT_INTRO + read_receipt(serializer.validated_data["image"])})


class AudioInput(serializers.Serializer):
    audio = serializers.FileField()


class Transcribe(APIView):
    """Voice recording -> text. The group's names help Whisper spell them right."""
    permission_classes = [IsAuthenticated]
    serializer_class = AudioInput

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        serializer = AudioInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        names = [member.name for member in group.members.all()]
        try:
            return Response({"text": transcribe(serializer.validated_data["audio"], names)})
        except GroqError:
            return Response({"detail": UNAVAILABLE}, status=503)
