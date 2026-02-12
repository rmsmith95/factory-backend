import os
import json
import logging


class PartsManager:
    def __init__(self):
        self.parts = {}
        self.parts_file = ""
    
    def load(self, parts_file):
        """Load parts"""
        self.parts_file = parts_file
        if parts_file and os.path.isfile(parts_file):
            try:
                with open(parts_file, "r") as f:
                    self.parts = json.load(f)
                    logging.info(f"Loaded {parts_file}")
            except json.JSONDecodeError:
                print(f"Invalid JSON in parts file: {parts_file}")
                self.parts = {}
            except Exception as e:
                print(f"Error loading parts file: {e}")
                self.parts = {}
        else:
            print("Parts file path is empty or invalid")
            self.parts = {}
