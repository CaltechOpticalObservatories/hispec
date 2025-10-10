import zmq
import time
from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
import json
import time

def main():
    # Create a ZeroMQ context
    context = zmq.Context()

    # Create a PULL socket
    socket = context.socket(zmq.XSUB)

    # Bind the socket to port 5555
    socket.connect("tcp://localhost:5555")

    # Subscribe to all topics
    socket.send(b'\x01')
    print("Listening for messages on port 5555...")

    info = {}

    # Continuously listen for incoming messages
    while True:
        try:
            message = socket.recv()
            print(f'Time: {time.time()} - Raw data:  {message}')

        except zmq.Again:
            time.sleep(5)
            # print("Waiting for messages...")

if __name__ == "__main__":
    main()

