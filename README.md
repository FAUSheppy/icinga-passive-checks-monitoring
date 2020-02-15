## Setup
Please refer to [my blog](https://blog.atlantishq.de/post/monitoring-icinga-1/) for a detailed how to.

## Script Parameters

    usage: monitoring-report.py [-h] [-H HOSTNAME] [-c CONFIGURATIONFILE] [-a]
                                [-u]
    optional arguments:
      -h, --help            show this help message and exit
      -H HOSTNAME, --hostname HOSTNAME
                            local identity/hostname)
      -c CONFIGURATIONFILE, --config CONFIGURATIONFILE
                            Configuration file (default: ./monitoring.conf)
      -a, --async           Run checks asynchronous
      -u, --ignore-user     Run as current user and ignore user column in config
                            file

## Configuration file
One service per line. User, service name and command separated by TAB and command and command arguments separated by spaces. Lines starting with ``#`` are ignored, inline comments are not supported.

    # a comment
    user<TAB>service-name<TAB>command args
    nobody<TAB>sheppy-mail<TAB>/usr/lib/nagios/plugins/check-something -w 5 -e 10
