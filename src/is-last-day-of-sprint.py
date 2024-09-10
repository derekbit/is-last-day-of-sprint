import requests
import os
import sys
from datetime import datetime, timedelta


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def get_github_project_info(github_token, github_org, github_project_number):
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json"
    }
    query = '''
    {
      organization(login: "%s") {
        projectsV2(first: 20) {
          nodes {
            id
            title
            number
          }
        }
      }
    }
    ''' % (github_org)
    payload = {
        "query": query
    }

    response = requests.post(GITHUB_GRAPHQL_URL, headers=headers, json=payload)
    if response.status_code == 200:
        # fine project by number
        nodes = response.json().get("data").get("organization").get("projectsV2").get("nodes")
        for node in nodes:
            if node.get("number") == int(github_project_number):
                return node
    else:
        response.raise_for_status()


def get_current_sprint(github_token, project_id):
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json"
    }
    query = '''
    query {
      node(id: "%s") {
        ... on ProjectV2 {
          fields(first: 20) {
            nodes {
              ... on ProjectV2IterationField {
                configuration {
                  iterations {
                    startDate
                    id
                  }
                }
              }
            }
          }
        }
      }
    }
    ''' % (project_id)

    payload = {
        "query": query
    }

    response = requests.post(GITHUB_GRAPHQL_URL, headers=headers, json=payload)
    if response.status_code == 200:
        # fine project by title
        result = response.json().get("data").get("node").get("fields").get("nodes")
        filtered_result = [node for node in result if 'configuration' in node]
        iterations = filtered_result[0].get("configuration").get("iterations")

        # Find current iteration
        current_date = datetime.now().date()
        current_iteration = None
        for iteration in iterations:
            start_date = datetime.strptime(iteration['startDate'], "%Y-%m-%d").date()
            end_date = start_date + timedelta(days=13)
            if start_date <= current_date <= end_date:
                current_iteration = iteration
                break

        return current_iteration
    else:
        response.raise_for_status()


def is_last_day_of_current_sprint(github_token, project_id, date_str):
    current_iteration = get_current_sprint(github_token, project_id)
    if current_iteration is None:
        print("Current sprint not found")
        return False

    # Convert date_str string to datetime object
    current_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    end_date = datetime.strptime(current_iteration['startDate'], "%Y-%m-%d").date() + timedelta(days=13)

    print("Current date: %s, end date: %s" % (current_date, end_date))

    return current_date == end_date


def github_output(name, value):
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as env:
            env.write(f'{name}={value}')


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print('Usage: python scan_and_notify_testing_items.py github_org github_project_number date')
        sys.exit()

    github_token = os.getenv("GITHUB_TOKEN")

    github_org = sys.argv[1]
    github_project_number = sys.argv[2]
    date_str = sys.argv[3]

    project = get_github_project_info(github_token, github_org, github_project_number)
    print(f"GitHub Project Details: {project}")

    last_day = is_last_day_of_current_sprint(github_token, project.get("id"), date_str)
    github_output("last_day", str(last_day).lower())
