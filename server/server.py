import os
import sys
import time
import random
import argparse
import RNS

# A reference to the latest client link that connected
latest_client_link = None


def return_path(path, data, request_id, remote_identity, requested_at):
    with open('root/' + path, 'r') as file:
        data = file.read()
    RNS.log("Generating response to request " + RNS.prettyhexrep(request_id))
    return data


# This initialisation is executed when the users chooses
# to run as a server
def server(identitypath):
    # We must first initialise Reticulum
    reticulum = RNS.Reticulum(None)

    if os.path.isfile(identitypath):
        try:
            server_identity = RNS.Identity.from_file(identitypath)
            if server_identity != None:
                RNS.log("Loaded Primary Identity %s from %s" % (str(server_identity), identitypath))
            else:
                RNS.log("Could not load the Primary Identity from " + identitypath, RNS.LOG_ERROR)
        except Exception as e:
            RNS.log("Could not load the Primary Identity from " + identitypath, RNS.LOG_ERROR)
            RNS.log("The contained exception was: %s" % (str(e)), RNS.LOG_ERROR)
    else:
        try:
            RNS.log("No Primary Identity file found, creating new...")
            server_identity = RNS.Identity()
            server_identity.to_file(identitypath)
            RNS.log("Created new Primary Identity %s" % (str(server_identity)))
        except Exception as e:
            RNS.log("Could not create and save a new Primary Identity", RNS.LOG_ERROR)
            RNS.log("The contained exception was: %s" % (str(e)), RNS.LOG_ERROR)

    # We create a destination that clients can connect to. We
    # want clients to create links to this destination, so we
    # need to create a "single" destination type.
    server_destination = RNS.Destination(
        server_identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        "rip",
        "server"
    )

    # We configure a function that will get called every time
    # a new client creates a link to this destination.
    server_destination.set_link_established_callback(client_connected)

    for subdir, dirs, files in os.walk("root"):
        for file in files:
            filepath = file
            print("/" + filepath)
            server_destination.register_request_handler(
                "/" + filepath,
                response_generator=return_path,
                allow=RNS.Destination.ALLOW_ALL
            )


    # Everything's ready!
    # Let's Wait for client requests or user input
    server_loop(server_destination)


def server_loop(destination):
    # Let the user know that everything is ready
    RNS.log(
        "Request example " +
        RNS.prettyhexrep(destination.hash) +
        " running, waiting for a connection."
    )

    RNS.log("Hit enter to manually send an announce (Ctrl-C to quit)")

    # We enter a loop that runs until the users exits.
    # If the user hits enter, we will announce our server
    # destination on the network, which will let clients
    # know how to create messages directed towards it.
    while True:
        entered = input()
        destination.announce()
        RNS.log("Sent announce from " + RNS.prettyhexrep(destination.hash))


# When a client establishes a link to our server
# destination, this function will be called with
# a reference to the link.
def client_connected(link):
    global latest_client_link

    RNS.log("Client connected")
    link.set_link_closed_callback(client_disconnected)
    latest_client_link = link


def client_disconnected(link):
    RNS.log("Client disconnected")


if __name__ == "__main__":
    try:
        server("storage/identity")

    except KeyboardInterrupt:
        print("")
        exit()
