"""The AI-062 harness on a port read from MySQL (AI-050 snapshot, B2 context, B3), the way the
PART2_SOLVE handler reads it. Every value is SYNTHETIC; the port comes from the AI-059 scenarios.
"""

from datetime import timedelta
from decimal import Decimal

import pytest

from common.config import WorkerPart, load_env_settings
from common.db.connection import connect_worker
from part2.context import load_filter_context
from part2.inputs import as_duration, read_service_inputs, service_times
from part2.solver import SolverSettings
from part2.state.snapshot import load_port_state
from tests.integration.test_part2_job import H0, Port, port, queues, root  # noqa: F401 (fixtures)
from tools.evaluate.harness import NOT_DEFINED, compare

pytestmark = pytest.mark.integration


def test_the_harness_produces_the_table_for_a_port_read_from_the_database(
    port: Port,  # noqa: F811 (the fixture imported above)
) -> None:
    first, second, untimed = port.request(), port.request(), port.request(baplie=False)
    ids = [first, second, untimed]
    connection = connect_worker(
        load_env_settings(port.port_db.worker_env(WorkerPart.PART2), WorkerPart.PART2)
    )
    try:
        state = load_port_state(
            connection,
            ids,
            horizon_start=H0 - timedelta(days=1),
            horizon_end=H0 + timedelta(days=7),
        )
        context = load_filter_context(connection, state)
        inputs = read_service_inputs(connection, ids)
        connection.rollback()
        timed = service_times(state, inputs, context.vessel_type_ids)
        durations = {
            r: as_duration(t.p50_hours) for r, t in timed.items() if t.p50_hours is not None
        }
        settings = SolverSettings(10, 3, Decimal(10), Decimal("1.0"), Decimal("1.0"))
        comparison = compare(state, sorted(durations), context, durations, settings)
    finally:
        connection.close()

    assert sorted(durations) == [first, second]  # B3 can't time the request without a BAPLIE
    rows = {name: (cpsat, fifo) for name, cpsat, fifo in comparison.rows()}
    assert rows["Requests placed"] == ("2 of 2", "2 of 2")
    assert rows["Conflicts (resource overlaps)"] == ("0", "0")
    assert rows["Hard-constraint violations (B2)"] == ("0", "0")
    assert rows["Estimated operational cost"] == (NOT_DEFINED, NOT_DEFINED)
    assert all(float(v) > 0 for v in rows["Utilisation, berths"])
