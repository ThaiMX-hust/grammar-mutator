rule_name="win_chcp_codepage_switch"
sigma_detection=r"""
detection:
    selection:
        Image|endswith: '\chcp.com'
        CommandLine|endswith:
            - ' 936'    # Chinese
            # - ' 1256' # Arabic
            - ' 1258'   # Vietnamese
            # - ' 855'  # Russian
            # - ' 866'  # Russian
            # - ' 864'  # Arabic
    condition: selection
"""
tags=r"""
tags:
    - attack.t1036
    - attack.defense-evasion
"""

mitre_techniques =r"""
# T1036 - Masquerading (Defense Evasion)

## Context:
Attackers use `chcp` (Change Code Page) to switch console encoding, often to:
- Display obfuscated text (Chinese/Vietnamese characters)
- Hide malicious strings from Western security tools
- Evade signature-based detection

## Alternative Methods to Change Code Page:

### 1. Using MODE command
mode con cp select=936
mode con cp select=1258
mode con: codepage select=936

### 2. Registry modification
reg add "HKCU\Console" /v CodePage /t REG_DWORD /d 936 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Nls\CodePage" /v OEMCP /d "936" /f
reg add "HKCU\Console\%%SystemRoot%%_system32_cmd.exe" /v CodePage /t REG_DWORD /d 936 /f

### 3. PowerShell encoding change
powershell -c "[Console]::OutputEncoding = [System.Text.Encoding]::GetEncoding(936)"
powershell -c "$OutputEncoding = [System.Text.Encoding]::GetEncoding(1258)"
powershell Set-ItemProperty -Path "HKCU:\Console" -Name CodePage -Value 936

### 4. Environment variable manipulation
set LANG=zh_CN.GB2312
set LC_ALL=zh_CN.GB2312
chcp 936 && set CODEPAGE=936

### 5. Obfuscated chcp execution
cmd.exe /c chcp 936
%COMSPEC% /c chcp 1258
echo chcp 936 | cmd
c^hcp 93^6
"chcp" 936
chcp.com 936

### 6. Alternative code page utilities
nlsfunc 936
nlsfunc /y 936
country 086,936

### 7. Batch file with encoding
@echo off
chcp 936 >nul 2>&1
echo 中文测试

### 8. Hidden execution with output redirection
chcp 936 >nul
chcp 1258 2>nul
chcp 936 >nul 2>&1

### 9. Combined with malicious commands
chcp 936 && powershell -enc <base64>
cmd /c "chcp 936 & malicious.exe"
chcp 1258 | malicious.bat

### 10. Unicode/UTF-8 switching
chcp 65001  # UTF-8
chcp 1200   # Unicode
chcp 1201   # Unicode (Big-Endian)

## Real-world APT usage:
- APT10 (MenuPass): Uses chcp 936 before downloading Chinese-language payloads
- Lazarus Group: Switches to Korean codepage (949) for obfuscation
- TA505: Uses Vietnamese codepage (1258) to evade Western EDR

## Detection bypass techniques:
- Using environment variables: %COMSPEC% /c ch^cp
- String concatenation: cmd /c "ch"+"cp" 936
- Base64 encoded: powershell -enc Y2hjcCA5MzY=
- Delayed execution: ping -n 5 127.0.0.1>nul && chcp 936
"""