"""
Provides an example of how a third-party model can be incorporated into Steamship as a Trainable Tagger.

In this example, we have three classes:

- MockClient       -- Simulates the API client for a service such as Google AutoML
- ThirdPartyModel  -- Demonstrates how to build a model that is simply wrapping usage of the MockClient
- ThirdPartyTrainableTaggerPlugin -- Plugin-wrapper around the ThirdPartyModel
"""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Type

from assets.plugins.taggers.plugin_trainable_tagger import (
    TRAINING_PARAMETERS,
    TestTrainableTaggerModel,
)

from steamship import Block, File, SteamshipError, Tag
from steamship.app import Response, create_handler
from steamship.base import Task
from steamship.plugin.config import Config
from steamship.plugin.inputs.block_and_tag_plugin_input import BlockAndTagPluginInput
from steamship.plugin.inputs.train_plugin_input import TrainPluginInput
from steamship.plugin.inputs.train_status_plugin_input import TrainStatusPluginInput
from steamship.plugin.inputs.training_parameter_plugin_input import TrainingParameterPluginInput
from steamship.plugin.outputs.block_and_tag_plugin_output import BlockAndTagPluginOutput
from steamship.plugin.outputs.train_plugin_output import TrainPluginOutput
from steamship.plugin.outputs.training_parameter_plugin_output import TrainingParameterPluginOutput
from steamship.plugin.service import PluginRequest
from steamship.plugin.tagger import TrainableTagger
from steamship.plugin.trainable_model import TrainableModel

# If this isn't present, Localstack won't show logs
logging.getLogger().setLevel(logging.INFO)


class MockClient:
    """This is a simulation of what a third-party client to an AutoML-style API might look like.

    We simulate the fact that it offers:
    * The ability to upload a dataset
    * The ability to initiate an async model training job
    * The ability to check on that training job
    * The ability to run the resulting trained model.
    """

    class ThirdPartyTrainingStatus(str, Enum):
        TRAINING = "training"
        TRAINED = "trained"

    LABELS = ["label__mock"]
    FAKE_TRAINING_FILE_ID = "0000-0000-0000-0000"
    FAKE_MODEL_ID = "0000-0000-0000-0000"

    def upload_file_training_file(self, data: Optional[bytes] = None) -> str:
        """Pretends to upload a file and returns an ID representing that file on the remote third-party system"""
        return self.FAKE_TRAINING_FILE_ID

    def train(self, training_file_id: str) -> str:
        """Pretends to initiate a training process on the third-party system. Returns an ID representing the model ID."""
        return self.FAKE_MODEL_ID

    def training_status(self, model_id: str) -> ThirdPartyTrainingStatus:
        return self.ThirdPartyTrainingStatus.TRAINED

    def infer(self, text: str, model_id) -> List[str]:
        return self.LABELS


class ThirdPartyModel(TrainableModel):
    """Example of a trainable model that wraps a third-party training/inference process.

    We separate this class from the `MockClient` above because, in a real setting, the `MockClient` would be a
    pip-installable package (e.g. `pip install google-automl`), where as this class is the Steamship-created
    wrapper of that pacakge.

    From this *Steamship* perspective, the goal of this `ThirdPartyModel` wrapper class is to load and store
    all the necessary state for training and communicating with the remote model. This might be as simple as
    a single `MODEL_ID` parameter returned by the remote service, used for inquiring about training status
    and/or invoking the trained model.
    """

    # We save the the remote model ID in this file.
    PARAM_FILE = "model_information.json"
    params: Optional[Dict] = None
    client: Optional[MockClient] = None

    def __init__(self):
        self.client = MockClient()

    def load_from_folder(self, checkpoint_path: Path):
        """[Required by TrainableModel] Load state from the provided path."""
        with open(checkpoint_path / self.PARAM_FILE, "r") as f:
            self.params = json.loads(f.read())

    def save_to_folder(self, checkpoint_path: Path):
        """[Required by TrainableModel] Save state to the provided path."""
        with open(checkpoint_path / self.PARAM_FILE, "w") as f:
            f.write(json.dumps(self.params))

    def train(self, input: TrainPluginInput) -> TrainPluginOutput:
        """Trains using the MockClient."""

        if self.client is None:
            raise SteamshipError(message="MockClient was null.")

        reference_data = {"num_checkins": 0}
        return TrainPluginOutput(training_complete=False, training_reference_data=reference_data)

    def train_status(self, input: TrainStatusPluginInput) -> TrainPluginOutput:
        reference_data = input.training_reference_data
        logging.info(f'Called train_status with {reference_data["num_checkins"]}')
        reference_data["num_checkins"] += 1
        complete = reference_data["num_checkins"] > 2
        if complete:
            # Initialize the parameter bundle we'll eventually save to disk.
            self.params = {}

            # Step 1. Simulate preparing data
            data = None

            # Step 2. Simulate uploading data
            data_file_id = self.client.upload_file_training_file(data)
            self.params["data_file_id"] = data_file_id

            # Step 3. Simulate training
            model_id = self.client.train(data_file_id)
            self.params["model_id"] = model_id

        return TrainPluginOutput(training_complete=complete, training_reference_data=reference_data)

    def run(
        self, request: PluginRequest[BlockAndTagPluginInput]
    ) -> Response[BlockAndTagPluginOutput]:
        """Runs the mock client"""

        if "model_id" not in self.params:
            raise SteamshipError(
                message="No model_id was found in model parameter file. Has the model been trained?"
            )

        output = BlockAndTagPluginOutput(file=File.CreateRequest(blocks=[]))

        for in_block in request.data.file.blocks:
            tags = self.client.infer(in_block.text, self.params["model_id"])
            out_block = Block.CreateRequest(
                id=in_block.id, tags=[Tag.CreateRequest(name=tag) for tag in tags]
            )
            output.file.blocks.append(out_block)

        return Response(json=output)


class ThirdPartyTrainableTaggerPlugin(TrainableTagger):
    """Plugin Wrapper for the `ThirdPartyModel`.

    This wrapper class does little other than translate the plugin lifecycle requests from Steamship
    into calls on the `ThirdPartyModel` object above.
    """

    class EmptyConfig(Config):
        pass

    def config_cls(self) -> Type[Config]:
        return self.EmptyConfig

    def model_cls(self) -> Type[ThirdPartyModel]:
        return ThirdPartyModel

    def run_with_model(
        self, request: PluginRequest[BlockAndTagPluginInput], model: TestTrainableTaggerModel
    ) -> Response[BlockAndTagPluginOutput]:
        """Downloads the model file from the provided space"""
        logging.debug(f"run_with_model {request} {model}")
        return model.run(request)

    def get_training_parameters(
        self, request: PluginRequest[TrainingParameterPluginInput]
    ) -> Response[TrainingParameterPluginOutput]:
        logging.debug(f"get_training_parameters {request}")
        return Response(data=TRAINING_PARAMETERS)

    def train(
        self, request: PluginRequest[TrainPluginInput], model: ThirdPartyModel
    ) -> Response[TrainPluginOutput]:
        """Since trainable can't be assumed to be asynchronous, the trainer is responsible for uploading its own model file."""
        logging.debug(f"train {request}")

        # Create a Response object at the top with a Task attached. This will let us stream back updates
        # TODO: This is very non-intuitive. We should improve this.
        response = Response(status=Task(task_id=request.task_id))

        # Train the model
        train_plugin_input = request.data
        train_plugin_output = model.train(train_plugin_input)

        # Set the response on the `data` field of the object
        response.set_data(json=train_plugin_output)
        logging.info(response.dict(by_alias=True))
        return response

    def train_status(
        self, request: PluginRequest[TrainStatusPluginInput], model: ThirdPartyModel
    ) -> Response[TrainPluginOutput]:
        """Since trainable can't be assumed to be asynchronous, the trainer is responsible for uploading its own model file."""
        logging.debug(f"train {request}")

        # Create a Response object at the top with a Task attached. This will let us stream back updates
        # TODO: This is very non-intuitive. We should improve this.
        response = Response(status=Task(task_id=request.task_id))

        # Call train status
        train_plugin_output = model.train_status(request.data)

        if train_plugin_output.training_complete:
            # Save the model with the `default` handle.
            archive_path_in_steamship = model.save_remote(
                client=self.client, plugin_instance_id=request.plugin_instance_id
            )

            # Set the model location on the plugin output.
            train_plugin_output.archive_path = archive_path_in_steamship

        # Set the response on the `data` field of the object
        response.set_data(json=train_plugin_output)
        logging.info(response.dict(by_alias=True))
        return response


handler = create_handler(ThirdPartyTrainableTaggerPlugin)
