import re
import sys

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

def split_print_items(print_str: str) -> list:
    """
    Splits a string of items separated by commas, but avoids
    splitting on commas that appear inside parentheses.
    
    For example, the string:
      "i, pow(i, 2)"
    should split into:
      ["i", "pow(i, 2)"]
    """
    tokens = []
    current = ""
    paren_level = 0
    for char in print_str:
        if char == '(':
            paren_level += 1
        elif char == ')':
            paren_level -= 1
        if char == ',' and paren_level == 0:
            tokens.append(current.strip())
            current = ""
        else:
            current += char
    if current:
        tokens.append(current.strip())
    return tokens

def convert_exponentiation(text: str) -> str:
    """
    Convert Fortran exponentiation using the ** operator to C++ pow() calls.
    For example, converts "i**2" to "pow(i, 2)".
    This simple regex assumes the exponentiation operands are simple identifiers or numbers.
    """
    return re.sub(r'(\w+)\s*\*\*\s*(\w+)', r'pow(\1, \2)', text)

def convert_double_literals(text: str) -> str:
    """
    Convert Fortran-style double precision literals to C++ style.
    For example, convert "2.1d0" to "2.1e0".
    """
    # This regex looks for a floating point literal with a d or D exponent indicator.
    return re.sub(r'(\d+\.\d+)[dD]([\+\-]?\d+)', r'\1e\2', text)

def translate_fortran_to_cpp(fortran_code: str) -> str:
    """
    Translates a subset of Fortran code into valid C++ code.
    
    Handles:
      - Modules as C++ namespaces.
      - Pure functions (assumes a single int parameter and int return type).
      - Variable declarations, including parameters and array definitions.
      - DO loops converted to C++ for-loops.
      - Early loop exits (if ... exit becomes if ... break).
      - Type conversion of dble() into C++ static_cast<double>().
      - Conversion of Fortran-style array element access: var(expr) becomes var[expr-1]
        for known array variables.
      - Conversion of exponentiation expressions using ** into pow() calls.
      - Conversion of double precision literals (e.g. 2.1d0 to 2.1e0).
      - Translation of READ statements to use cin.
      - If no "program" block is present, wraps the translated statements in a valid main().
    """
    cpp_lines = []
    array_vars = set()   # Set of variable names known to be arrays.
    function_result_var = None
    in_function = False  # Used to skip duplicate declarations in functions.
    main_declared = False  # Tracks whether we've seen a "program" declaration.

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

        # Skip empty lines.
        if not line:
            continue

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
        m_prog = re.match(r"program\s+(\w+)", line, re.IGNORECASE)
        if m_prog:
            main_declared = True
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
                # Convert exponentiation and double literals in the print content.
                content = convert_exponentiation(content)
                content = convert_double_literals(content)
                # Then, split the content into items without splitting inside parentheses.
                items = split_print_items(content)
                # Finally, adjust array accesses.
                converted_items = [convert_array_access(item) for item in items]
                cout_line = "  cout << " + " << \" \" << ".join(converted_items) + " << endl;"
                cpp_lines.append(cout_line)
            continue

        # Process READ statements: convert Fortran read (*,*) into C++ cin.
        m_read = re.match(r"read\s*\(\s*\*\s*,\s*\*\s*\)\s*(.+)", line, re.IGNORECASE)
        if m_read:
            var_list = m_read.group(1).strip()
            items = split_print_items(var_list)
            cin_line = "  cin >> " + " >> ".join(items) + ";"
            cpp_lines.append(cin_line)
            continue

        # Process assignments. Convert dble() to static_cast<double>(), adjust array accesses,
        # convert exponentiation expressions and double literals.
        if "=" in line and not line.lower().startswith("if") and not line.lower().startswith("do"):
            line = line.replace("dble(", "static_cast<double>(")
            line = convert_exponentiation(line)
            line = convert_double_literals(line)
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

        # Skip a lone "end" line.
        if re.match(r"^end\s*$", line, re.IGNORECASE):
            continue

        # Add any remaining non-empty lines.
        cpp_lines.append("  " + line)

    # If no main() block was declared, wrap the code in main().
    if not main_declared:
        cpp_lines = ["int main() {"] + ["  " + ln for ln in cpp_lines] + ["  return 0;", "}"]

    # Prepend necessary headers.
    includes = (
        "#include <iostream>\n"
        "#include <cmath>\n"
        "using namespace std;\n\n"
    )
    cpp_code = includes + "\n".join(cpp_lines)
    return cpp_code

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python translator.py <fortran_source_file>")
        sys.exit(1)
    
    source_file = sys.argv[1]
    
    try:
        with open(source_file, "r") as f:
            fortran_code = f.read()
    except FileNotFoundError:
        print(f"Error: File '{source_file}' not found.")
        sys.exit(1)
    
    cpp_code = translate_fortran_to_cpp(fortran_code)
    print("// Translated C++ code:")
    print("// ---------------------")
    print(cpp_code)
