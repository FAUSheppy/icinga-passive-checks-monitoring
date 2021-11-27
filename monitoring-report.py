#!/usr/bin/python3

import multiprocessing
import subprocess
import socket
import sys
import argparse
import os
import pwd
import grp

import requests

ENCODING = "UTF-8"
NO_GROUP = "nogroup"

def dropPivileges(uid_name, gid_name=None):
    if not gid_name:
        gid_name = NO_GROUP 

    target_uid = pwd.getpwnam(uid_name).pw_uid
    target_gid = grp.getgrnam(gid_name).gr_gid
    
    os.setgid(target_gid)
    os.setuid(target_uid)

def splitCMD(cmd):
    return list(filter(lambda a: a,cmd.strip("\n").split(" ")))

def executeAndSubmit(hostnameIdent, user, service, cmd, args):

    if not args.ignore_user:
        dropPivileges(user)

    message = ""
    cmd = splitCMD(cmd)

    # run monitoring command
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding=ENCODING)
        message = "{}\t{}\t{}\t{}\n".format(hostnameIdent, service, p.returncode, p.stdout)
    except FileNotFoundError:
        print("{} command not found!".format(splitCMD(cmd)[0]), file=sys.stderr)

    # submitt the results
    if args.gateway:

        if p.returncode == 0:
            status = "OK"
            info   = p.stdout
        else:
            status = "CRITICAL"
            info   = p.stderr

        print(args.gateway, { "service" : service,
                "token" : args.gateway_token, "status" : status, "info" : info })
        r = requests.post(args.gateway, json={ "service" : service,
                "token" : args.gateway_token, "status" : status, "info" : info })
        r.raise_for_status()

    else:
        if args.nsca_config:
            nscaCMD = [args.nsca_bin, '-c', args.nsca_config]
        else:
            nscaCMD = [args.nsca_bin]

        nscaProcess = subprocess.Popen(nscaCMD, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        stdout = nscaProcess.communicate(input=bytes(message, ENCODING))
        if nscaProcess.returncode != 0:
            raise RuntimeError("Execution of send_nsca failed - {}".format(stdout))

def executeConfig(hostnameIdent, args):

    asyncTasks = []

    # parse config and start tasks
    with open(args.config, "r") as f:

        for line in f:

            # split config #
            user, service, cmd = list(filter(lambda x: x, line.split("\t")))
            executeAndSubmit(hostnameIdent, user, service, cmd, args)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Icinga passive checks and curl report-ins.')
    parser.add_argument('-H', '--hostname', help='Local Identity (often hostname)')
    parser.add_argument('--nsca-config', 
                    help='send-nsca configuration file (default set by nsca-package)')
    parser.add_argument('--nsca-bin', default="/usr/sbin/send_nsca",
                    help='send-nsca executable (default: /usr/sbin/send_nsca)')
    parser.add_argument('--config', default="monitoring.conf",
                    help='Configuration file (default: ./monitoring.conf)')
    parser.add_argument('--async', action="store_const", const=True, default=False,
                    help='Run checks asynchronous')
    parser.add_argument('--ignore-user', action="store_const", const=True, default=False, 
                    help='Run as current user and ignore user column in config file')

    parser.add_argument('--gateway', help='If set, use an async icinga checks gateway')
    parser.add_argument('--gateway-token', help='Token to use with the gateway')

    args = parser.parse_args()
    if not args.hostname:
        hostname = socket.gethostname()
    else:
        hostname = args.hostname

    executeConfig(hostname, args)
