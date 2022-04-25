from steamship import DocTag
from steamship.data.plugin import TrainingPlatform
from steamship.extension.file import File
from steamship.plugin.inputs.export_plugin_input import ExportPluginInput
from steamship.plugin.inputs.training_parameter_plugin_input import TrainingParameterPluginInput
import time

from ..client.helpers import deploy_plugin, upload_file, _steamship

__copyright__ = "Steamship"
__license__ = "MIT"


def test_e2e_trainable_tagger_lambda_training():
    client = _steamship()
    versionConfigTemplate = dict(
        textColumn=dict(type="string"),
        tagColumns=dict(type="string"),
        tagKind=dict(type="string")
    )
    instanceConfig = dict(
        textColumn="Message",
        tagColumns="Category",
        tagKind="Intent"
    )

    # Make a blockifier which will generate our training corpus
    with deploy_plugin("plugin_blockifier_csv.py", "blockifier", versionConfigTemplate=versionConfigTemplate, instanceConfig=instanceConfig, trainingPlatform=TrainingPlatform.custom) as (plugin, version, instance):
        with upload_file("utterances.csv") as file:
            assert (len(file.query().data.blocks) == 0)
            # Use the plugin we just registered
            file.blockify(pluginInstance=instance.handle).wait()
            assert (len(file.query().data.blocks) == 5)

            # Now make a trainable tagger to train on those tags
            with deploy_plugin("plugin_trainable_tagger.py", "tagger", trainingPlatform=TrainingPlatform.custom) as (tagger, taggerVersion, taggerInstance):

                # Now train the plugippcn
                trainingRequest = TrainingParameterPluginInput(
                    pluginInstance=taggerInstance.handle,
                    exportPluginInput=ExportPluginInput(
                        type="corpus",
                        handle="default"
                    )
                )

                trainResult = taggerInstance.train(trainingRequest)

                trainResult.wait()

def test_e2e_trainable_tagger_ecs_training():
    client = _steamship()
    versionConfigTemplate = dict(
        textColumn=dict(type="string"),
        tagColumns=dict(type="string"),
        tagKind=dict(type="string")
    )
    instanceConfig = dict(
        textColumn="Message",
        tagColumns="Category",
        tagKind="Intent"
    )

    # Make a blockifier which will generate our training corpus
    with deploy_plugin("plugin_blockifier_csv.py", "blockifier", versionConfigTemplate=versionConfigTemplate, instanceConfig=instanceConfig, trainingPlatform=TrainingPlatform.managed) as (plugin, version, instance):
        with upload_file("utterances.csv") as file:
            assert (len(file.query().data.blocks) == 0)
            # Use the plugin we just registered
            file.blockify(pluginInstance=instance.handle).wait()
            assert (len(file.query().data.blocks) == 5)

            # Now make a trainable tagger to train on those tags
            with deploy_plugin("plugin_trainable_tagger.py", "tagger", trainingPlatform=TrainingPlatform.custom) as (tagger, taggerVersion, taggerInstance):

                # Now train the plugippcn
                trainingRequest = TrainingParameterPluginInput(
                    pluginInstance=taggerInstance.handle,
                    exportPluginInput=ExportPluginInput(
                        type="corpus",
                        handle="default"
                    )
                )

                trainResult = taggerInstance.train(trainingRequest)

                trainResult.wait()