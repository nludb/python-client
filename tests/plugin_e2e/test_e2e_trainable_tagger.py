import json
import logging
from pathlib import Path

from steamship import Block, File
from steamship.base import Response
from steamship.client.operations.tagger import TagResponse
from steamship.data.plugin import InferencePlatform, TrainingPlatform
from steamship.data.plugin_instance import PluginInstance
from steamship.data.space import Space
from steamship.plugin.inputs.export_plugin_input import ExportPluginInput
from steamship.plugin.inputs.training_parameter_plugin_input import TrainingParameterPluginInput
from steamship.plugin.outputs.model_checkpoint import ModelCheckpoint
from tests import APPS_PATH
from tests.demo_apps.plugins.trainable_taggers.plugin_trainable_tagger import (
    TestTrainableTaggerModel,
)
from tests.utils.client import get_steamship_client
from tests.utils.deployables import deploy_plugin

EXPORTER_HANDLE = "signed-url-exporter"
KEYWORDS = ["product", "coupon"]


def test_e2e_trainable_tagger_lambda_training():
    client = get_steamship_client()
    spaceR = Space.get(client)
    assert spaceR.data is not None
    space = spaceR.data

    version_config_template = dict(
        text_column=dict(type="string"),
        tag_columns=dict(type="string"),
        tag_kind=dict(type="string"),
    )
    instance_config = dict(text_column="Message", tag_columns="Category", tag_kind="Intent")

    exporter_plugin_r = PluginInstance.create(
        client=client,
        handle=EXPORTER_HANDLE,
        plugin_handle=EXPORTER_HANDLE,
        upsert=True,
    )
    assert exporter_plugin_r.data is not None
    exporter_plugin = exporter_plugin_r.data
    assert exporter_plugin.handle is not None

    csv_blockifier_path = APPS_PATH / "plugins" / "blockifiers" / "csv_blockifier.py"
    trainable_tagger_path = (
        APPS_PATH / "plugins" / "trainable_taggers" / "plugin_trainable_tagger.py"
    )

    # # Make a blockifier which will generate our trainable corpus
    # with deploy_plugin(
    #     client,
    #     csv_blockifier_path,
    #     "blockifier",
    #     version_config_template=version_config_template,
    #     instance_config=instance_config,
    # ) as (plugin, version, instance):
    #     with upload_file(client, "utterances.csv") as file:
    #         assert len(file.refresh().data.blocks) == 0
    #         # Use the plugin we just registered
    #         file.blockify(plugin_instance=instance.handle).wait()
    #         assert len(file.refresh().data.blocks) == 5
    if True:
        if True:
            # Now make a trainable tagger to train on those tags
            with deploy_plugin(
                client,
                trainable_tagger_path,
                "tagger",
                training_platform=TrainingPlatform.LAMBDA,
                inference_platform=InferencePlatform.LAMBDA,
            ) as (tagger, tagger_version, tagger_instance):
                # Now train the plugin
                training_request = TrainingParameterPluginInput(
                    plugin_instance=tagger_instance.handle,
                    export_request=ExportPluginInput(
                        plugin_instance=EXPORTER_HANDLE, type="corpus", handle="default"
                    ),
                    training_params=dict(
                        keyword_list=KEYWORDS  # This is a key defined by the test model we're training
                    ),
                )

                train_result = tagger_instance.train(training_request)
                train_result.wait()

                # At this point, the PluginInstance will have written a parameter file to disk. We should be able to
                # retrieve it since we know that it is tagged as the `default`.

                checkpoint = ModelCheckpoint(
                    client=client,
                    handle="default",
                    plugin_instance_id=tagger_instance.id,
                )
                checkpoint_path = checkpoint.download_model_bundle()
                assert checkpoint_path.exists()
                keyword_path = Path(checkpoint_path) / TestTrainableTaggerModel.KEYWORD_LIST_FILE
                assert keyword_path.exists()
                with open(keyword_path, "r") as f:
                    params = json.loads(f.read())
                    assert params == KEYWORDS

                logging.info("Waiting 15 seconds for instance to deploy.")
                import time

                time.sleep(15)

                # If we're here, we have verified that the plugin instance has correctly recorded its parameters
                # into the pluginData bucket under a path unique to the PluginInstnace/ModelCheckpoint.

                # Now we'll attempt to USE this plugin. This plugin's behavior is to simply tag any file with the
                # tags that parameter it. Since those tags are (see above) ["product", "coupon"] we should expect
                # this tagger to apply those tags to any file provided to it.

                # First we'll create a file
                test_doc = "Hi there"
                res = client.tag(doc=test_doc, plugin_instance=tagger_instance.handle)
                res.wait()
                assert res.error is None
                assert res.data is not None
                assert res.data.file is not None
                assert res.data.file.tags is not None
                assert len(res.data.file.tags) == len(KEYWORDS)
                assert sorted([tag.name for tag in res.data.file.tags]) == sorted(KEYWORDS)
