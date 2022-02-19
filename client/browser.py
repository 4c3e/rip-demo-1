#!/usr/bin/env python3

import cgi
import mailcap
import tempfile
import textwrap
import urllib.parse
import os
import time
import RNS

caps = mailcap.getcaps()
menu = []
hist = []

server_link = None
APP_NAME = "rip"


def absolutise_url(base, relative):
    if "://" not in relative:
        # Python's URL tools somehow only work with known schemes?
        base = base.replace("rip://", "http://")
        relative = urllib.parse.urljoin(base, relative)
        relative = relative.replace("http://", "rip://")
    return relative


def request(destination_hexhash, path):
    global server_link

    try:
        if len(destination_hexhash) != 20:
            raise ValueError("Destination length is invalid, must be 20 hexadecimal characters (10 bytes)")
        destination_hash = bytes.fromhex(destination_hexhash)

    except:
        RNS.log("Invalid destination entered. Check your input!\n")
        exit()

    # Check if we know a path to the destination
    if not RNS.Transport.has_path(destination_hash):
        RNS.log("Destination is not yet known. Requesting path and waiting for announce to arrive...")
        RNS.Transport.request_path(destination_hash)
        while not RNS.Transport.has_path(destination_hash):
            time.sleep(0.1)

    # Recall the server identity
    server_identity = RNS.Identity.recall(destination_hash)

    # Inform the user that we'll begin connecting
    RNS.log("Establishing link with server...")

    # When the server identity is known, we set
    # up a destination
    server_destination = RNS.Destination(
        server_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "rip",
        "server"
    )

    # And create a link
    t_link = RNS.Link(server_destination)

    # We'll set up functions to inform the
    # user when the link is established or closed
    t_link.set_link_established_callback(link_established)
    t_link.set_link_closed_callback(link_closed)

    while not server_link:
        time.sleep(0.1)

    c_path = path
    if path == "" or path == "/":
        c_path = "/index.gem"

    try:
        RNS.log("Sending request to " + c_path)
        server_link.request(
            c_path,
            data=None,
            response_callback=got_response,
            failed_callback=request_failed,
            timeout=5,
        )

    except Exception as e:
        RNS.log("Error while sending request over the link: " + str(e))
        should_quit = True
        server_link.teardown()


def browser_loop():
    global responded
    reticulum = RNS.Reticulum(None)
    client_identity = RNS.Identity()
    while True:
        # Get input
        cmd = input("> ").strip()
        # Handle things other than requests
        if cmd.lower() == "q":
            print("Bye!")
            break
        # Get URL, from menu, history or direct entry
        if cmd.isnumeric():
            url = menu[int(cmd) - 1]
        elif cmd.lower() == "b":
            # Yes, twice
            url = hist.pop()
            url = hist.pop()
        else:
            url = cmd
        try:
            url_sp = url.split(" ")
            url_base = url_sp[0]
            url_path = url_sp[1]
            responded = False
            request(url_base, url_path)
            while not responded:
                time.sleep(0.1)

        except Exception as err:
            print(err)
            continue
        print("appending: " + url)
        hist.append(url)


def link_established(link):
    # We store a reference to the link
    # instance for later use
    global server_link
    server_link = link

    # Inform the user that the server is
    # connected
    RNS.log("Link established with server, hit enter to perform a request, or type in \"quit\" to quit")


def got_response(request_receipt):
    global responded
    request_id = request_receipt.request_id
    response = request_receipt.response
    responded = True
    print(str(response))


def request_received(request_receipt):
    RNS.log("The request " + RNS.prettyhexrep(request_receipt.request_id) + " was received by the remote peer.")


def request_failed(request_receipt):
    RNS.log("The request " + RNS.prettyhexrep(request_receipt.request_id) + " failed.")


def link_closed(link):
    if link.teardown_reason == RNS.Link.TIMEOUT:
        RNS.log("The link timed out, exiting now")
    elif link.teardown_reason == RNS.Link.DESTINATION_CLOSED:
        RNS.log("The link was closed by the server, exiting now")
    else:
        RNS.log("Link closed, exiting now")

    RNS.Reticulum.exit_handler()
    time.sleep(1.5)
    os._exit(0)


if __name__ == "__main__":
    browser_loop()
