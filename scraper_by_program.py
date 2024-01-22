"""Scrapes data on undergraduate programs at UNC.

1) List departments
2) List programs within departments
3) Extract information on opportunities within departments

More resources for parsing:
https://beautiful-soup-4.readthedocs.io/
https://stackoverflow.com/questions/1080411/retrieve-links-from-web-page-using-python-and-beautifulsoup 

More resources for working with CSVs:
https://docs.python.org/3/library/csv.html
"""


import httplib2
from bs4 import BeautifulSoup, SoupStrainer
import csv


http = httplib2.Http()
CATALOG_BASE_URL = "https://catalog.unc.edu"
APPEND_MODE = "a"  # append


def main():
    """Entrypoint to the program."""
    all_dept_links = get_sublinks(
        "/undergraduate/departments/#bydivisiontext", "bydivisiontextcontainer", "undergraduate")
    all_dept_names = list(all_dept_links.keys())

    current_dept_index = 0
    while current_dept_index < len(all_dept_links):
        dept = all_dept_names[current_dept_index]

        all_dept_opportunities = []
        program_links = get_sublinks(
            all_dept_links[dept] + "#programstext", "programstextcontainer", "undergraduate")

        for program_link in program_links:
            program_opportunities = extract_hierarchical_text_info(program_links[program_link],
                                                                   "opportunitiestexttab",
                                                                   "#opportunities",
                                                                   "opportunitiestextcontainer",
                                                                   ["h2", "h3", "p"],
                                                                   {
                                                                        "program": program_link,
                                                                        "department": dept
                                                                    })
            all_dept_opportunities += program_opportunities

        write_dicts_to_csv(
            "opportunity_info", all_dept_opportunities, not bool(current_dept_index))
        
        print("Completed Department of " + dept)
        current_dept_index += 1


def get_sublinks(resource_path: str, container_id: str = "content", links_filter: str = "") -> dict[str, str]:
    """Given a resource_path to the department list, get department links."""

    status, response = http.request(CATALOG_BASE_URL + resource_path)

    soup = BeautifulSoup(response, features="html.parser")
    relevant_soup = soup.find(id=container_id)
    raw_links = relevant_soup.find_all('a')

    links = {}
    for link in raw_links:
        href = str(link.get('href'))
        if links_filter in href:
            links[link.get_text()] = href

    return links


def extract_hierarchical_text_info(resource_path: str, tab_id: str, tab_link: str, container_id: str,
                                   tag_hierarchy_decreasing: list[str], base_data: dict[str, str] = {}) -> list[dict[str, str]]:
    """Extract textual information on program opportunities, if documented in the catalog.

    Return a list of dictionaries, with tags as keys.
    """

    status, response = http.request(CATALOG_BASE_URL + resource_path)

    soup_general = BeautifulSoup(response, features="html.parser")
    find_tab = soup_general.find(id=tab_id)

    result = []
    if find_tab is not None:
        status_subpage, response_subpage = http.request(
            CATALOG_BASE_URL + resource_path + tab_link)
        soup_subpage = BeautifulSoup(response_subpage, features="html.parser")
        relevant_soup_subpage = soup_subpage.find(id=container_id)
        relevant_soup_subpage_as_list = list(relevant_soup_subpage.children)

        working_dictionary = {tag: "" for tag in tag_hierarchy_decreasing}
        working_dictionary.update(base_data)
        previous_index = -1
        i = 0
        while i < len(relevant_soup_subpage_as_list):
            current_tag = relevant_soup_subpage_as_list[i]
            current_tag_type = str(current_tag.name)

            if (current_tag_type is not None) and (current_tag_type in tag_hierarchy_decreasing):
                current_index = tag_hierarchy_decreasing.index(
                    current_tag_type)
                current_text = current_tag.get_text().strip().replace(
                    "\xa0", "").encode("ascii", "ignore").decode()

                if current_index < previous_index:
                    # Add working dictionary to list if coming back from the end of the hierarchy.
                    if previous_index == len(tag_hierarchy_decreasing) - 1:
                        result.append(working_dictionary.copy())
                    # Update working dictionary with current state.
                    working_dictionary.update({current_tag_type: current_text})
                    # Clear children.
                    for index in range(current_index + 1, len(tag_hierarchy_decreasing)):
                        working_dictionary.update(
                            {tag_hierarchy_decreasing[index]: ""})
                elif current_index > previous_index:
                    # Update working dictionary with current state.
                    working_dictionary.update({current_tag_type: current_text})
                    # Clear jumped indices.
                    for index in range(previous_index + 1, current_index):
                        working_dictionary.update(
                            {tag_hierarchy_decreasing[index]: ""})
                else:
                    if current_index == len(tag_hierarchy_decreasing) - 1:
                        # Update dictionary to include current text if at the end of the hierarchy.
                        working_dictionary.update(
                            {current_tag_type: working_dictionary[current_tag_type] + current_text})
                    else:
                        # Update working dictionary with current state.
                        working_dictionary.update(
                            {current_tag_type: current_text})
                        # Add working dictionary to list.
                        result.append(working_dictionary.copy())

                # print("ITEM: " + current_tag_type + ", index: " + str(current_index) + ", text: " + current_text)
                previous_index = current_index

            i += 1

        # Append the last working dictionary to the list.
        result.append(working_dictionary.copy())

    return result


def write_dicts_to_csv(filename: str, data: list[dict[str, str]], write_header):
    """Write data to CSV, if data exists."""
    if len(data) > 0:
        with open(filename + ".csv", APPEND_MODE, newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, data[0].keys())
            if write_header:
                dict_writer.writeheader()
            dict_writer.writerows(data)


if __name__ == "__main__":
    main()
