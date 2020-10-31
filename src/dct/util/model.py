import json
import tensorflow.compat.v1 as tf

tf.disable_v2_behavior()


class ModelMetadata:
    def __init__(self, sensor, network, simapp_version):
        self.sensor = sensor
        self.network = network
        self.simapp_version = simapp_version

        # TODO > Action space :)

    def __str__(self):
        return "{} -- {} -- SIMAPP_VERSION {}".format(
            self.sensor, self.network, self.simapp_version
        )

    def input_type(self):
        # Currently only support old observation or single camera
        # TODO: Check how we can do this more smart and support stereo.
        input_type = None
        if "observation" in self.sensor:
            input_type = "observation"
        elif "FRONT_FACING_CAMERA" in self.sensor:
            input_type = "FRONT_FACING_CAMERA"
        else:
            raise Exception("Metadata contains unsupported sensor.")

        return input_type

    @staticmethod
    def from_file(model_metadata_path: str):
        """Load a model metadata file

        Args:
            model_metadata_path (str): Path to the model_metadata.json file.

        Raises:
            Exception: If metadata cannot be loaded from the file.

        Returns:
            [tuple]: model sensors, network type, simapp version.
        """
        try:
            with open(model_metadata_path, "r") as json_file:
                data = json.load(json_file)
                if "version" in data:
                    simapp_version = data["version"]
                else:
                    simapp_version = None

                if "sensor" in data:
                    sensor = data["sensor"]
                else:
                    sensor = ["observation"]
                    simapp_version = "1.0"

                if "neural_network" in data:
                    network = data["neural_network"]
                else:
                    network = "DEEP_CONVOLUTIONAL_NETWORK_SHALLOW"

            return ModelMetadata(sensor, network, simapp_version)
        except Exception as e:
            raise Exception("Error parsing model metadata: {}".format(e))


class Model:
    def __init__(self, session, metadata):
        self.metadata = metadata
        self.session = session

    def input_size(self):
        input = self.get_model_input()

        height = input.shape[1]
        width = input.shape[2]

        return (width, height)

    def get_model_input(self):
        ops = self.session.graph.get_operations()

        # Select first operation output tensor.
        return ops[0].outputs[0]

    def get_model_output(self):
        ops = self.session.graph.get_operations()

        # Select last operation output tensor.
        return ops[-1].outputs[0]

    def get_model_convolutional_output(self):
        # Get all convolutional ops.
        ops = self.session.graph.get_operations()
        conv_ops = list(filter(lambda x: "Conv2d" in x.name, ops))

        # Return last conv op.
        return conv_ops[-1].outputs[0]

    @staticmethod
    def from_file(model_pb_path: str, metadata: ModelMetadata):
        """Load the TensorFlow graph for a model.pb model file.

        Args:
            pbpath (str): Path to the model.pb file

        Raises:
            Exception: If the session cannot be loaded from the model file.

        Returns:
            [tf.Session]: TensorFlow session object.
        """
        try:
            tf.reset_default_graph()
            sess = tf.Session(
                config=tf.compat.v1.ConfigProto(
                    allow_soft_placement=True, log_device_placement=True
                )
            )

            with tf.io.gfile.GFile(model_pb_path, "rb") as f:
                graph_def = tf.GraphDef()
                graph_def.ParseFromString(f.read())

            sess.graph.as_default()
            tf.import_graph_def(graph_def, name="")

            return Model(sess, metadata)
        except Exception as e:
            raise Exception("Could not get session for model: {}".format(e))
