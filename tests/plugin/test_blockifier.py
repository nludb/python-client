import pytest

from steamship.plugin.inputs.raw_data_plugin_input import RawDataPluginInput
from steamship.plugin.inputs.train_plugin_input import TrainPluginInput
from steamship.plugin.inputs.training_parameter_plugin_input import TrainingParameterPluginInput
from steamship.plugin.service import PluginRequest
from tests.demo_apps.plugins.blockifiers.blockifier import DummyBlockifierPlugin

__copyright__ = "Steamship"
__license__ = "MIT"

TEST_REQ = RawDataPluginInput(data="Hi there")
TEST_PLUGIN_REQ = PluginRequest(data=TEST_REQ)
TEST_PLUGIN_REQ_DICT = TEST_PLUGIN_REQ.to_dict()

def _test_resp(res):
    assert res.data is not None
    assert res.data.file is not None
    assert len(res.data.file.blocks) == 4

def test_resp():
    blockifier = DummyBlockifierPlugin()
    request = PluginRequest(data=TEST_REQ)
    res = blockifier.run(request)
    _test_resp(res)

    # The endpoints take a kwargs block which is transformed into the appropriate JSON object
    res2 = blockifier.run_endpoint(**TEST_PLUGIN_REQ_DICT)
    _test_resp(res2)

    # This plugin is not trainable, and thus it refuses training parameters requests
    with pytest.raises(Exception):
        blockifier.get_training_parameters(PluginRequest(data=TrainingParameterPluginInput()))
    with pytest.raises(Exception):
        blockifier.get_training_parameters_endpoint(**PluginRequest(data=TrainingParameterPluginInput()))

    # This plugin is not trainable, and thus it refuses train requests
    with pytest.raises(Exception):
        blockifier.train(PluginRequest(data=TrainPluginInput()))
    with pytest.raises(Exception):
        blockifier.train_endpoint(**PluginRequest(data=TrainPluginInput()))
