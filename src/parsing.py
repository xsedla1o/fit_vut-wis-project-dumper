from typing import Generator, Optional

from bs4 import BeautifulSoup

from .http import Connection


class Parser:

    def __init__(self, page_content: str):
        self.content = BeautifulSoup(page_content, "html5lib")


class StudyParser(Parser):

    def get_course_names_and_links(self) -> Generator[tuple[str, str], None, None]:
        course_entries = self.content.select(".content > .table-holder tr[align='center'][valign='top']")
        for entry in course_entries:
            yield entry.find("th").text, entry.select_one("a.bar")["href"]


class CourseParser(Parser):

    def get_task_names_and_links(self) -> Generator[tuple[str, str], None, None]:
        task_links = self.content.select(".content > form > .table-holder a.bar")
        for link in task_links:
            yield link.text, link["href"]

    def get_course_materials_link(self):
        links = self.content.select(".content > ul.nomargin > li > a")
        material_link = None
        for link in links:
            if link.text == 'Soubory k předmětu':
                material_link = link
                break
        if material_link is None:
            return None
        return material_link["href"]


def chunk(iterable, chunk_size):
    return (iterable[i * chunk_size:(i + 1) * chunk_size]
            for i in range((len(iterable) + chunk_size - 1) // chunk_size))


class MaterialsParser(Parser):
    def get_materials_subpage_links(self):
        form_cells = self.content.select(".content > form > .table-holder > table.stbl > tbody > tr > td")[9:]
        table_rows = chunk(form_cells, 6)
        for _, _, _, cz_link, vel, _ in table_rows:
            if int(vel.text[:-1]) > 0:
                link = next(iter(cz_link.children))
                yield link.text, link["href"]


class MaterialsSubpagesParser(Parser):

    def __init__(self, page_content: str, connection: Connection):
        super().__init__(page_content)
        self.connection = connection

    def get_material_download_links(self):
        form_cells = self.content.select(".content > form > .table-holder > table.stbl > tbody > tr > td")[11:]
        table_rows = chunk(form_cells, 7)
        for _, _, _, link, _, vel, _ in table_rows:
            link = next(iter(link.children))
            if vel.text.endswith('.'):
                subpage_content = self.connection.get_content(link['href'])
                for link_text, link_href in MaterialsSubpagesParser(subpage_content,
                                                                    self.connection).get_material_download_links():
                    yield f"{link.text}/{link_text}", link_href
            else:
                yield link.text, link["href"]


class TaskParser(Parser):

    def try_get_files_link(self) -> Optional[str]:
        task_links = self.content.select(".content > p > a")
        for link in task_links:
            link_target = link["href"]
            if "course-sf.php" in link_target:
                return link_target

        return None


class TaskFilesParser(Parser):

    def get_file_names_and_links(self) -> Generator[tuple[str, str, str], None, None]:
        year = self.content.find("h1").text.rsplit("/", maxsplit=1)[-1]
        file_links = self.content.select(".content > form > table tr[valign='middle'] > td > a")
        for link in file_links:
            yield link.text, year, link["href"]

        return None
