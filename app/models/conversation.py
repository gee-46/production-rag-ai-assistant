import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPk


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ConversationSession(Base, UUIDPk, TimestampMixin):
    __tablename__ = "conversation_sessions"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", order_by="Message.created_at", cascade="all, delete-orphan"
    )


class Message(Base, UUIDPk, TimestampMixin):
    __tablename__ = "messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # List of {chunk_id, document_id, filename, snippet, score} — the exact
    # evidence used to ground this assistant message, and the hallucination
    # verdict computed for it (see services/rag/hallucination.py).
    citations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    groundedness: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    session: Mapped["ConversationSession"] = relationship(back_populates="messages")
