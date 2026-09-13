"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-13 16:10:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure PostGIS extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('location', Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_dataset', sa.String(length=100), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_alerts_id', 'alerts', ['id'])
    op.create_index('ix_alerts_alert_type', 'alerts', ['alert_type'])
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'])

    # 2. vessel_risk_records table
    op.create_table(
        'vessel_risk_records',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('mmsi', sa.String(length=20), nullable=False),
        sa.Column('vessel_name', sa.String(length=100), nullable=True),
        sa.Column('vessel_type', sa.Integer(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('speed_knots', sa.Float(), nullable=True),
        sa.Column('course_degrees', sa.Float(), nullable=True),
        sa.Column('ais_gap_minutes', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_dark_vessel', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('in_mpa_zone', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('mpa_zone_name', sa.String(length=100), nullable=True),
        sa.Column('risk_breakdown', sa.JSON(), nullable=True),
        sa.Column('scored_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index('ix_vessel_risk_records_mmsi', 'vessel_risk_records', ['mmsi'])
    op.create_index('ix_vessel_risk_records_scored_at', 'vessel_risk_records', ['scored_at'])

    # 3. thermal_hotspots table
    op.create_table(
        'thermal_hotspots',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('location', Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('brightness_kelvin', sa.Float(), nullable=True),
        sa.Column('frp_mw', sa.Float(), nullable=True),
        sa.Column('confidence', sa.String(length=10), nullable=True),
        sa.Column('satellite', sa.String(length=20), nullable=True),
        sa.Column('instrument', sa.String(length=20), nullable=True),
        sa.Column('acquisition_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('classification', sa.String(length=50), nullable=True),
        sa.Column('classification_confidence', sa.Float(), nullable=True),
        sa.Column('cpcb_cluster_name', sa.String(length=100), nullable=True),
        sa.Column('dist_to_cpcb_km', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index('ix_thermal_hotspots_acquisition_date', 'thermal_hotspots', ['acquisition_date'])

    # 4. vessel_ais_history table
    op.create_table(
        'vessel_ais_history',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('mmsi', sa.String(length=20), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('sog', sa.Float(), nullable=True),
        sa.Column('cog', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index('ix_vessel_ais_history_mmsi_timestamp', 'vessel_ais_history', ['mmsi', 'timestamp'])

    # 5. cpcb_polluted_areas table
    op.create_table(
        'cpcb_polluted_areas',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('cepi_score', sa.Float(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
    )

    # 6. landslide_risk_zones table
    op.create_table(
        'landslide_risk_zones',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('zone_name', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('slope_degrees', sa.Float(), nullable=True),
        sa.Column('geology_type', sa.String(length=100), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
    )

    # 7. landslide_monitoring_zones table
    op.create_table(
        'landslide_monitoring_zones',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('site_name', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('last_insar_displacement_mm', sa.Float(), nullable=True),
        sa.Column('cumulative_rainfall_mm', sa.Float(), nullable=True),
        sa.Column('alert_triggered', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('landslide_monitoring_zones')
    op.drop_table('landslide_risk_zones')
    op.drop_table('cpcb_polluted_areas')
    op.drop_table('vessel_ais_history')
    op.drop_table('thermal_hotspots')
    op.drop_table('vessel_risk_records')
    op.drop_table('alerts')
