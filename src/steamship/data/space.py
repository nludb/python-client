<<<<<<< HEAD
import logging
from dataclasses import dataclass
=======
from __future__ import annotations

>>>>>>> main
from typing import Any

from pydantic import BaseModel

from steamship.base import Client, Request, Response
from steamship.base.request import GetRequest, IdentifierRequest
from enum import Enum
from steamship.utils.localstack import apply_localstack_url_fix

class SignedUrl:
    class Bucket(str, Enum):
        EXPORTS = "exports"
        IMPORTS = "imports"
        USER_DATA = "userData"
        PLUGIN_DATA = "pluginData"
        APP_DATA = "appData"

    class Operation(str, Enum):
        READ = "Read"
        WRITE = "Write"

    class Request(Request):
        bucket: "SignedUrl.Bucket"
        filepath: str
        operation: "SignedUrl.Operation"
        expiresInMinutes: int = None

    class Response(Response):
        bucket: str = None
        filepath: str = None
        operation: str = None
        expiresInMinutes: int = None
        signedUrl: str = None

        @staticmethod
        def from_dict(d: dict, client: Client):
            if d is None:
                return None
            return SignedUrl.Response(
                bucket=d.get("bucket"),
                filepath=d.get("filepath"),
                operation=d.get("operation"),
                expiresInMinutes=d.get("expiresInMinutes"),
                signedUrl=d.get("signedUrl"),
            )


class Space(BaseModel):
    client: Client = None
    id: str = None
    handle: str = None

    class CreateRequest(Request):
        id: str = None
        handle: str = None
        upsert: bool = None
        externalId: str = None
        externalType: str = None
        metadata: str = None

    class ListRequest(Request):
        pass

    def delete(self) -> Response[Space]:
        return self.client.post("space/delete", IdentifierRequest(id=self.id), expect=Space)

    @staticmethod
    def from_dict(d: Any, client: Client) -> Space:
        if "space" in d:
            d = d["space"]

        return Space(client=client, id=d.get("id"), handle=d.get("handle"))

    @staticmethod
    def get(
        client: Client,
        id_: str = None,
        handle: str = None,
        upsert: bool = None,
        space_id: str = None,
        space_handle: str = None,
        space: "Space" = None,
    ) -> Response[Space]:
        req = GetRequest(id=id_, handle=handle, upsert=upsert)
        return client.post(
            "space/get",
            req,
            expect=Space,
            space_id=space_id,
            space_handle=space_handle,
            space=space,
        )

    @staticmethod
    def create(
        client: Client,
        handle: str,
        external_id: str = None,
        external_type: str = None,
        metadata: Any = None,
        upsert: bool = True,
    ) -> Response[Space]:
        req = Space.CreateRequest(
            handle=handle,
            upsert=upsert,
            externalId=external_id,
            externalType=external_type,
            metadata=metadata,
        )
        return client.post("space/create", req, expect=Space)

    def create_signed_url(self, request: SignedUrl.Request) -> Response[SignedUrl.Response]:
        import requests
        logging.info(f"Requesting signed URL: {request}")
        ret = self.client.post("space/createSignedUrl", payload=request, expect=SignedUrl.Response)
        logging.info(f"Got signed URL: {ret}")
        return ret
