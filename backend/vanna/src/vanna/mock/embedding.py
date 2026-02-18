from typing import List

from ..base import VannaBase
import logging
logger = logging.getLogger(__name__)


class MockEmbedding(VannaBase):
    def __init__(self, config=None):
        pass

    def generate_embedding(self, data: str, **kwargs) -> List[float]:
        return [1.0, 2.0, 3.0, 4.0, 5.0]
