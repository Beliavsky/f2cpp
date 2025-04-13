@echo off
REM -----------------------------------------------------------------------------
REM This batch script converts a Fortran (.f90) source file to C++,
REM formats the resulting C++ code, and then compiles and runs the executable.
REM 
REM Steps:
REM 1. Run xtranslate.py on the input Fortran file (%1.f90) to generate temp.cpp.
REM 2. Format temp.cpp using clang-format and output to %1.cpp.
REM 3. Display the formatted C++ code.
REM 4. Delete any existing executable (a.exe) before compilation.
REM 5. Compile %1.cpp with g++.
REM 6. If compilation is successful (a.exe exists), run the executable.
REM -----------------------------------------------------------------------------
python xtranslate.py %1.f90 > temp.cpp
clang-format temp.cpp > %1.cpp
echo C++ code
type %1.cpp
if exist a.exe del a.exe
g++ %1.cpp
echo.
echo output:
if exist a.exe a.exe
