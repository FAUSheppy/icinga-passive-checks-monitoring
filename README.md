## Setup
Please refer to [my blog](https://blog.atlantishq.de/post/monitoring-icinga-1/) for a detailed how to.

## Script Parameters

    hostname        local identity (usually hostname)
    -c, --config    configuration file
    -a, --async     execute all checks paralelle
    -h, --help      show help

## Configuration file
One service per line. User, service name and command separated by TAB and command and command arguments separated by spaces. Lines starting with ``#`` are ignored, inline comments are not supported.

    # a comment
    user<TAB>service-name<TAB>command args
    nobody<TAB>sheppy-mail<TAB>/usr/lib/nagios/plugins/check-something -w 5 -e 10
