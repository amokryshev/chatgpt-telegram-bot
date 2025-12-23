import os
import time
from itertools import islice
from typing import Dict

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .plugin import Plugin


class DDGWebSearchPlugin(Plugin):
    """
    A plugin to search the web for a given query, using DuckDuckGo
    """
    def __init__(self):
        self.safesearch = os.getenv('DUCKDUCKGO_SAFESEARCH', 'moderate')

    def get_source_name(self) -> str:
        return "DuckDuckGo"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "web_search",
            "description": "Execute a web search for the given query and return a list of results",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "the user query"
                    },
                    "region": {
                        "type": "string",
                        "enum": ['xa-ar', 'xa-en', 'ar-es', 'au-en', 'at-de', 'be-fr', 'be-nl', 'br-pt', 'bg-bg',
                                 'ca-en', 'ca-fr', 'ct-ca', 'cl-es', 'cn-zh', 'co-es', 'hr-hr', 'cz-cs', 'dk-da',
                                 'ee-et', 'fi-fi', 'fr-fr', 'de-de', 'gr-el', 'hk-tzh', 'hu-hu', 'in-en', 'id-id',
                                 'id-en', 'ie-en', 'il-he', 'it-it', 'jp-jp', 'kr-kr', 'lv-lv', 'lt-lt', 'xl-es',
                                 'my-ms', 'my-en', 'mx-es', 'nl-nl', 'nz-en', 'no-no', 'pe-es', 'ph-en', 'ph-tl',
                                 'pl-pl', 'pt-pt', 'ro-ro', 'ru-ru', 'sg-en', 'sk-sk', 'sl-sl', 'za-en', 'es-es',
                                 'se-sv', 'ch-de', 'ch-fr', 'ch-it', 'tw-tzh', 'th-th', 'tr-tr', 'ua-uk', 'uk-en',
                                 'us-en', 'ue-es', 've-es', 'vn-vi', 'wt-wt'],
                        "description": "The region to use for the search. Infer this from the language used for the"
                                       "query. Default to `wt-wt` if not specified",
                    }
                },
                "required": ["query", "region"],
            },
        }]

    @retry(
        retry=retry_if_exception_type(DDGSException),
        wait=wait_exponential(multiplier=1, min=2, max=6),
        stop=stop_after_attempt(2)
    )
    def _perform_search(self, query: str, region: str) -> list:

        time.sleep(int(os.environ.get('DICKDUCKGO_TENANCY', 10)))

        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(
                query,
                region=region,
                safesearch=self.safesearch,
                max_results=5
            )
            results = list(islice(ddgs_gen, 3))
            return results

    async def execute(self, function_name, helper, **kwargs) -> Dict:
        query = kwargs['query']
        region = kwargs.get('region', 'wt-wt')

        try:
            results = self._perform_search(query, region)
        except DDGSException:
            return {"Result": "No good DuckDuckGo Search Result was found due to rate limits"}

        if not results:
            return {"Result": "No good DuckDuckGo Search Result was found"}

        def to_metadata(result: Dict) -> Dict[str, str]:
            return {
                "snippet": result.get("body", ""),
                "title": result.get("title", ""),
                "link": result.get("href", ""),
            }

        return {"result": [to_metadata(result) for result in results]}
