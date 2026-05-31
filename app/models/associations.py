from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

# Association table for many-to-many relationship between decisions and risks
# (if a risk can affect multiple decisions)
decision_risk_association = Table(
    "decision_risk_association",
    Base.metadata,
    Column("decision_id", UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE")),
    Column("risk_id", UUID(as_uuid=True), ForeignKey("risks.id", ondelete="CASCADE")),
)

# Association table for action_items and risks
action_item_risk_association = Table(
    "action_item_risk_association",
    Base.metadata,
    Column("action_item_id", UUID(as_uuid=True), ForeignKey("action_items.id", ondelete="CASCADE")),
    Column("risk_id", UUID(as_uuid=True), ForeignKey("risks.id", ondelete="CASCADE")),
)