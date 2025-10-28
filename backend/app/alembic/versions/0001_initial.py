from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String()),
        sa.Column("country", sa.String()),
        sa.Column("city", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "organizers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_name", sa.String(), nullable=False),
        sa.Column("contact_email", sa.String()),
        sa.Column("contact_phone", sa.String()),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organizer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizers.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("location_text", sa.String()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("capacity_total", sa.Integer(), nullable=False),
        sa.Column("capacity_available", sa.Integer(), nullable=False),
        sa.Column("allow_children", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "ticket_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("price", sa.Numeric(12,2), nullable=False),
        sa.Column("is_child", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("per_adult_child_limit", sa.Integer()),
    )
    op.create_table(
        "price_windows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_multiplier", sa.Numeric(6,3)),
        sa.Column("fixed_discount", sa.Numeric(12,2)),
    )
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subtotal", sa.Numeric(12,2), nullable=False, server_default="0"),
        sa.Column("discount_total", sa.Numeric(12,2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12,2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(), server_default="CLP"),
        sa.Column("status", sa.String(), server_default="pending"),
        sa.Column("payment_provider", sa.String()),
        sa.Column("payment_reference", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.String(), unique=True),
    )
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("ticket_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ticket_types.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12,2), nullable=False),
        sa.Column("final_price", sa.Numeric(12,2), nullable=False),
    )
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("order_items.id"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("holder_first_name", sa.String(), nullable=False),
        sa.Column("holder_last_name", sa.String(), nullable=False),
        sa.Column("holder_document_type", sa.String(), nullable=False),
        sa.Column("holder_document_number", sa.String(), nullable=False),
        sa.Column("is_child", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("qr_signature", sa.String()),
        sa.Column("pdf_object_key", sa.String()),
        sa.Column("status", sa.String(), server_default="issued"),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "capacity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

def downgrade() -> None:
    for t in [
        "capacity_logs","tickets","order_items","orders","price_windows",
        "ticket_types","events","organizers","users"
    ]:
        op.drop_table(t)
