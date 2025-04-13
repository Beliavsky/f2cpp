import re

def split_declarations(decl_str: str) -> list:
    """
    Splits a string of declarations separated by commas,
    but does not split on commas that appear inside square brackets.
    
    For example:
      "n = 3, vec(n) = [3, 5, 10]"
    becomes:
      ["n = 3", "vec(n) = [3, 5, 10]"]
    """
    tokens = []
    current = ""
    bracket_level = 0
    for char in decl_str:
        if char == '[':
            bracket_level += 1
        elif char == ']':
            bracket_level -= 1
        if char == ',' and bracket_level == 0:
            tokens.append(current.strip())
            current = ""
        else:
            current += char
    if current:
        tokens.append(current.strip())
    return tokens

def translate_fortran_to_cpp(fortran_code: str) -> str:
    """
    Translates a subset of Fortran code into C++ code.
    
    Handles:
      - Modules as C++ namespaces.
      - Pure functions (assumes a single int parameter and int return type).
      - Variable declarations, including parameters and array definitions.
      - DO loops converted to C++ for-loops.
      - Early loop exits (if ... exit becomes if ... break).
      - Type conversion of dble() into C++ static_cast<double>().
      - Conversion of Fortran-style array element access: var(expr) becomes var[expr-1]
        for known array variables.
    """
    cpp_lines = []
    array_vars = set()   # Set of variable names known to be arrays.
    function_result_var = None
    in_function = False  # Used to skip duplicate declarations in functions.

    def convert_array_access(text: str) -> str:
        """
        For every known array variable, replace Fortran-style array access,
        e.g. vec(expr) with C++ style: vec[expr-1].
        """
        for var in array_vars:
            pattern = re.compile(rf"\b{var}\(([^)]+)\)")
            text = re.sub(pattern, lambda m: f"{var}[{m.group(1)}-1]", text)
        return text

    lines = fortran_code.splitlines()

    for raw_line in lines:
        line = raw_line.strip()

        # Skip lines that don't need translation.
        if re.match(r"implicit\s+none", line, re.IGNORECASE):
            continue
        if line.lower() == "contains":
            continue

        # Process module definitions.
        m_mod = re.match(r"module\s+(\w+)", line, re.IGNORECASE)
        if m_mod:
            mod_name = m_mod.group(1)
            cpp_lines.append(f"namespace {mod_name} {{")
            continue
        if re.match(r"end\s+module", line, re.IGNORECASE):
            cpp_lines.append("} // end namespace")
            continue

        # Process pure function definitions.
        m_func = re.match(r"pure\s+function\s+(\w+)\s*\((\w+)\)\s+result\((\w+)\)", line, re.IGNORECASE)
        if m_func:
            func_name, param, result_var = m_func.groups()
            function_result_var = result_var
            in_function = True
            cpp_lines.append(f"  int {func_name}(int {param}) {{")
            continue
        # Skip duplicate declarations inside functions.
        if in_function and re.search(r"intent\s*\(in\)", line, re.IGNORECASE):
            continue
        if re.match(r"end\s+function", line, re.IGNORECASE):
            if function_result_var:
                cpp_lines.append(f"    return {function_result_var};")
            cpp_lines.append("  }")
            function_result_var = None
            in_function = False
            continue

        # Process the program entry point.
        if re.match(r"program\s+(\w+)", line, re.IGNORECASE):
            cpp_lines.append("int main() {")
            continue
        if re.match(r"end\s+program", line, re.IGNORECASE):
            cpp_lines.append("  return 0;")
            cpp_lines.append("}")
            continue

        # Process module usage.
        m_use = re.match(r"use\s+(\w+)", line, re.IGNORECASE)
        if m_use:
            mod_name = m_use.group(1)
            cpp_lines.append(f"  using namespace {mod_name};")
            continue

        # Process parameter and array declarations.
        m_param = re.match(r"integer,\s*parameter\s*::\s*(.+)", line, re.IGNORECASE)
        if m_param:
            decl_str = m_param.group(1)
            decls = split_declarations(decl_str)
            for decl in decls:
                # Handle array declarations, e.g., vec(n) = [3, 5, 10]
                m_arr = re.match(r"(\w+)\s*\(\s*(\w+)\s*\)\s*=\s*\[(.+)\]", decl)
                if m_arr:
                    var_name, size, values = m_arr.groups()
                    array_vars.add(var_name)
                    cpp_lines.append(f"  int {var_name}[{size}] = {{{values}}};")
                else:
                    m_simple = re.match(r"(\w+)\s*=\s*(\w+)", decl)
                    if m_simple:
                        var_name, value = m_simple.groups()
                        cpp_lines.append(f"  const int {var_name} = {value};")
            continue

        # Process plain variable declarations.
        m_int_decl = re.match(r"integer\s*::\s*(.+)", line, re.IGNORECASE)
        if m_int_decl:
            decl = m_int_decl.group(1).strip()
            cpp_lines.append(f"  int {decl};")
            continue

        m_double_decl = re.match(r"double\s+precision\s*::\s*(.+)", line, re.IGNORECASE)
        if m_double_decl:
            decl = m_double_decl.group(1).strip()
            cpp_lines.append(f"  double {decl};")
            continue

        # Process DO loops, e.g., "do i=2,n"
        m_do = re.match(r"do\s+(\w+)\s*=\s*(\w+)\s*,\s*(\w+)", line, re.IGNORECASE)
        if m_do:
            var, start, end = m_do.groups()
            cpp_lines.append(f"  for (int {var} = {start}; {var} <= {end}; {var}++) {{")
            continue
        if re.match(r"end\s+do", line, re.IGNORECASE):
            cpp_lines.append("  }")
            continue

        # Process print statements: convert Fortran "print*," into C++ cout.
        if line.lower().startswith("print*"):
            parts = line.split(",", 1)
            if len(parts) > 1:
                content = parts[1].strip()
                items = [x.strip() for x in content.split(",")]
                converted_items = [convert_array_access(item) for item in items]
                cout_line = "  cout << " + " << \" \" << ".join(converted_items) + " << endl;"
                cpp_lines.append(cout_line)
            continue

        # Process assignments. Convert dble() to static_cast<double>() and adjust array accesses.
        if "=" in line and not line.lower().startswith("if") and not line.lower().startswith("do"):
            line = line.replace("dble(", "static_cast<double>(")
            line = convert_array_access(line)
            if not line.endswith(";"):
                line += ";"
            cpp_lines.append("  " + line)
            continue

        # Process IF exit statements.
        m_if_exit = re.match(r"if\s*\((.+)\)\s*exit", line, re.IGNORECASE)
        if m_if_exit:
            condition = m_if_exit.group(1)
            cpp_lines.append(f"  if ({condition}) break;")
            continue

        # Add any remaining non-empty lines as-is.
        if line:
            cpp_lines.append("  " + line)

    # Prepend necessary headers.
    includes = (
        "#include <iostream>\n"
        "#include <cmath>\n"
        "using namespace std;\n\n"
    )
    cpp_code = includes + "\n".join(cpp_lines)
    return cpp_code

if __name__ == "__main__":
    # Sample Fortran code.
    fortran_sample = """\
module m
implicit none
contains
pure function factorial(n) result(nfac)
integer, intent(in) :: n
integer :: nfac
integer :: i
nfac = 1
do i=2,n
   nfac = nfac*i
end do
end function factorial
end module m

program main
use m
implicit none
integer, parameter :: n = 3, vec(n) = [3, 5, 10]
integer :: i, fac
double precision :: xfac
do i=1,n
   fac = factorial(vec(i))
   xfac = dble(fac)
   print*,vec(i), fac, sqrt(xfac)
   if (fac > 100) exit
end do
end program main
"""
    cpp_output = translate_fortran_to_cpp(fortran_sample)
    print("// Translated C++ code:")
    print(cpp_output)
