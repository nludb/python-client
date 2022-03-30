import logging
from typing import List

from steamship.base import Client, Response
from steamship.client.tasks import Tasks
from steamship.data import File
from steamship.data.embeddings import EmbedAndSearchRequest, EmbedAndSearchResponse, EmbedRequest, EmbedResponse
from steamship.data.embedding_index import EmbeddingIndex
from steamship.data.space import Space

__copyright__ = "Steamship"
__license__ = "MIT"

from steamship.extension.file import TagResponse
from steamship.plugin.tagger import TagRequest

_logger = logging.getLogger(__name__)


class Steamship(Client):
    """Steamship Python Client."""

    def __init__(
            self,
            apiKey: str = None,
            apiBase: str = None,
            appBase: str = None,
            spaceId: str = None,
            spaceHandle: str = None,
            profile: str = None,
            configFile: str = None,
            configDict: dict = None,
            dQuery: bool = False):
        super().__init__(
            apiKey=apiKey,
            apiBase=apiBase,
            appBase=appBase,
            spaceId=spaceId,
            spaceHandle=spaceHandle,
            profile=profile,
            configFile=configFile,
            configDict=configDict,
            dQuery=dQuery)
        """
        The base.py class will properly detect and set the defaults. They should be None here.
    
        dQuery is a Beta option that will return chainable responses, like:
          file.upload()
              .convert()
              .parse()
              .embed()
              .query()
    
        It offers no new functionality -- in fact at the moment it's slightly less in that you 
        are given the syntactically convenient response object for chaining rather than the actual
        response object of the invocation.
        """
        self.tasks = Tasks(self)

    def create_index(
            self,
            handle: str = None,
            name: str = None,
            plugin: str = None,
            upsert: bool = True,
            externalId: str = None,
            externalType: str = None,
            metadata: any = None,
            spaceId: str = None,
            spaceHandle: str = None,
            space: Space = None
    ) -> Response[EmbeddingIndex]:
        return EmbeddingIndex.create(
            client=self,
            handle=handle,
            name=name,
            plugin=plugin,
            upsert=upsert,
            externalId=externalId,
            externalType=externalType,
            metadata=metadata,
            spaceId=spaceId,
            spaceHandle=spaceHandle,
            space=space
        )

    # def create_classifier(
    #         self,
    #         name: str,
    #         plugin: str,
    #         upsert: bool = True,
    #         save: bool = None,
    #         labels: List[str] = None,
    #         spaceId: str = None,
    #         spaceHandle: str = None,
    #         space: Space = None
    # ) -> Classifier:
    #     return Classifier.create(
    #         client=self,
    #         plugin=plugin,
    #         name=name,
    #         upsert=upsert,
    #         save=save,
    #         labels=labels,
    #         spaceId=spaceId,
    #         spaceHandle=spaceHandle,
    #         space=space
    #     )

    def upload(
            self,
            filename: str = None,
            name: str = None,
            content: str = None,
            mimeType: str = None,
            plugin: str = None,
            spaceId: str = None,
            spaceHandle: str = None,
            space: Space = None
    ) -> File:
        return File.create(
            self,
            filename=filename,
            name=name,
            content=content,
            mimeType=mimeType,
            spaceId=spaceId,
            spaceHandle=spaceHandle,
            space=space
        )

    def scrape(
            self,
            url: str,
            name: str = None,
            spaceId: str = None,
            spaceHandle: str = None,
            space: Space = None,
    ) -> File:
        if name is None:
            name = url
        return File.scrape(
            self,
            url,
            name,
            spaceId=spaceId,
            spaceHandle=spaceHandle,
            space=space
        )

    def embed(
            self,
            docs: List[str],
            plugin: str,
            spaceId: str = None,
            spaceHandle: str = None,
            space: Space = None
    ) -> Response[EmbedResponse]:
        req = EmbedRequest(
            docs=docs,
            plugin=plugin
        )
        return self.post(
            'embedding/create',
            req,
            expect=EmbedResponse,
            spaceId=spaceId,
            spaceHandle=spaceHandle,
            space=space
        )

    def embed_and_search(
            self,
            query: str,
            docs: List[str],
            plugin: str,
            k: int = 1,
            spaceId: str = None,
            spaceHandle: str = None,
            space: Space = None
    ) -> Response[EmbedAndSearchResponse]:
        req = EmbedAndSearchRequest(
            query=query,
            docs=docs,
            plugin=plugin,
            k=k
        )
        return self.post(
            'embedding/search',
            req,
            expect=EmbedAndSearchResponse,
            spaceId=spaceId,
            spaceHandle=spaceHandle,
            space=space
        )

    def parse(
            self,
            docs: List[str],
            pluginInstance: str = None,
            includeTokens: bool = True,
            includeParseData: bool = True,
            includeEntities: bool = False,
            metadata: any = None,
            spaceId: str = None,
            spaceHandle: str = None,
            space: Space = None
    ) -> Response[TagResponse]:
        req = TagRequest(
            type="inline",
            docs=docs,
            pluginInstance=pluginInstance,
            includeTokens=includeTokens,
            includeParseData=includeParseData,
            includeEntities=includeEntities,
            metadata=metadata
        )
        return self.post(
            'plugin/instance/tag',
            req,
            expect=TagResponse,
            spaceId=spaceId,
            spaceHandle=spaceHandle,
            space=space
        )
