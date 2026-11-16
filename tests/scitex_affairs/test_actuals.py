from scitex_dev.store import FieldRole, WriterPolicy

from scitex_affairs.actuals import (
    ACTUALS_PLUGIN,
    ACTUALS_SCHEMA,
    provide_store_plugins,
)


def test_store_plugin_is_multi_writer():
    # Arrange
    plugin = ACTUALS_PLUGIN
    # Act
    policy = plugin.writer_policy
    # Assert
    assert policy is WriterPolicy.MULTI_WRITER


def test_actual_ids_are_identity_fields():
    # Arrange
    schema = ACTUALS_SCHEMA
    # Act
    role = schema.fields["id"].role
    # Assert
    assert role is FieldRole.IDENTITY


def test_plugin_provider_is_discoverable():
    # Arrange
    expected = (ACTUALS_PLUGIN,)
    # Act
    discovered = provide_store_plugins()
    # Assert
    assert discovered == expected
