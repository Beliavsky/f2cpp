#!/bin/bash
# -----------------------------------------------------------------------------
# This script converts a Fortran (.f90) source file to C++,
# formats the resulting C++ code, and then compiles and runs the executable.
#
# Steps:
# 1. Run xtranslate.py on the input Fortran file ($1.f90) to generate temp.cpp.
# 2. Format temp.cpp using clang-format and output to $1.cpp.
# 3. Display the formatted C++ code.
# 4. Delete any existing executable (a.out) before compilation.
# 5. Compile $1.cpp with g++.
# 6. If compilation is successful (a.out exists), run the executable.
# -----------------------------------------------------------------------------

python xtranslate.py "$1.f90" > temp.cpp
clang-format temp.cpp > "$1.cpp"
echo "C++ code:"
cat "$1.cpp"
[ -f a.out ] && rm a.out
g++ "$1.cpp" -o a.out
echo
echo "output:"
[ -f a.out ] && ./a.out
