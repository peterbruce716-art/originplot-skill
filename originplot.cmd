@echo off
setlocal
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3.10 -m originplot.cli.main %*
) else (
  python -m originplot.cli.main %*
)
exit /b %ERRORLEVEL%
