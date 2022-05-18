import json
import logging
from pathlib import Path
from typing import List, Optional, Type

from steamship import File, Tag
from steamship.app import Response, create_handler
from steamship.base import Client, Task, TaskState
from steamship.plugin.inputs.block_and_tag_plugin_input import BlockAndTagPluginInput
from steamship.plugin.inputs.train_plugin_input import TrainPluginInput
from steamship.plugin.inputs.training_parameter_plugin_input import TrainingParameterPluginInput
from steamship.plugin.outputs.block_and_tag_plugin_output import BlockAndTagPluginOutput
from steamship.plugin.outputs.train_plugin_output import TrainPluginOutput
from steamship.plugin.outputs.training_parameter_plugin_output import TrainingParameterPluginOutput
from steamship.plugin.service import PluginRequest
from steamship.plugin.tagger import TrainableTagger
from steamship.plugin.trainable_model import TrainableModel

TRAINING_PARAMETERS = TrainingParameterPluginOutput(
    trainingEpochs=3,
    modelName="pytorch_text_classification",
    testingHoldoutPercent=0.3,
    trainingParams=dict(keywords=["chocolate", "roses", "chanpagne"]),
)

TRAIN_RESPONSE = TrainPluginOutput(archive_path_in_steamship="000/default.zip")


class TestTrainableTaggerModel(TrainableModel):
    """Example of a trainable model.

    At some point, may want to evolve this into an abstract base class, but for the time being, here is the
    design of what a "Model" ought to look like:

    TRAINING:
    - Save all results to the folder provided during initialization. The zipfile of this folder
      is the ModelCheckpoint that gets saved to steamship.
    - Note that we'll likely want to iterate on this, e.g.:
        - Does the model create the checkpoint or simply receive a folder into which to save data, etc etc

    LOADING:
    - Offer a constructor that loads the model with a provided path. This path is assumed to contain the unzipped
      ModelCheckpoint that was requested.

      In this example model, the `from_disk(path: Path)` method provides this functionality.
    """

    KEYWORD_LIST_FILE = (
        "keyword_list.json"  # File, relative to the checkpoint, to save/load features from.
    )
    keyword_list: List[str] = None  # Contents of the KEYWORD_LIST_FILE file
    path: Optional[Path] = None  # Save the effective path for testing

    def __init__(self):
        self.path = None
        self.keyword_list = []

    def load_from_folder(self, checkpoint_path: Path):
        """Creates a model instance & loads the provided checkpoint."""
        self.path = checkpoint_path
        with open(self.path / TestTrainableTaggerModel.KEYWORD_LIST_FILE, "r") as f:
            self.keyword_list = json.loads(f.read())

    def save_to_folder(self, checkpoint_path: Path):
        self.path = checkpoint_path
        with open(checkpoint_path / TestTrainableTaggerModel.KEYWORD_LIST_FILE, "w") as f:
            f.write(json.dumps(self.keyword_list))

    def train(self, input: TrainPluginInput) -> TrainPluginOutput:
        """Training for this model is to set the parameters to those provided in the input object.

        This allows us to test that we're properly passing through the training parameters to the train process.
        """
        self.keyword_list = input.training_params.trainingParams.get("keyword_list", [])
        return TRAIN_RESPONSE

    def run(
        self, request: PluginRequest[BlockAndTagPluginInput]
    ) -> Response[BlockAndTagPluginOutput]:
        """Tags the incoming data for any instance of the keywords in the parameter file."""
        return Response(
            data=BlockAndTagPluginOutput(
                file=File.CreateRequest(
                    tags=list(map(lambda word: Tag.CreateRequest(name=word), self.keyword_list))
                )
            )
        )


class TestTrainableTaggerPlugin(TrainableTagger):
    """Tests the Trainable Tagger lifecycle.

    - This tagger produces a FIXED set of trainable parameters.
    - These parameters (and not the trainable data!) fully parameterize the trained model.
    - The trained model (and not the trainable parameters!) fully parameterize the running model.
    - The model simply tags keywords that it finds in the text.

    Taken together, this plugin can be seen as a reference implementation of the data/process lifecycle of a trainable
    model, regardless of where the actual work occurs:

    - It could occur here, running in Lambda.
    - It could occur here, running in ECS.
    - It could be orchestrated from here, but runs in HuggingFace / SageMaker / or elsewhere

    """

    def get_model_class(self) -> Type[TestTrainableTaggerModel]:
        return TestTrainableTaggerModel

    def get_steamship_client(self) -> Client:
        return self.client

    def run_with_model(
        self,
        request: PluginRequest[BlockAndTagPluginInput],
        model: TestTrainableTaggerModel,
    ) -> Response[BlockAndTagPluginOutput]:
        """Downloads the model file from the provided space"""
        logging.info(f"run_with_model {request} {model}")

        return model.run(request)

    def get_training_parameters(
        self, request: PluginRequest[TrainingParameterPluginInput]
    ) -> Response[TrainingParameterPluginOutput]:
        logging.info(f"get training parameters {TRAINING_PARAMETERS}")
        return Response(data=TRAINING_PARAMETERS)

    def train(self, request: PluginRequest[TrainPluginInput]) -> Response[TrainPluginOutput]:
        """Since trainable can't be assumed to be asynchronous, the trainer is responsible for uploading its own model file."""

        # Create a Response object at the top with a Task attached. This will let us stream back updates
        # TODO: This is very non-intuitive. We should improve this.
        logging.info(f"train {request}")

        response = Response(status=Task(task_id=request.task_id))

        # Example of recording training progress
        response.status.status_message = "About to train!"
        response.post_update(client=self.client)

        # Let's create an instance of our model. We'll use get_model_class() here for copy-paste safety.
        model = self.get_model_class()()

        # Train the model
        train_plugin_input = request.data
        train_plugin_output = model.train(train_plugin_input)

        # Save the model with the `default` handle.
        archive_path_in_steamship = model.save_remote(
            client=self.client, plugin_instance_id=request.plugin_instance_id
        )

        # Set the model location on the plugin output.
        train_plugin_output.archive_path_in_steamship = archive_path_in_steamship

        # Set the response on the `data` field of the object
        response.set_data(json=train_plugin_output)

        # If we want we can post this to the Engine
        response.status.status_message = "Done!"
        response.status.state = TaskState.succeeded
        response.post_update(client=self.client)

        # Or, if this training really did happen synchronously, we return it.
        # Some models (e.g. those running on ECS, or on a third party system) will not have completed by the time
        # the Lambda function finishes. For now, let's just pretend they're synchronous. But in a future PR when we
        # have a better method of handling such situations, the response below would include a `status` of type `running`
        # to indicate that, while the plugin handler has returned, the plugin's execution continues.

        return response


handler = create_handler(TestTrainableTaggerPlugin)
