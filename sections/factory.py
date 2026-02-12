from typing import List, Dict
from aabb import AABB, plan_path
import logging
import json
from machines.gantry import Gantry
from machines.cobot280 import Cobot280
from machines.gripper import ST3020Gripper
from machines.arduino import Arduino
from .jobs import JobsManager
from .parts import PartsManager
import os


class Factory:
    """
    Represents a factory workspace with machines, parts and jobs.
    Provides methods to add them to the factory
    """

    def __init__(self):
        self.machines = {'gantry': Gantry(), 'cobot280': Cobot280(), 'gripper': ST3020Gripper(), 'arduino': Arduino()}
        self.parts_manager = PartsManager()
        self.jobs_manager = JobsManager()
        self.tools: Dict[str, dict] = {}
        self.save_file = ""
    
    @property
    def jobs(self):
        return self.jobs_manager.jobs
    
    @property
    def parts(self):
        return self.parts_manager.parts

    def load_factory(self, file):
        self.save_file = file
        with open(file, "r") as f:
            data = json.load(f)
        
        machines = data.get("machines", {})
        gantry = machines['gantry']
        self.machines = {'gantry': Gantry(), 'cobot280': Cobot280(), 'gripper': ST3020Gripper(), 'arduino': Arduino()}
        self.machines['gantry'].holders = gantry['holders']
        self.machines['gantry'].locations = gantry['locations']
        self.machines['gantry'].toolend = gantry['toolend']
        self.machines['gantry'].set_position(**self.machines['gantry'].toolend['position'])
        self.tools = data.get("tools", {})

        # Load jobs
        jobs_file = data.get("jobs")
        self.jobs_manager.load(jobs_file)
        # Load jobs
        parts_file = data.get("parts")
        self.parts_manager.load(parts_file)
        return self

    def save_factory(self):
        if not self.save_file:
            raise RuntimeError("Factory save_file not set")

        data = {
            "parts_file": self.parts_manager.parts_file,
            "jobs_file": self.jobs_manager.jobs_file,
            "machines": {
                'gantry': {
                    'toolend': self.machines['gantry'].toolend, 
                    'holders': self.machines['gantry'].holders,
                    'locations': self.machines['gantry'].locations
                    },
                'cobot280': {'pose': self.machines['cobot280'].pose},
                'gripper': {},
                'arduino': {},
            },
            "tools": self.tools,
        }

        with open(self.save_file, "w") as f:
            json.dump(data, f, indent=2)

        logging.debug(f"Saved Factory, toolend {self.machines['gantry'].toolend}")


    def plot_path(self, machine, target_part):
        workspace = machine['bounds']  # ((0, 300), (0, 200))  # XY bounds

        obstacles = []
        for part in self.parts.values():
            aabb = AABB(part['bounds'])  # (50, 40, 0, 120, 160, 40)
            obstacles.append(aabb)
        
        start = machine['location']  # (10, 10, 0)
        goal = target_part['location']  # (260, 150, 5)
        path = plan_path(start, goal, obstacles, workspace, safe_z=60, step=10, radius=5)
        print("Planned path:")
        for p in path:
            print(p)
        pass

    def add_job(self):
        new_id = self.jobs_manager.add_job()
        self.save_factory()
        logging.info(f'add_job: "{new_id}"')
        return new_id

    def update_job(self, job):
        logging.info(f'update_job: "{job}"')
        self.jobs_manager.update_job(job)
        self.save_factory()
        logging.info(f'update_job: "{job}"')

    def delete_job(self, job_id):
        self.jobs_manager.delete_job(job_id)
        self.save_factory()
        logging.info(f'delete_job: "{job_id}"')
    
    def run_job(self, job_id):
        job = self.jobs[job_id]
        machine_name = job['machine']
        machine = self.machines[machine_name]
        self.jobs_manager.run_job(job, machine)
        self.save_factory()
        logging.info(f'run_job: "{job_id}"')
    
    def run_script(self, path):
        self.jobs_manager.run_script(path)
        self.save_factory()
