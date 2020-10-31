import requests
import tempfile
import shutil
import pysftp
import os
import threading
import time
import re
import logging
import paramiko

from urllib3.connection import ConnectTimeoutError
from dct.util.model import ModelMetadata, Model


class DeepRacerCar:
    def __init__(self, ip, ssh_password=None, name="Car", verbose=False):
        self.ip = ip
        self.ssh_password = ssh_password
        self.base_url = "https://{}".format(ip)
        self.name = name

        self.carThread = threading.Thread(target=self.monitor)
        self.carThread.daemon = True

        self.logThread = threading.Thread(target=self.roslog)
        self.logThread.daemon = True

        self.tmpdir = tempfile.mkdtemp()

        self.session = requests.Session()
        self.session.verify = False

        self.connected = False

        self.model_name = None
        self.throttle = None
        self.car_driving = None

        self.battery_level = None
        self.camera_status = None
        self.stereo_status = None
        self.lidar_status = None

        self.verbose = verbose

    def __del__(self):
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def roslog(self):
        while True:
            try:
                with paramiko.SSHClient() as client:
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(
                        self.ip, 22, "deepracer", self.ssh_password, timeout=2
                    )

                    stdin, stdout, stderr = client.exec_command(
                        "source /opt/ros/kinetic/setup.bash; rostopic echo /rosout_agg/msg",
                    )

                    for line in iter(lambda: stdout.readline(2048), ""):
                        self._update_log_values(line)
            except Exception as e:
                print(e)
            finally:
                # Retry every 5 seconds.
                time.sleep(5)

    def monitor(self):
        while True:
            try:
                if not self.connected:
                    self._connect()

                # Update battery level
                self._update_battery_level()

                # Update sensor info
                self._update_sensor_status()

                if self.verbose:
                    print(self)

            except Exception as e:
                self.connected = False
                print(e)
                logging.info("Car '{}' disconnected".format(self.name))
            finally:
                # Update every 10 seconds.
                time.sleep(10)

    def __str__(self):
        return "[{}]: Model: {} - Battery: {} - Driving: {} - Throttle: {}%".format(
            self.name,
            self.model,
            self.battery_level,
            self.car_driving,
            self.throttle if self.throttle is not None else "?",
        )

    def connect(self):
        self.carThread.start()
        self.logThread.start()

    def _connect(self):
        try:
            logging.info("Attempting to connect to {}".format(self.name))
            deepracer_token_path = os.path.join(self.tmpdir, "token.txt")

            # Use SSH to get the deepracer token from the cookie.
            with pysftp.Connection(
                self.ip, username="deepracer", password=self.ssh_password
            ) as sftp:
                logging.info("Downloading token for {}".format(self.name))

                sftp.get(
                    "/opt/aws/deepracer/token.txt",
                    deepracer_token_path,
                )

                with open(deepracer_token_path, "r") as f:
                    self.cookie = "deepracer_token={}".format(f.readlines()[0])

            self.session.headers["Cookie"] = self.cookie

            self.connected = True
            logging.info("Car '{}' connected!".format(self.name))
        except ConnectTimeoutError:
            self.connected = False
            logging.info("Timeout connecting to car '{}'".format(self.name))
            return
        except Exception as e:
            logging.debug(e)

    def load_model(self, model_name):
        logging.info(
            "Loading model '{}' from car '{}'' at {}".format(
                model_name, self.name, self.ip
            )
        )

        with pysftp.Connection(
            self.ip, username="deepracer", password=self.ssh_password
        ) as sftp:
            base_path = os.path.join(self.tmpdir, model_name)

            if not os.path.exists(base_path):
                os.makedirs(base_path)

            model_path = os.path.join(self.tmpdir, model_name, "model.pb")
            metadata_path = os.path.join(self.tmpdir, model_name, "model_metadata.json")

            if not os.path.exists(model_path):
                sftp.get(
                    "/opt/aws/deepracer/artifacts/{}/model.pb".format(model_name),
                    model_path,
                )

            if not os.path.exists(metadata_path):
                sftp.get(
                    "/opt/aws/deepracer/artifacts/{}/model_metadata.json".format(
                        model_name
                    ),
                    metadata_path,
                )

        metadata = ModelMetadata.from_file(metadata_path)
        return Model.from_file(model_path, metadata), metadata

    def camera_feed(self, width=480, height=360, quality=90, topic="display_mjpeg"):
        assert topic in ["display_mjpeg", "overlay_msg"], "Camera topic not supported!"

        return "{}/route?topic=/{}&width={}&height={}&quality={}".format(
            self.base_url, topic, width, height, quality
        )

    def _update_battery_level(self):
        res = self.session.get(
            "{}/api/get_battery_level".format(self.base_url), timeout=20
        )
        if res.status_code != 200:
            raise Exception("Error updating car battery level.")

        out = res.json()
        if out["success"] is True and self.battery_level != out["battery_level"]:
            self.battery_level = out["battery_level"]
            logging.info(
                "{} battery level changed: {}".format(self.name, self.battery_level)
            )

    def _update_sensor_status(self):
        res = self.session.get(
            "{}/api/get_sensor_status".format(self.base_url), timeout=20
        )
        if res.status_code != 200:
            raise Exception("Error updating car sensor status.")

        out = res.json()

        if out["success"] is True:
            if self.camera_status != out["camera_status"]:
                self.camera_status = out["camera_status"]
                logging.info(
                    "Car '{}' camera_status changed: {}".format(
                        self.name, self.camera_status
                    )
                )

            if self.stereo_status != out["stereo_status"]:
                self.stereo_status = out["stereo_status"]
                logging.info(
                    "Car '{}' stereo_status changed: {}".format(
                        self.name, self.stereo_status
                    )
                )

            if self.lidar_status != out["lidar_status"]:
                self.lidar_status = out["lidar_status"]
                logging.info(
                    "Car '{}' lidar_status changed: {}".format(
                        self.name, self.lidar_status
                    )
                )

    def _update_log_values(self, line):
        if line == "---\n":
            return

        line = line.lstrip('"').rstrip('"\n')

        # Check if car is running
        match = re.search(r"Inference task .* has (.*)", line)
        if match:
            state = match[1]
            car_driving = True if state == "started" else False
            if self.car_driving != car_driving:
                self.car_driving = car_driving
                logging.info(
                    "Car '{}' driving state changed: {}".format(
                        self.name, self.car_driving
                    )
                )
            return

        # Find currently loaded model.
        match = re.search(r"Model '(.*)' is installed", line)
        if match:
            if self.model_name != match[1]:
                self.model_name = match[1]
                logging.info(
                    "Car '{}' loaded model changed: {}".format(
                        self.name, self.model_name
                    )
                )
            return

        # Find last throttle value.
        match = re.search(r"Setting throttle to (\d+\.\d+)", line)
        if match:
            throttle = float(match[1]) * 100
            if self.throttle != throttle:
                self.throttle = throttle
                logging.info(
                    "Car '{}' throttle changed: {}".format(self.name, self.throttle)
                )
            return
