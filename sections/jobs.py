from copy import deepcopy
import inspect
import os
import logging
import json


class JobsManager:

    PARAM_TEMPLATES = {
        "gantry": {
            "goto": {"x": 0, "y": 0, "z": 0, "a": 0, "speed": 2000},
            "step": {"x": 0, "y": 0, "z": 0, "r": 0, "speed": 1000},
            "unlock": {},
            "attach": {},
            "detach": {},
        },
        "cobot280": {
            "goto": {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0},
            "step": {"j1": 0, "j2": 0, "j3": 0, "j4": 0, "j5": 0, "j6": 0},
        },
        "gripper": {
            "open": {},
            "close": {},
            "speedUp": {},
            "speedDown": {},
        },
        "screwdriver": {
            "screwIn": {},
            "screwOut": {},
        }
    }

    def __init__(self):
        """ jobs[id] = {"id": "", "machine": "gantry", "action": "step", "params": {}"""
        self.jobs_file = ""
        self._job_counter = 0
        self.jobs = {}

    def get_default_params(self, machine: str, action: str) -> dict:
        try:
            return deepcopy(self.PARAM_TEMPLATES[machine][action])
        except KeyError:
            return {}

    def load(self, jobs_file):
        self.jobs_file = jobs_file
        if jobs_file and os.path.isfile(jobs_file):
            try:
                with open(jobs_file, "r") as f:
                    self.jobs = json.load(f)
                    logging.info(f"Loaded {jobs_file}")
            except json.JSONDecodeError:
                print(f"Invalid JSON in jobs file: {jobs_file}")
                self.jobs = {}
            except Exception as e:
                print(f"Error loading jobs file: {e}")
                self.jobs = {}
        else:
            print("Jobs file path is empty or invalid")
            self.jobs = {}
        return self
    
    def add_job(self):
        new_id = self._job_counter
        self._job_counter += 1
        new_job = {
            "id": new_id,
            "machine": "gantry",
            "action": "step",
            "params": {"x": 0,"y": 5,"z": 0,"a": 0,"speed": 3000},
        }
        self.jobs[new_id] = new_job
        return new_id
    
    def update_job(self,job):
        # Assign new ID if missing
        # if not job_id or job_id == "" or job_id == '':
        #     self._job_counter += 1
        #     job["id"] = f"J{self._job_counter}"
        self.jobs[job["id"]] = job
        return job['id']
    
    def delete_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            del self.jobs[job_id]
            return True
        return False
    
    async def run_job(self, job, machine):
        """ """

        action = job['action']
        params = job['params']

        method = getattr(machine, action, None)
        if not method:
            print(f"⚠ Method missing on machine: {machine}.{action}")
            return

        result = method(params)

        if inspect.isawaitable(result):
            return await result

        return result

    # -------------------------
    # macro runner helper
    # -------------------------

    async def run_jobs(self, jobs: list, machines):
        for job in jobs:
            await self.run_action(job)
