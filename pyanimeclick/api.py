import httpx
import re

from bs4 import BeautifulSoup
from bs4.element import Tag
from httpx._models import Response
from typing import Dict, List, Optional

from .errors import *
from .types import *
from .utils import *

class AnimeClick:
        
    @classmethod
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Dict=None,
    ) -> Optional[Response]:
        async with httpx.AsyncClient() as session:
            r = await session.request(
                    method=method,
                    url=url,
                    headers=headers(),
                    cookies=cookies(),
                    params=params,
                    follow_redirects=True
                )

            code = r.status_code
            if code != 200:
                raise RequestError(f"[{code}] {r.text}")
            if "AnimeClick.it ....dove sei?!" in r.text:
                raise InvalidCode(f"Il codice inserito non è valido.")
            return r

    async def search(self, query: str) -> List[Result]:
        r = await self._make_request(
            "GET", SEARCH_PAGE,
            params={"name": query}
        )
        soup = BeautifulSoup(r.text, "lxml")
        tab = soup.find("h3", {"id": "type-opera"}).find_next("div")
        operas: List[Tag] = tab.find_all("div", {
            "class": "col-xs-12 col-sm-12 col-md-6 col-lg-4"
        })
        results = list()
        for opera in operas:
            left = opera.find("div", {"class": "media-left"})
            body = opera.find("div", {"class": "media-body"})
            data = dict()
            data["title"] = body.find("a").text.strip()
            data["url"] = BASE_URL + body.find("a")["href"].strip()
            data["id"] = int(body.find("a")["href"].split("/")[-2].strip())
            data["thumb"] = BASE_URL + left.find("img")["src"].replace("-thumb-mini", "")
            data["type"] = "manga" if body.find(text="tipo opera: Fumetto") else "anime"
            data["year"] = int(re.search(r"(\d{4})", body.find(text=re.compile("anno inizio:")).strip()).group(1))
            results.append(data)
            
        return [Result(**result) for result in results]

    async def get_anime(self, id: int) -> Anime:
        r = await self._make_request(
            "GET", ANIME_PAGE.format(str(id))
        )
        main = BeautifulSoup(r.text, "lxml")
        r = await self._make_request(
            "GET", ANIME_PAGE.format(str(id)) + "/staff"
        )
        staff = BeautifulSoup(r.text, "lxml")
        r = await self._make_request(
            "GET", ANIME_PAGE.format(str(id)) + "/episodi"
        )
        episodes = r.text

        data = dict()
        if title := main.find(text="Titolo inglese"):
            data["title"] = title.find_next("span").text.strip()
        if original_title := main.find(text="Titolo originale"):
            data["original_title"] = original_title.find_next("span").text.strip()
        if short_title := main.find(text="Titolo breve"):
            data["short_title"] = short_title.find_next("span").text.strip()
        if italian_name := main.find("div", {"class": "page-header"}):
            data["italian_name"] = italian_name.find("h1").text
        if year := main.find(text="Anno"):
            data["year"] = int(year.find_next("dd").a.text.strip())
        if genres := main.find(text="Genere"):
            data["genres"] = [
                genre.text.strip()
                for genre in genres.find_next("dd").find_all("a")
            ]
        if overview := main.find("div", {"id": "trama-div"}):
            data["overview"] = overview.text.replace("Trama: ", "").strip()
        if animations := staff.find(text="Animazioni"):
            data["animations"] = [
                studio.a.text for studio in
                animations.find_next(
                    "div", {"class": "well"}
                ).div.find_all("h4", {"class": "media-heading"})
            ]
        durations = [
            int(i) for i
            in re.findall(r"(\d{1,3})\&\#39", episodes)
        ]
        if len(durations) != 0:
            data["average_duration"] = int(sum(durations) // len(durations))
        data["thumb"] = BASE_URL + main.find("img", {"alt": "copertina"})["src"]
        
        return Anime(**data)
    
    async def get_manga(self, id: int) -> Anime:
        r = await self._make_request(
            "GET", MANGA_PAGE.format(str(id))
        )
        main = BeautifulSoup(r.text, "lxml")

        data = dict()
        if title := main.find(text="Titolo inglese"):
            data["title"] = title.find_next("span").text.strip()
        if original_title := main.find(text="Titolo originale"):
            data["original_title"] = original_title.find_next("span").text.strip()
        if short_title := main.find(text="Titolo breve"):
            data["short_title"] = short_title.find_next("span").text.strip()
        if italian_name := main.find("div", {"class": "page-header"}):
            data["italian_name"] = italian_name.find("h1").text
        if nationatlity := main.find(text="Nazionalità"):
            data['nationality'] = nationatlity.find_next("span").text.strip()
        if category := main.find(text='Categoria'):
            data['category'] = category.find_next('a').text.strip()
        if year := main.find(text="Anno"):
            data["year"] = int(year.find_next("dd").a.text.strip())
        if genres := main.find(text="Genere"):
            data["genres"] = [
                genre.text.strip()
                for genre in genres.find_next("dd").find_all("a")
            ]
        if status := main.find(text="Stato in Italia"):
            data['status'] = status.find_next("dd").text.strip()
        if overview := main.find("div", {"id": "trama-div"}):
            data["overview"] = overview.text.replace("Trama: ", "").strip()
        data["thumb"] = BASE_URL + main.find("img", {"alt": "copertina"})["src"]
        
        return Manga(**data)
