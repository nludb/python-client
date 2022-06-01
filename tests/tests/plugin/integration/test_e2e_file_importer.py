from steamship import File
from steamship.client import Steamship
from tests import PLUGINS_PATH
from tests.assets.plugins.blockifiers.blockifier import TEST_DOC
from tests.utils.deployables import deploy_plugin
from tests.utils.fixtures import client  # noqa: F401


def test_e2e_importer(client: Steamship):
    file_importer_path = PLUGINS_PATH / "importers" / "plugin_file_importer.py"
    with deploy_plugin(client, file_importer_path, "fileImporter") as (
        plugin,
        version,
        instance,
    ):
        # The test FileImporter should always return a string file with contents TEST_DOC
        file = File.create(
            client=client, content="This is a test.", plugin_instance=instance.handle
        ).data

        # Now fetch the data from Steamship and assert that it is the SAME as the data the FileImporter creates
        data = file.raw().data
        assert data.decode("utf-8") == TEST_DOC

        file.delete()
