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

responded: bool = False
server_link = None
current_destination = None

# assumes url is in this form: rip://<destinationhash>/some/optional/path
def parse_url(url):
    if "://" not in url:
        url = "rip://" + url
    t_url = url.replace("rip://", "http://")
    parsed = urllib.parse.urlparse(t_url)
    print("1: " + parsed.netloc + " " + parsed.path)
    return parsed.netloc, parsed.path

def absolutise_url(base, relative):
    if "://" not in relative:
        # Python's URL tools somehow only work with known schemes?
        base = base.replace("rip://", "http://")
        relative = urllib.parse.urljoin(base, relative)
        relative = relative.replace("http://", "rip://")
    return relative


def request(destination_hexhash, path):
    global server_link
    global current_destination

    c_path = path
    if path == "" or path == "/":
        c_path = "/index.gem"

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

    if current_destination == destination_hash and server_link:
        try:
            RNS.log("Sending request to " + c_path)
            server_link.request(
                c_path,
                data=None,
                response_callback=got_response,
                failed_callback=request_failed,
                timeout=5,
            )
            current_destination = destination_hash

        except Exception as e:
            RNS.log("Error while sending request over the link: " + str(e))
            should_quit = True
            server_link.teardown()

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

    try:
        RNS.log("Sending request to " + c_path)
        server_link.request(
            c_path,
            data=None,
            response_callback=got_response,
            failed_callback=request_failed,
            timeout=5,
        )
        current_destination = destination_hash

    except Exception as e:
        RNS.log("Error while sending request over the link: " + str(e))
        should_quit = True
        server_link.teardown()


def browser_loop():
    global responded
    global server_link
    reticulum = RNS.Reticulum(None)
    client_identity = RNS.Identity()
    while True:
        # Get input
        cmd = input("> ").strip()
        # Handle things other than requests
        if cmd.lower() == "q":
            print("Bye!")
            if server_link:
                server_link.teardown()
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
            netloc, path = parse_url(url)
            responded = False
            request(netloc, path)
            while not responded:
                time.sleep(0.1)

        except Exception as err:
            print(err)
            continue
        hist.append(url)


def link_established(link):
    global server_link
    server_link = link

    RNS.log("Link established with server")


def got_response(request_receipt):
    global responded
    request_id = request_receipt.request_id
    response = request_receipt.response
    responded = True
    gemlines = response.strip().split('\n')
    parse_gemtext(gemlines)

def parse_gemtext(gemlines):
    global current_destination
    preformatted = False
    if gemlines[0] == "text/gemini":
        for line in gemlines:
            if line == gemlines[0]:
                continue
            if line.startswith("```"):
                preformatted = not preformatted
            elif preformatted:
                print(line)
            elif line.startswith("=>") and line[2:].strip():
                bits = line[2:].strip().split(maxsplit=1)
                link_url = bits[0]
                link_url = absolutise_url(current_destination, link_url)
                menu.append(link_url)
                text = bits[1] if len(bits) == 2 else link_url
                print("[%d] %s" % (len(menu), text))
            else:
                print(textwrap.fill(line, 80))
    else:
        print("\nSorry I don't support that type of file yet\n")



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
