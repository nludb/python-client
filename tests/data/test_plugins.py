# noinspection PyPackageRequirements
import pytest

from steamship import PluginInstance, Space
from steamship.data.plugin import Plugin, PluginAdapterType, PluginType
from tests.utils.client import get_steamship_client


def test_plugin_create():
    steamship = get_steamship_client()

    my_plugins = Plugin.list(steamship).data
    orig_count = len(my_plugins.plugins)

    plugin_args = dict(
        name="name",
        client=steamship,
        description="This is just for test",
        type_=PluginType.embedder,
        transport=PluginAdapterType.steamshipDocker,
        is_public=True,
    )

    required_fields = {"name", "description", "type_"}
    for required_field in required_fields:
        with pytest.raises(Exception):
            del plugin_args[required_field]
            # noinspection PyArgumentList
            _ = Plugin.create(**plugin_args)

    my_plugins = Plugin.list(steamship).data
    assert len(my_plugins.plugins) == orig_count

    plugin = Plugin.create(
        client=steamship,
        training_platform=None,
        description="This is just for test",
        type_=PluginType.tagger,
        transport=PluginAdapterType.steamshipDocker,
        is_public=False,
    ).data
    my_plugins = Plugin.list(steamship).data
    assert len(my_plugins.plugins) == orig_count + 1

    # No upsert doesn't work
    plugin_x = Plugin.create(
        client=steamship,
        training_platform=None,
        handle=plugin.handle,
        description="This is just for test",
        type_=PluginType.tagger,
        transport=PluginAdapterType.steamshipDocker,
        is_public=False,
    )
    assert plugin_x.error is not None
    assert plugin_x.data is None

    # Upsert does work
    plugin2 = Plugin.create(
        client=steamship,
        training_platform=None,
        handle=plugin.handle,
        description="This is just for test 2",
        type_=PluginType.tagger,
        transport=PluginAdapterType.steamshipDocker,
        is_public=False,
        upsert=True,
    ).data

    assert plugin2.id == plugin.id

    my_plugins = Plugin.list(steamship).data
    assert len(my_plugins.plugins) == orig_count + 1

    assert plugin2.id in [plugin.id for plugin in my_plugins.plugins]
    assert plugin2.description in [plugin.description for plugin in my_plugins.plugins]

    # assert(my_plugins.plugins[0].description != plugin.description)

    plugin.delete()

    my_plugins = Plugin.list(steamship).data
    assert len(my_plugins.plugins) == orig_count


def test_plugin_public():
    steamship = get_steamship_client()

    resp = Plugin.list(steamship).data
    assert resp.plugins is not None
    plugins = resp.plugins

    assert len(plugins) > 0

    # Make sure they can't be deleted.
    res = plugins[0].delete()
    assert res.error is not None
    assert res.data is None


def test_deploy_in_space():

    client = get_steamship_client()
    space = Space.create(client, handle="test-non-default-space").data
    instance = PluginInstance.create(client, plugin_handle="test-tagger", space_id=space.id).data
    assert instance.spaceId == space.id
