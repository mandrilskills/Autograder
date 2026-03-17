"""
ast_generator.py
Deterministic Test Case Generation using Abstract Syntax Trees (AST).
"""

import re
import logging
from pycparser import c_parser, c_ast

logger = logging.getLogger(__name__)

def clean_c_code_for_ast(source_code: str) -> str:
    """
    pycparser does not support standard library macros and headers natively.
    This function strips #include directives and common macros so the AST
    can focus purely on the student's structural logic.
    """
    # Remove standard includes
    code = re.sub(r'#include\s*<.*?>', '', source_code)
    code = re.sub(r'#include\s*".*?"', '', code)
    
    # Add dummy typedefs if students use common standard types 
    # (prevents pycparser from crashing on unknown types)
    dummy_typedefs = """
    typedef int size_t;
    typedef int bool;
    #define NULL 0
    """
    return dummy_typedefs + "\n" + code

class ScanfVisitor(c_ast.NodeVisitor):
    """
    Traverses the AST to find all scanf() calls and extracts their format strings.
    """
    def __init__(self):
        self.format_strings = []

    def visit_FuncCall(self, node):
        # Check if the function being called is 'scanf'
        if getattr(node.name, 'name', '') == 'scanf':
            # Extract the first argument (the format string)
            if node.args and len(node.args.exprs) > 0:
                first_arg = node.args.exprs[0]
                if isinstance(first_arg, c_ast.Constant) and first_arg.type == 'string':
                    self.format_strings.append(first_arg.value)
        # Continue traversing children
        self.generic_visit(node)

def generate_inputs_from_ast(source_code: str) -> list[str] | None:
    """
    Parses the C code AST, extracts expected input types, and generates
    5 deterministic boundary test cases.
    Returns None if parsing fails or no inputs are required.
    """
    try:
        clean_code = clean_c_code_for_ast(source_code)
        parser = c_parser.CParser()
        ast = parser.parse(clean_code, filename='<stdin>')
        
        visitor = ScanfVisitor()
        visitor.visit(ast)
        
        if not visitor.format_strings:
            # If no scanf is found, maybe it takes no input, or uses gets/fgets.
            # Return a default empty input to trigger the oracle.
            return ["\n", "1\n", "0\n", "-1\n", "100\n"]

        # Combine all format strings found in the order they execute
        # e.g., ['"%d"', '"%f %c"'] -> "%d %f %c"
        combined_formats = " ".join([f.strip('"') for f in visitor.format_strings])
        
        # Extract individual specifiers
        specifiers = re.findall(r'%[0-9]*[a-zA-Z]', combined_formats)
        
        if not specifiers:
             return ["\n", "1\n", "0\n", "-1\n", "100\n"]

        # Define boundary test profiles
        test_profiles = {
            "standard": [],
            "zeros": [],
            "negatives": [],
            "large_bounds": [],
            "edge": []
        }

        for spec in specifiers:
            if 'd' in spec or 'i' in spec:  # Integer
                test_profiles["standard"].append("42")
                test_profiles["zeros"].append("0")
                test_profiles["negatives"].append("-7")
                test_profiles["large_bounds"].append("2147483647")
                test_profiles["edge"].append("-2147483648")
            elif 'f' in spec or 'lf' in spec:  # Float/Double
                test_profiles["standard"].append("3.14")
                test_profiles["zeros"].append("0.0")
                test_profiles["negatives"].append("-99.99")
                test_profiles["large_bounds"].append("1e38")
                test_profiles["edge"].append("0.0000001")
            elif 'c' in spec:  # Character
                test_profiles["standard"].append("A")
                test_profiles["zeros"].append(" ")
                test_profiles["negatives"].append("z")
                test_profiles["large_bounds"].append("Z")
                test_profiles["edge"].append("@")
            elif 's' in spec:  # String
                test_profiles["standard"].append("Hello")
                test_profiles["zeros"].append("a")
                test_profiles["negatives"].append("Test_String")
                test_profiles["large_bounds"].append("A_very_long_string_without_spaces")
                test_profiles["edge"].append("12345!@#")
            else:
                test_profiles["standard"].append("1")

        # Compile profiles into final input strings
        inputs = [
            " ".join(test_profiles["standard"]) + "\n",
            " ".join(test_profiles["zeros"]) + "\n",
            " ".join(test_profiles["negatives"]) + "\n",
            " ".join(test_profiles["large_bounds"]) + "\n",
            " ".join(test_profiles["edge"]) + "\n"
        ]
        
        logger.info(f"AST generated deterministic inputs: {inputs}")
        return inputs

    except Exception as e:
        logger.error(f"AST Parsing failed: {e}. Falling back to default generation.")
        return None
