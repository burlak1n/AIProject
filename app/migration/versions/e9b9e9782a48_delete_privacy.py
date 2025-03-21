"""Delete privacy

Revision ID: e9b9e9782a48
Revises: 29139b6fb7e9
Create Date: 2025-03-21 19:19:49.355987

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9b9e9782a48'
down_revision: Union[str, None] = '29139b6fb7e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'private')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('private', sa.BOOLEAN(), nullable=False))
    # ### end Alembic commands ###
