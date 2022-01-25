from typing import List
from dataclasses import dataclass
from steamship.types.base import Request, Model
from steamship.types.search import Hit
from steamship.client.base import ApiBase 

@dataclass
class EmbedRequest(Request):
  docs: List[str]
  model: str

@dataclass
class EmbedResponse(Model):
  embeddings: List[List[float]]

  @staticmethod
  def safely_from_dict(d: any, client: ApiBase = None) -> "EmbedResponse":
    return EmbedResponse(
      embeddings = d.get('embeddings', None),
    )

@dataclass
class EmbedAndSearchRequest(Request):
  query: str
  docs: List[str]
  model: str
  k: int = 1

@dataclass
class EmbedAndSearchResponse(Request):
  hits: List[Hit] = None

  @staticmethod
  def safely_from_dict(d: any, client: ApiBase = None) -> "EmbedAndSearchResponse":
    hits = [Hit.safely_from_dict(h) for h in (d.get("hits", []) or [])]
    return EmbedAndSearchResponse(
      hits=hits
    )
