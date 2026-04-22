import os
from time import sleep
import requests

from dotenv import load_dotenv

BASE_AUTH_URL = "https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token"
BASE_API_URL = "https://api.strata.paloaltonetworks.com"


HEADERS = {
    "Accept": "application/json",
}

FOLDER = "Remote Networks"

AUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
}

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
    response = requests.request(
        method="POST", url=url, headers=HEADERS, json=payload
    ).json()
    return response


def get_commit_jobs():
    url = f"{BASE_API_URL}/config/operations/v1/jobs"
    response = requests.request(method="GET", url=url, headers=HEADERS).json()
    return response


def get_specific_job(job_id):
    url = f"{BASE_API_URL}/config/operations/v1/jobs/{job_id}"
    response = requests.request(method="GET", url=url, headers=HEADERS).json()
    return response


if __name__ == "__main__":
    create_token()
    commit_response = make_commit()
    parent_job = commit_response["job_id"]
    status_payload = get_specific_job(job_id=commit_response["job_id"])
    status = status_payload["data"][0]["result_str"]
    print(f"Parent job status: {status}")
    print("-" * 50)
    while status == "PEND":
        status_payload = get_specific_job(job_id=commit_response["job_id"])
        status = status_payload["data"][0]["result_str"]
        print(status)
        print("-" * 50)
        sleep(15)

    parent_jobs = []
    if status == "OK":
        all_jobs = get_commit_jobs()
        for x in all_jobs["data"]:
            if x["parent_id"] == parent_job:
                parent_jobs.append(x["id"])

    while parent_jobs != []:
        for job in sorted(parent_jobs):
            status_payload = get_specific_job(job_id=job)
            status = status_payload["data"][0]["result_str"]
            print(f"Job {job} has status: {status}")
            print("-" * 50)
            if status != "OK":
                sleep(15)
                break
            else:
                parent_jobs.remove(job)
