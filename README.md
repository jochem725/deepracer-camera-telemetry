# AWS DeepRacer Camera Telemetry
Toolkit to process and stream an AWS DeepRacer camera feed, including telemetry such as the current throttle value.

# Setup
## Requirements
- Python 3
- [Poetry](https://github.com/sdispater/poetry)

## Installation
First prepare the Python enviroment using `poetry install`.

## Configuration
Copy `config.json.sample` to `config.json` and fill in car details.
```json
{
  "cars": [
    {
      "name": "Car 1", # Car name to display in camera feed
      "ip": "10.0.1.1", # Car IP
      "ssh_password": "somepassword" # Car SSH password
    },
    ...
  ],
  "stream_width": 480, # Width of output stream
  "stream_height": 360, # Height of output stream
  "stream_quality": 50, # Stream quality [1, 100] (lower = less data)
  "port": 8080 # Port for webserver.
}
```

## Running
Make sure the virtual environment is activated using `poetry shell`.
Then run `dct server`
`localhost:<PORT>/stream/0/live` provides the stream of the first car. 

The following streams will are available
- `localhost:<PORT>/stream/<CAR_ID>/live`
- `localhost:<PORT>/stream/<CAR_ID>/live_hud`
- `localhost:<PORT>/stream/<CAR_ID>/live_grad`

