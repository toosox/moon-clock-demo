Unicode True
RequestExecutionLevel user
SetCompressor /SOLID lzma

!include "MUI2.nsh"

!define APP_NAME "Moon Clock Demo"
!define APP_VERSION "0.1.0-demo1"
!define APP_PUBLISHER "TarotByAndrew.com"
!define APP_EXE "Moon Clock Demo.exe"
!define APP_REG_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Moon Clock Demo"

Name "${APP_NAME}"
OutFile "${PROJECT_ROOT}\dist\windows\MoonClock-Demo-Setup-${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\TarotByAndrew\Moon Clock Demo"
InstallDirRegKey HKCU "${APP_REG_KEY}" "InstallLocation"
BrandingText "${APP_PUBLISHER}"
VIProductVersion "0.1.0.1"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription" "Moon Clock Demo Installer"
VIAddVersionKey "LegalCopyright" "Copyright 2026 TarotByAndrew.com"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Moon Clock Demo"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${PROJECT_ROOT}\DEMO-LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Section "Moon Clock Demo" MainSection
    SetShellVarContext current
    SetOutPath "$INSTDIR"
    File "/oname=${APP_EXE}" "${PROJECT_ROOT}\dist\windows\${APP_EXE}"
    File "${PROJECT_ROOT}\DEMO-LICENSE.txt"
    File "${PROJECT_ROOT}\THIRD-PARTY-NOTICES.txt"
    SetOutPath "$INSTDIR\third-party-licenses"
    File "${PROJECT_ROOT}\third-party-licenses\*.txt"
    SetOutPath "$INSTDIR"

    CreateDirectory "$SMPROGRAMS\${APP_PUBLISHER}"
    CreateShortcut "$SMPROGRAMS\${APP_PUBLISHER}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"

    WriteUninstaller "$INSTDIR\Uninstall.exe"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "${APP_REG_KEY}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "${APP_REG_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKCU "${APP_REG_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegDWORD HKCU "${APP_REG_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${APP_REG_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
    SetShellVarContext current
    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_PUBLISHER}\${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_PUBLISHER}"
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\DEMO-LICENSE.txt"
    Delete "$INSTDIR\THIRD-PARTY-NOTICES.txt"
    RMDir /r "$INSTDIR\third-party-licenses"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"
    DeleteRegKey HKCU "${APP_REG_KEY}"
SectionEnd
