import click
import requests
import json
import logging
import sys
import socket
import os


from dct.util.silverstone import DeepRacerCar
from dct.camera.stream import DeepRacerMJPEGStream, StreamConsumer
from dct.visualizations.base import BaseFrameVisualizer
from dct.visualizations.hud import HudOverlay
from dct.visualizations.gradcam import GradCamOverlay

from dct.stream.broadcaster import Broadcaster
from dct.stream.http import HTTPRequestHandler

requests.packages.urllib3.disable_warnings()
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

root = logging.getLogger()
root.setLevel(logging.DEBUG)

vizlog = logging.getLogger("deepracer-viz")
vizlog.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "[%(levelname)s]\t%(asctime)s - %(name)s - %(filename)s - %(lineno)d - %(message)s"
)
handler.setFormatter(formatter)
vizlog.addHandler(handler)
root.addHandler(handler)


@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)

    # Add config to context
    with open(
        os.path.join(os.path.dirname(__file__), "..", "..", "config.json"), "r"
    ) as f:
        config = json.load(f)

    # Store in context so other commands can use.
    ctx.obj["CONFIG"] = config


@cli.command()
@click.pass_context
def server(ctx):
    config = ctx.obj["CONFIG"]

    # Start the broadcasting server.
    requestHandler = HTTPRequestHandler(config["port"])
    requestHandler.start()

    cars = []
    for car in config["cars"]:
        car = DeepRacerCar(
            car["ip"], ssh_password=car["ssh_password"], name=car["name"]
        )
        car.connect()
        cars.append(car)

    broadcasters = []
    for i, car in enumerate(cars):
        stream = DeepRacerMJPEGStream(
            car,
            quality=config["stream_quality"],
            width=config["stream_width"],
            height=config["stream_height"],
        )
        stream.start()

        # TODO: Hacky.
        streamconsumer = StreamConsumer()
        stream.consumers.append(streamconsumer)
        viz = BaseFrameVisualizer(
            streamconsumer,
            width=config["stream_width"],
            height=config["stream_height"],
        )

        streamconsumer2 = StreamConsumer()
        stream.consumers.append(streamconsumer2)
        viz2 = BaseFrameVisualizer(
            streamconsumer2,
            width=config["stream_width"],
            height=config["stream_height"],
        )
        viz2.add(HudOverlay(car))

        streamconsumer3 = StreamConsumer()
        stream.consumers.append(streamconsumer3)
        viz3 = BaseFrameVisualizer(
            streamconsumer,
            width=config["stream_width"],
            height=config["stream_height"],
        )
        viz3.add(GradCamOverlay(car))
        viz3.add(HudOverlay(car))

        # Add the broadcasters
        broadcasters.append(Broadcaster(viz, key="{}/live".format(i)))
        broadcasters.append(Broadcaster(viz2, key="{}/live_hud".format(i)))
        broadcasters.append(Broadcaster(viz3, key="{}/live_grad".format(i)))

    for broadcaster in broadcasters:
        broadcaster.start()
        requestHandler.addBroadcaster(broadcaster, key=broadcaster.key)

        logging.info("Output stream available: {}".format(broadcaster.key))

    def quit():
        # broadcaster.kill = True
        requestHandler.kill = True
        quitsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        quitsock.connect(("127.0.0.1", config["port"]))
        quitsock.close()
        sys.exit(1)

    try:
        while input() != "quit":
            continue
        quit()
    except KeyboardInterrupt:
        quit()
    except EOFError:
        try:
            quit()
        except KeyboardInterrupt:
            os._exit(0)
