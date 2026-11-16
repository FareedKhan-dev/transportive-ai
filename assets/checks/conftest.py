"""checks/conftest.py: tests in the room read the replica alias from the lagging standby.
Saleor's test settings mirror the replica onto the primary, so no test there can see lag. Once pytest-django has
created the test database, point a real connection at the same database on the standby."""
import os

import pytest
from django.db import connections


@pytest.fixture(autouse=True)
def standby_replica(django_db_setup, settings):
    name = connections["default"].settings_dict["NAME"]
    replica = {**connections["default"].settings_dict, "HOST": "standby", "NAME": name, "TEST": {"MIRROR": None}}
    connections.databases[settings.DATABASE_CONNECTION_REPLICA_NAME] = replica
    del connections[settings.DATABASE_CONNECTION_REPLICA_NAME]
    yield
    connections[settings.DATABASE_CONNECTION_REPLICA_NAME].close()
