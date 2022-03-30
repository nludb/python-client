import base64
import logging
from dataclasses import dataclass
from typing import Dict, Any

from steamship.base.mime_types import TEXT_MIME_TYPES
from steamship.base import Client


@dataclass
class RawDataPluginInput:
    pluginInstance: str = None
    data: Any = None
    defaultMimeType: str = None

    @staticmethod
    def from_dict(d: any, client: Client = None) -> "RawDataPluginInput":
        logging.info("RawDataPluginInput.fromDict {} {}".format(type(d), d))
        data = d.get('data', None)
        if data is not None and d.get('isBase64', False):
            data_bytes = base64.b64decode(data)
            if d.get('defaultMimeType', None) in TEXT_MIME_TYPES:
                data = data_bytes.decode('utf-8')
            else:
                data = data_bytes

        return RawDataPluginInput(
            pluginInstance=d.get('pluginInstance', None),
            data=data,
            defaultMimeType=d.get('defaultMimeType', None)
        )