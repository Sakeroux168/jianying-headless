@echo off
rem Build jy14_codec_win.exe with MSVC.  Set VSINSTALL to override the
rem Build Tools location.
setlocal
if "%VSINSTALL%"=="" set "VSINSTALL=E:\Dev\VSBuildTools"
call "%VSINSTALL%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
if not exist out mkdir out
cl /nologo /std:c++17 /EHsc /O2 /MD /utf-8 /W4 jy14_codec_win.cpp /Fo:out\ /Fe:out\jy14_codec_win.exe
