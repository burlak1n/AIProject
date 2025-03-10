"""new

Revision ID: 28c2f466f749
Revises: 7fe13a29cdde
Create Date: 2025-03-10 15:56:58.714879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28c2f466f749'
down_revision: Union[str, None] = '7fe13a29cdde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
