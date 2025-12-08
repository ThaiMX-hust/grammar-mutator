rule_name="win_csi_use_of_csharp_console"
sigma_detection=r"""
detection:
    selection:
        Image|endswith: '\csi.exe'
        ParentImage|endswith:
            - '\powershell.exe'
            - '\pwsh.exe'
            - '\powershell_ise.exe'
        OriginalFileName: 'csi.exe'
    condition: selection
"""
tags=r"""
tags:
    - attack.execution
    - attack.defense-evasion
    - attack.t1127
"""
description=r"""
description: Detects the execution of CSharp interactive console by PowerShell
"""