import re
import sys

def split_declarations(decl_str: str) -> list:
    """
    Splits a string of declarations separated by commas,
    but does not split on commas that appear inside square brackets.
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
    splitting on commas that appear inside parentheses or square brackets.
    """
    tokens = []
    current = ""
    paren_level = 0
    bracket_level = 0
    for char in print_str:
        if char == '(':
            paren_level += 1
        elif char == ')':
            paren_level -= 1
        elif char == '[':
            bracket_level += 1
        elif char == ']':
            bracket_level -= 1
        if char == ',' and paren_level == 0 and bracket_level == 0:
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
    For example, "i**2" becomes "pow(i, 2)".
    """
    return re.sub(r'(\w+)\s*\*\*\s*(\w+)', r'pow(\1, \2)', text)

def convert_double_literals(text: str) -> str:
    """
    Convert Fortran-style double precision literals to C++ style.
    For example, "2.1d0" becomes "2.1e0".
    """
    return re.sub(r'(\d+\.\d+)[dD]([\+\-]?\d+)', r'\1e\2', text)

def convert_array_constructor_literal(literal: str) -> str:
    """
    Convert a Fortran array constructor literal (e.g. "[10.0, 20.0]")
    into a C++ vector literal. Here we assume that if any element contains
    a dot or exponent, the type is float.
    """
    content = literal.strip()[1:-1].strip()  # remove surrounding brackets
    items = [item.strip() for item in content.split(',')]
    # Heuristically choose type: if any item looks like a floating-point number, use float.
    is_float = any(re.search(r'[.\deED]', item) for item in items)
    type_str = "float" if is_float else "int"
    return f"std::vector<{type_str}>{{{', '.join(items)}}}"

# Global set to record which variables (as function parameters) should be treated as vectors.
vector_params = set()

def replace_trailing_comment(line: str) -> str:
    """
    Scans a line for a Fortran comment indicator (!) that is not inside a string literal.
    If found, replaces it with a C++ comment marker (//) preserving the preceding code
    and the exact whitespace following the exclamation mark.
    """
    in_single_quote = False
    in_double_quote = False
    for i, char in enumerate(line):
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif char == '!' and not in_single_quote and not in_double_quote:
            # Found an unquoted exclamation mark.
            return line[:i].rstrip() + " //" + line[i+1:]
    return line

def preprocess_fortran_comments(fortran_code: str) -> str:
    """
    Processes the Fortran code to convert comments.
    Lines that start with an exclamation mark (after optional whitespace) are replaced entirely.
    Additionally, any trailing unquoted exclamation mark in a code line is replaced by a C++ comment.
    """
    processed_lines = []
    for line in fortran_code.splitlines():
        # If the line is entirely a comment (after stripping whitespace), replace it.
        if re.match(r'^\s*!', line):
            processed_lines.append(re.sub(r'^(\s*)!(.*)$', r'\1//\2', line))
        else:
            processed_lines.append(replace_trailing_comment(line))
    return "\n".join(processed_lines)

def convert_array_access(text: str, in_function: bool, array_vars: set) -> str:
    """
    For every variable known to be an array (either main or function parameter),
    replace Fortran-style array access "x(expr)" with:
      - If x is a function vector parameter and we are in function context, use "x[expr]".
      - Otherwise, use "x[(expr)-1]".
    """
    for var in array_vars.union(vector_params):
        pattern = re.compile(rf"\b{var}\(([^)]+)\)")
        def repl(m):
            expr = m.group(1).strip()
            if in_function and (var in vector_params):
                return f"{var}[{expr}]"
            else:
                return f"{var}[({expr})-1]"
        text = re.sub(pattern, repl, text)
    return text

def translate_fortran_to_cpp(fortran_code: str) -> str:
    """
    Translates a subset of Fortran code into valid C++ code.
    """
    # Preprocess the Fortran code to replace comment markers.
    fortran_code = preprocess_fortran_comments(fortran_code)
    
    cpp_lines = []
    array_vars = set()  # Variables declared as arrays in main.
    func_header_info = None  # Store (func_name, param, result_var)
    in_function = False
    main_declared = False
    # Flag to indicate that the current function has a vector parameter.
    current_function_is_vector = False

    lines = fortran_code.splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"implicit\s+none", line, re.IGNORECASE):
            continue
        if line.lower() == "contains":
            continue

        # Module definitions.
        m_mod = re.match(r"module\s+(\w+)", line, re.IGNORECASE)
        if m_mod:
            mod_name = m_mod.group(1)
            cpp_lines.append(f"namespace {mod_name} {{")
            continue
        if re.match(r"end\s+module", line, re.IGNORECASE):
            cpp_lines.append("} // end namespace")
            continue

        # Function header.
        m_func = re.match(r"function\s+(\w+)\s*\((\w+)\)\s+result\((\w+)\)", line, re.IGNORECASE)
        if m_func:
            func_name, param, result_var = m_func.groups()
            func_header_info = (func_name, param, result_var)
            in_function = True
            cpp_lines.append("/* function header pending */")
            continue

        # Inside function, check for real intent(in) declarations.
        m_real_param = re.match(r"real,\s*intent\s*\(in\)\s*::\s*(.+)", line, re.IGNORECASE)
        if m_real_param and in_function:
            decl = m_real_param.group(1).strip()
            for var in [v.strip() for v in decl.split(',')]:
                if re.search(r"\(:\)", var):
                    var_name = var.split('(')[0].strip()
                    vector_params.add(var_name)
                    current_function_is_vector = True
            continue

        # Inside function, skip integer intent(in) declarations.
        m_int_param = re.match(r"integer,\s*intent\s*\(in\)\s*::\s*(.+)", line, re.IGNORECASE)
        if m_int_param and in_function:
            continue

        # End of function.
        if in_function and re.match(r"end\s+function", line, re.IGNORECASE):
            if func_header_info is not None:
                func_name, param, result_var = func_header_info
                ret_type = "float"  # Assuming real -> float.
                if param in vector_params:
                    header = f"  {ret_type} {func_name}(const std::vector<float>& {param}) {{"
                    vector_params.add(param)
                else:
                    header = f"  {ret_type} {func_name}(int {param}) {{"
                for i, l in enumerate(cpp_lines):
                    if "/* function header pending */" in l:
                        cpp_lines[i] = header
                        break
                cpp_lines.append(f"    return {result_var};")
            cpp_lines.append("  }")
            in_function = False
            current_function_is_vector = False
            func_header_info = None
            continue

        # Program entry.
        m_prog = re.match(r"program\s+(\w+)", line, re.IGNORECASE)
        if m_prog:
            main_declared = True
            cpp_lines.append("int main() {")
            continue
        if re.match(r"end\s+program", line, re.IGNORECASE):
            cpp_lines.append("  return 0;")
            cpp_lines.append("}")
            continue

        # Module usage.
        m_use = re.match(r"use\s+(\w+)", line, re.IGNORECASE)
        if m_use:
            mod_name = m_use.group(1)
            cpp_lines.append(f"  using namespace {mod_name};")
            continue

        # Parameter and array declarations.
        m_param = re.match(r"integer,\s*parameter\s*::\s*(.+)", line, re.IGNORECASE)
        if m_param:
            decl_str = m_param.group(1)
            decls = split_declarations(decl_str)
            for decl in decls:
                m_arr = re.match(r"(\w+)\s*\(\s*(\w+)\s*\)\s*=\s*\[(.+)\]", decl)
                if m_arr:
                    var_name, size, values = m_arr.groups()
                    array_vars.add(var_name)
                    cpp_lines.append(f"  std::vector<int> {var_name} = {{{values}}};")
                else:
                    m_simple = re.match(r"(\w+)\s*=\s*(\w+)", decl)
                    if m_simple:
                        var_name, value = m_simple.groups()
                        cpp_lines.append(f"  const int {var_name} = {value};")
            continue

        # Real declarations.
        m_real_decl = re.match(r"real\s*::\s*(.+)", line, re.IGNORECASE)
        if m_real_decl:
            decl = m_real_decl.group(1).strip()
            vars_decl = [v.strip() for v in decl.split(',')]
            for var in vars_decl:
                if '(' in var:
                    m_arr = re.match(r"(\w+)\((.+)\)", var)
                    if m_arr:
                        var_name, dims = m_arr.groups()
                        dims = dims.strip()
                        if dims == ":":
                            vector_params.add(var_name)
                        else:
                            cpp_lines.append(f"  std::vector<float> {var_name}({dims});")
                            array_vars.add(var_name)
                else:
                    cpp_lines.append(f"  float {var};")
            continue

        # Integer declarations.
        m_int_decl = re.match(r"integer\s*::\s*(.+)", line, re.IGNORECASE)
        if m_int_decl:
            decl = m_int_decl.group(1).strip()
            cpp_lines.append(f"  int {decl};")
            continue

        # DO loops.
        m_do = re.match(r"do\s+(\w+)\s*=\s*(\w+)\s*,\s*(\w+)", line, re.IGNORECASE)
        if m_do:
            var, start, end = m_do.groups()
            if in_function and current_function_is_vector and start == "1":
                cpp_lines.append(f"  for (int {var} = 0; {var} < {end}; ++{var}) {{")
            else:
                cpp_lines.append(f"  for (int {var} = {start}; {var} <= {end}; {var}++) {{")
            continue
        if re.match(r"end\s+do", line, re.IGNORECASE):
            cpp_lines.append("  }")
            continue

        # Print statements.
        if line.lower().startswith("print*"):
            # Split the line into the code part and a trailing comment if present.
            if "//" in line:
                code_part, comment_part = line.split("//", 1)
                # Preserve the exact whitespace in the trailing comment.
            else:
                code_part = line
                comment_part = ""
            parts = code_part.split(",", 1)
            if len(parts) > 1:
                content = parts[1].strip()
                content = convert_exponentiation(content)
                content = convert_double_literals(content)
                items = split_print_items(content)
                converted_items = []
                for item in items:
                    if item.startswith('[') and item.endswith(']'):
                        converted_items.append(convert_array_constructor_literal(item))
                    else:
                        converted_items.append(convert_array_access(item, in_function, array_vars))
                cout_line = "  cout << " + " << \" \" << ".join(converted_items) + " << endl;"
                # Append the trailing comment if one exists.
                if comment_part:
                    cout_line += " //" + comment_part
                cpp_lines.append(cout_line)
            continue

        # READ statements.
        m_read = re.match(r"read\s*\(\s*\*\s*,\s*\*\s*\)\s*(.+)", line, re.IGNORECASE)
        if m_read:
            var_list = m_read.group(1).strip()
            items = split_print_items(var_list)
            cin_line = "  cin >> " + " >> ".join(items) + ";"
            cpp_lines.append(cin_line)
            continue

        # Assignments.
        if "=" in line and not line.lower().startswith("if") and not line.lower().startswith("do"):
            line = line.replace("dble(", "static_cast<double>(")
            line = convert_exponentiation(line)
            line = convert_double_literals(line)
            line = convert_array_access(line, in_function, array_vars)
            if not line.endswith(";"):
                line += ";"
            cpp_lines.append("  " + line)
            continue

        # IF exit statements.
        m_if_exit = re.match(r"if\s*\((.+)\)\s*exit", line, re.IGNORECASE)
        if m_if_exit:
            condition = m_if_exit.group(1)
            cpp_lines.append(f"  if ({condition}) break;")
            continue

        # Skip a lone "end" line.
        if re.match(r"^end\s*$", line, re.IGNORECASE):
            continue

        cpp_lines.append("  " + line)

    if not main_declared:
        cpp_lines = ["int main() {"] + ["  " + ln for ln in cpp_lines] + ["  return 0;", "}"]

    includes = (
        "#include <iostream>\n"
        "#include <cmath>\n"
        "#include <vector>\n"
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
    print(cpp_code)
