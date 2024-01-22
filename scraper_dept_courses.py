"""Scrapes data on undergraduate programs at UNC.

1) List departments
3) Extract information on courses within departments

More resources for parsing:
https://beautiful-soup-4.readthedocs.io/
https://stackoverflow.com/questions/1080411/retrieve-links-from-web-page-using-python-and-beautifulsoup 

More resources for working with CSVs:
https://docs.python.org/3/library/csv.html
"""


import httplib2
from bs4 import BeautifulSoup, SoupStrainer
import csv
import re


http = httplib2.Http()
CATALOG_BASE_URL = "https://catalog.unc.edu"
APPEND_MODE = "a"  # append


def main():
    """Entrypoint to the program."""
    all_dept_links = get_sublinks("/courses/#text", "atozindex", "courses")
    all_dept_names = list(all_dept_links.keys())

    current_dept_index = 0
    while current_dept_index <len(all_dept_links):
        dept = all_dept_names[current_dept_index]

        all_general = []
        all_prereqs = []
        all_coreqs = []

        course_info = extract_courses_and_reqs(all_dept_links[dept],
                                                    "courseblock",
                                                    {
                                                        "department": dept
                                                    })
        
        all_general += course_info["general"]
        all_prereqs += course_info["prereqs"]
        all_coreqs += course_info["coreqs"]

        write_dicts_to_csv("general", all_general, not bool(current_dept_index))
        write_dicts_to_csv("prereqs", all_prereqs, not bool(current_dept_index))
        write_dicts_to_csv("coreqs", all_coreqs, not bool(current_dept_index))
        
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

def extract_courses_and_reqs(resource_path: str, course_container_id: str, base_data: dict[str, str] = {}):
    """Extract course info."""

    status, response = http.request(CATALOG_BASE_URL + resource_path)

    soup_general = BeautifulSoup(response, features="html.parser")
    courses = soup_general.find_all("div", course_container_id)

    result_general = []
    result_prereqs = []
    result_coreqs = []
    for course in courses:
        course_id = course.find("span", "text detail-code margin--tiny text--semibold text--big").get_text()[:-1].replace(" ", "")
        course_name = course.find("span", "text detail-title margin--tiny text--semibold text--big").get_text()[:-1]
        credit_hours = course.find("span", "text detail-hours margin--tiny text--semibold text--big").get_text()[0]  # assume single digit
        
        course_description = ""
        course_description_soup = course.find("p", "courseblockextra")
        if course_description_soup is not None:
            course_description = course_description_soup.get_text().strip()
        
        requisites = course.find("span", "text detail-requisites margin--default")
        prerequisites = []
        corequisites = []
        if requisites is not None:
            siblings = [sibling for sibling in requisites.span.next_siblings]
            i = 0
            prereqs_flag = 0
            coreqs_flag = 0
            req_dept = ""
            while i < len(siblings):
                temp_string = repr(siblings[i])
                if "href" in temp_string:  # only picks up linked courses
                    req_course = siblings[i].get_text().replace("\xa0", "").encode("ascii", "ignore").decode()
                    req_course_id = ""
                    if not req_course.isnumeric():
                        course_info = re.split('(\d+)', req_course)
                        req_dept = course_info[0]
                        req_course_id = req_course
                    else:
                        req_course_id = req_dept + req_course
                    
                    if prereqs_flag:
                        prerequisites.append(req_course_id)
                    elif coreqs_flag:
                        corequisites.append(req_course_id)

                elif "Prerequisite" in temp_string or "prerequisite" in temp_string:
                    prereqs_flag = 1
                elif "Corequisite" in temp_string or "corequisite" in temp_string:
                    prereqs_flag = 0
                    coreqs_flag = 1
                i += 1
        
        current_general = {}
        current_general.update(base_data)
        current_general.update({"course_id": course_id})
        current_general.update({"course_name": course_name})
        current_general.update({"credit_hours": credit_hours})
        current_general.update({"course_description": course_description})
        result_general.append(current_general)

        for prereq in prerequisites:
            result_prereqs.append({
                "course_id": course_id,
                "prereq_id": prereq
            })
        
        for coreq in corequisites:
            result_coreqs.append({
                "course_id": course_id,
                "coreq_id": coreq
            }) 

    all_data = {
        "general": result_general,
        "prereqs": result_prereqs,
        "coreqs": result_coreqs
    }

    # print(all_data)

    return all_data


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
