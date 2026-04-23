import os
from time import sleep
import requests

from dotenv import load_dotenv

BASE_AUTH_URL = "https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token"
BASE_API_URL = "https://api.strata.paloaltonetworks.com"


HEADERS = {
    "Accept": "application/json",
}

AUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
}

# Time to sleep between requests in seconds.
SLEEP_TIME = 15

load_dotenv()
TSG_ID = os.environ.get("TSG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
SECRET_ID = os.environ.get("SECRET_ID")


def create_token():
    auth_url = f"{BASE_AUTH_URL}?grant_type=client_credentials&scope:tsg_id:{TSG_ID}"

    token = requests.request(
        method="POST",
        url=auth_url,
        headers=AUTH_HEADERS,
        auth=(CLIENT_ID, SECRET_ID),
    ).json()
    HEADERS.update({"Authorization": f'Bearer {token["access_token"]}'})


def make_commit():
    url = f"{BASE_API_URL}/config/operations/v1/config-versions/candidate:push"
    payload = {"folders": ["All"], "description": "Commit from API"}
    return requests.request(
        method="POST", url=url, headers=HEADERS, json=payload
    ).json()


def get_commit_jobs():
    url = f"{BASE_API_URL}/config/operations/v1/jobs"
    return requests.request(method="GET", url=url, headers=HEADERS).json()


def get_specific_job(job_id):
    url = f"{BASE_API_URL}/config/operations/v1/jobs/{job_id}"
    return requests.request(method="GET", url=url, headers=HEADERS).json()


if __name__ == "__main__":
    create_token()

    # Make the initial commit and get the parent job ID.
    commit_response = make_commit()
    parent_job = commit_response["job_id"]
    status_payload = get_specific_job(job_id=parent_job)
    status = status_payload["data"][0]["result_str"]
    print(f"Parent job {parent_job} status: {status}")
    print("-" * 50)

    # Monitor the parent job until it is no longer pending.
    while status == "PEND":
        sleep(SLEEP_TIME)
        status_payload = get_specific_job(job_id=commit_response["job_id"])
        status = status_payload["data"][0]["result_str"]
        print(f"Parent job {parent_job} status: {status}")
        print("-" * 50)

    # Get all child jobs that are associated with the parent job and create a list of their IDs.
    child_jobs = []
    if status == "OK":
        all_jobs = get_commit_jobs()
        child_jobs.extend(
            x["id"] for x in all_jobs["data"] if x["parent_id"] == parent_job
        )

    # Loop through the child jobs and monitor their status until they are all complete.
    while child_jobs != []:
        for job in sorted(child_jobs):
            status_payload = get_specific_job(job_id=job)
            status = status_payload["data"][0]["result_str"]
            print(f"Child job {job} status: {status}")
            print("-" * 50)
            if status != "OK":
                sleep(SLEEP_TIME)
                break
            else:
                child_jobs.remove(job)
