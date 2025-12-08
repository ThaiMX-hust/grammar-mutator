rule_name="win_net_start_service"
sigma_detection=r"""
detection:
    selection_img:
        - Image|endswith:
              - '\net.exe'
              - '\net1.exe'
        - OriginalFileName:
              - 'net.exe'
              - 'net1.exe'
    selection_cli:
        CommandLine|contains: ' start '     # space character after the 'start' keyword indicates that a service name follows, in contrast to `net start` discovery expression
    condition: all of selection_*
"""

tags=r"""
tags:
    - attack.execution
    - attack.t1569.002
"""
description=r"""
description: Detects the usage of the "net.exe" command to start a service using the "start" flag
"""