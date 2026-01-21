import re
from io import BytesIO

from lxml import etree


class MMLExpression:
    """
    Class to parse and convert MathML expressions.

    This class will hold MathML expressions and handle the API for the
    conversion to different languages.

    Supported MathML tags:
        `mfenced`, `mfrac`, `mi`, `mn`, `mo`, `mrow`, `msqrt`, `msub`, `msup`, `mtext`
    Supported mathematic operations:
        `+`, `-`, `×`, `/`, `^`, `∑`, `∏`
    - Nested `∑` or `∏` is not supported.
    - `∑` and `∏` are applied all over the dimension without specified limits by default.

    This class follows the implementation path:
        MathML --> ElementTree --> Other languages
    
    The translation from MathML to ElementTree is done via `package:lxml` provided by https://lxml.de
        
    Example:
        >>> mml_str = '<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow><mfrac><mi>q</mi><mrow><mi>w</mi><mi>h</mi></mrow></mfrac></mrow></math>'
        >>> MMLExpression(mml_str).to_numpy()
        ('q / (w * h)', ['h', 'q', 'w'])
        >>> mml_str = '<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow><mfrac><mi>q</mi><mrow><mn>&#x03c0;</mn><msup><mi>r</mi><mn>2</mn></msup></mrow></mfrac></mrow></math>'
        >>> MMLExpression(mml_str).to_numpy()
        ('q / (np.pi * r ** 2)', ['q', 'r'])
        >>> mml_str = '<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow><mfrac><mn>1</mn><mn>2</mn></mfrac><mrow><mo>&#x2211;</mo><mi>c</mi><msup><mi>z</mi><mn>2</mn></msup></mrow></mrow></math>'
        >>> MMLExpression(mml_str).to_numpy()
        ('1 / 2 * np.sum(c * z ** 2)', ['c', 'z'])
    """
    mml_numpy_map = {"×": "*", "−": "-", "≤": "<=", "≥": ">=", "π": "np.pi"}
    mml_sanitize_skip_mos = ["maximum", "matmul"]
    mml_sanitize_skip_tags = ["math", "mfrac", "msub", "msup"]
    mml_sanitize_term_tags = ["mfenced", "mfrac", "mi", "mn", "mrow", "msqrt", "msub", "msup"]
    
    def __init__(self, mml_str):
        """Construction function for MMLExpression class."""
        self.mml_str = mml_str
    

    @staticmethod
    def sanitize_display_etree(root):
        if not root.getchildren():
            return
        children = root.getchildren()
        for child in children:
            MMLExpression.sanitize_display_etree(child)
        for l_child, r_child in zip(children[:-1], children[1:]):
            if root.tag in MMLExpression.mml_sanitize_skip_tags:
                continue
            if l_child.getprevious() is not None and l_child.getprevious().text in MMLExpression.mml_sanitize_skip_mos:
                if l_child.getprevious().text == "matmul":
                    elem_space = etree.fromstring('<mspace nspace="1"></mspace>')
                    l_child.addnext(elem_space)
                    root.remove(l_child.getprevious())
        return root


    def to_mainpage_mml(self):
        """Convert MathML expression for display in mainpage.

        Returns:
            dict: converted MathML for main page
        """
        parser = etree.XMLParser()
        root = etree.fromstring(self.mml_str, parser)
        root = MMLExpression.sanitize_display_etree(root)
        mainpage_mml_str = {"concise_formula": None, "detail_formula": []}
        rx = re.compile(r'<mspace nspace="(?P<nspace>[0-9]+)"/>')
        for i, child in enumerate(root.getchildren()):
            if i == 0:
                if len(child.getchildren()) > 0 and child.getchildren()[0].tag == "mtext":
                    mainpage_mml_str["detail_formula"].append(f"<math>{etree.tostring(child).decode('utf-8')}</math>")
                elif len(child.getchildren()) > 1 and child.getchildren()[1].text == "=":
                    mainpage_mml_str["detail_formula"].append(f"<math>{etree.tostring(child).decode('utf-8')}</math>")
                else:
                    mainpage_mml_str["concise_formula"] = f"<math>{etree.tostring(child).decode('utf-8')}</math>"
                    mainpage_mml_str["concise_formula"] = rx.sub(lambda x: "<mtext>" + "&nbsp;" * int(x.group("nspace")) + "</mtext>", mainpage_mml_str["concise_formula"])
            else:
                mainpage_mml_str["detail_formula"].append(f"<math>{etree.tostring(child).decode('utf-8')}</math>")
        mainpage_mml_str["detail_formula"] = "<br/>".join(mainpage_mml_str["detail_formula"])
        mainpage_mml_str["detail_formula"] = rx.sub(lambda x: "<mtext>" + "&nbsp;" * int(x.group("nspace")) + "</mtext>", mainpage_mml_str["detail_formula"])
        return mainpage_mml_str


    def to_sidebar_mml(self):
        """Convert MathML expression for display in sidebar.

        Returns:
            str: converted MathML
        """
        parser = etree.XMLParser()
        root = etree.fromstring(self.mml_str, parser)
        root = MMLExpression.sanitize_display_etree(root)
        sidebar_mml_str = []
        for i, child in enumerate(root.getchildren()):
            if i == 0:
                if len(child.getchildren()) > 0 and child.getchildren()[0].tag == "mtext":
                    sidebar_mml_str.append(f'<math style="font-size: 12.5px; color: gray; padding-bottom: 0.2rem;">\n{etree.tostring(child).decode("utf-8")}\n</math>')
                elif len(child.getchildren()) > 1 and child.getchildren()[1].text == "=":
                    sidebar_mml_str.append(f'<math style="font-size: 12.5px; color: gray; padding-bottom: 0.2rem;">\n{etree.tostring(child).decode("utf-8")}\n</math>')
                else:
                    sidebar_mml_str.append(f'<div {"class=card-header " if len(root.getchildren()) > 1 else ""}'
                                           'style="font-size: 12.5px; text-align:center; padding-top: 0.2rem; padding-bottom: 0.2rem; padding-left: 0; padding-right: 0; margin-bottom: 0.4rem">'
                                           f'<math style="color: black; padding-bottom: 0.2rem;">\n{etree.tostring(child).decode("utf-8")}\n</math>'
                                            '</div>')
            else:
                sidebar_mml_str.append(f'<math style="font-size: 12.5px; color: gray; padding-bottom: 0.2rem;">\n{etree.tostring(child).decode("utf-8")}\n</math>')
        sidebar_mml_str = sidebar_mml_str[0] + '\n<br/>\n'.join(sidebar_mml_str[1:])
        rx = re.compile(r'<mspace nspace="(?P<nspace>[0-9]+)"/>')
        sidebar_mml_str = rx.sub(lambda x: "<mtext>" + "&nbsp;" * int(x.group("nspace")) + "</mtext>", sidebar_mml_str)
        return sidebar_mml_str
    

    def to_numpy(self, postfix=""):
        """Convert MathML expression to numpy expression

        Returns:
            list of str: converted numpy expression
            list of str: extracted variables
        """
        parser = etree.XMLParser()
        root = etree.fromstring(self.mml_str, parser)
        root = self.sanitize_etree(root)
        mml_str = etree.tostring(root)
        expr = []
        vars = []
        root = etree.fromstring(mml_str)
        for child in root.getchildren():
            sub_str = b"<math>" + etree.tostring(child) + b"</math>"
            sub_expr, sub_vars = MMLExpression.mml2numpy(sub_str, postfix)
            expr.append(sub_expr)
            vars.extend(sub_vars)
        code = MMLExpression.formulate_numpy_code(expr)
        return code

    @staticmethod
    def translate(mathml: str) -> str | None:
        """Helper to translate a MathML string, handling potential namespaces."""
        if not mathml:
            return None
        try:
            # Strip namespaces as MMLExpression tags comparison is literal
            clean_mathml = re.sub(r'\sxmlns="[^"]+"', '', mathml)
            return MMLExpression(clean_mathml).to_numpy()
        except Exception:
            return None
    

    @staticmethod
    def formulate_numpy_code(expr):
        """Formulate runable numpy codes

        Args:
            expr (list of strs): list of converted numpy expressions

        Returns:
            str: runable numpy codes
        """
        code = []
        i = 0
        while i < len(expr):
            if expr[i] == "SOLVE START":
                j = i + 1
                while expr[j] != "SOLVE END":
                    j += 1
                param = expr[i+1].split(" ")[-1]
                x0 = float(expr[i+2].split(" ")[-1])
                code.append("")
                code.append(f"def inner_param_func({param}):")
                for k in range(i+3, j):
                    for sub_expr in expr[k].split("\n"):
                        code.append(f"    {sub_expr}")
                code.append("    return error")
                code.append("")
                code.append(f"fsolve(inner_param_func, {x0}, xtol=1e-6, maxfev=1000)[0]")
                i = j + 1
            else:
                code.append(expr[i])
                i += 1
        code = "\n".join(code)
        return code


    @staticmethod
    def sanitize_etree(root):
        """Sanitize xml etree:
            - adding omitted times operator

        Args:
            root (lxml.etree._Element): root element of the lxml etree
        """
        if not root.getchildren():
            return
        children = root.getchildren()
        for child in children:
            MMLExpression.sanitize_etree(child)
        for l_child, r_child in zip(children[:-1], children[1:]):
            if root.tag in MMLExpression.mml_sanitize_skip_tags:
                continue
            if l_child.getprevious() is not None and l_child.getprevious().text in MMLExpression.mml_sanitize_skip_mos:
                continue
            l_tag = l_child.tag
            r_tag = r_child.tag
            if l_tag in MMLExpression.mml_sanitize_term_tags and r_tag in MMLExpression.mml_sanitize_term_tags:
                if l_tag == "mrow" and l_child.getchildren() and l_child.getchildren()[0].text in ["if", "elif"]:
                    continue
                if r_tag == "mrow" and r_child.getchildren() and r_child.getchildren()[0].text in ["["]:
                    continue
                elem_times = etree.fromstring("<mo>×</mo>")
                l_child.addnext(elem_times)
        return root

    @staticmethod
    def sanitize_numpy(numpy_expr):
        """Sanitize numpy expression by adjusting spaces and brackets"""
        sanitize_numpy_expr = []
        for sub_numpy_expr in numpy_expr.split("\n"):
            match = re.match(r"^ +", sub_numpy_expr)
            pos = match.span()[1] if match else 0
            sub_numpy_expr = sub_numpy_expr[:pos] + re.sub(" +", " ", sub_numpy_expr[pos:])
            sub_numpy_expr = sub_numpy_expr.rstrip(" ")
            sub_numpy_expr = re.sub(r" *:", ":", sub_numpy_expr)
            sub_numpy_expr = re.sub(r"(?<!^) *\[ *", " [", sub_numpy_expr)
            sub_numpy_expr = re.sub(r" *\] *", "] ", sub_numpy_expr)
            sub_numpy_expr = re.sub(r"\( *", "(", sub_numpy_expr)
            sub_numpy_expr = re.sub(r" *\)", ")", sub_numpy_expr)
            sub_numpy_expr = re.sub(r"([^ \*]) *\* *([^ \*])", r"\1 * \2", sub_numpy_expr)
            sub_numpy_expr = re.sub(r"\(\(([^\(\)]*)\)\)", r"(\1)", sub_numpy_expr)
            sub_numpy_expr = re.sub(r"\(\(([^\(\)]*)\(([^\(\)]*)\)\)\)", r"(\1(\2))", sub_numpy_expr)
            sub_numpy_expr = re.sub(r" *(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])", r"\1", sub_numpy_expr)
            sub_numpy_expr = re.sub(r"\(\(((\(([^\(\)]*)\)([^\(\)]*))+)\)\)", r"(\1)", sub_numpy_expr)
            sub_numpy_expr = re.sub(r"\(np.sum\(([^\(\)]+)\)\)", r"np.sum(\1)", sub_numpy_expr)
            sub_numpy_expr = re.sub(r"\(np.prod\(([^\(\)]+)\)\)", r"np.prod(\1)", sub_numpy_expr)
            sub_numpy_expr = re.sub(r"(?<!len)(?<!np\.exp)(?<!np\.sum)(?<!np\.prod)(?<!np\.maximum)(?<!np\.matmul)\(([^\+\-\*\/\,\(\)]*)\)", r"\1", sub_numpy_expr)
            sanitize_numpy_expr.append(sub_numpy_expr)
        sanitize_numpy_expr = "\n".join(sanitize_numpy_expr)
        return sanitize_numpy_expr
    

    @staticmethod
    def mml2numpy(mml_str, postfix=""):
        """Iterative conversion of MathML expression to numpy expression and variables"""
        expr = ""
        vars = []
        level = 0
        context = etree.iterparse(BytesIO(mml_str), events=("start", "end"))
        for action, elem in context:
            # tag:mfenced
            if action == "start" and elem.tag == "mfenced":
                expr += "( "
            if action == "end" and elem.tag == "mfenced":
                expr += " )"
            # tag:mfrac
            if action == "start" and elem.tag == "mfrac":
                if level == 0:
                    l_mml_str = etree.tostring(elem[0])
                    r_mml_str = etree.tostring(elem[1])
                    l_expr, l_vars = MMLExpression.mml2numpy(l_mml_str, postfix)
                    r_expr, r_vars = MMLExpression.mml2numpy(r_mml_str, postfix)
                    expr += f"({l_expr}) / ({r_expr}) "
                    vars.extend(l_vars + r_vars)
                level += 1
            if action == "end" and elem.tag == "mfrac":
                level -= 1
            # tag:mi
            if action == "start" and elem.tag == "mi" and level == 0:
                mi_expr = elem.text.strip(" ")
                expr += f"{mi_expr}{postfix} "
                vars.append(mi_expr)
            # tag:mn
            if action == "start" and elem.tag == "mn" and level == 0:
                mn_expr = elem.text.strip(" ")
                for k, v in MMLExpression.mml_numpy_map.items():
                    mn_expr = mn_expr.replace(k, v)
                expr += f"{mn_expr} "
            # tag:mo
            if action == "start" and elem.tag == "mo" and level == 0:
                mo_expr = elem.text.strip(" ")
                for k, v in MMLExpression.mml_numpy_map.items():
                    mo_expr = mo_expr.replace(k, v)
                expr += f"{mo_expr} "
            # tag:mrow
            if action == "start" and elem.tag == "mrow":
                if level == 0:
                    if elem[0].tag == "mo":
                        l_mml_str = elem[0].text.strip(" ")
                        l_expr, l_vars = MMLExpression.mml2numpy(b"<math>" + etree.tostring(elem[0]) + b"</math>")
                        r_mml_str = b"".join([etree.tostring(e) for e in elem[1:]])
                        r_mml_str = b"<math>" + r_mml_str + b"</math>"
                        r_expr, r_vars = MMLExpression.mml2numpy(r_mml_str, postfix)
                        if l_mml_str == "[":
                            expr += f"{l_expr}{r_expr}"
                        elif l_mml_str == "len":
                            expr += f"len({r_expr}) "
                            vars.extend(r_vars)
                        elif l_mml_str == "exp":
                            expr += f"np.exp({r_expr}) "
                            vars.extend(r_vars)
                        elif l_mml_str == "∑":
                            expr += f"np.sum({r_expr}) "
                            vars.extend(r_vars)
                        elif l_mml_str == "∏":
                            expr += f"np.prod({r_expr}) "
                            vars.extend(r_vars)
                            vars.extend(r_vars)
                        elif l_mml_str == "maximum":
                            first_mml_str = etree.tostring(elem[1])
                            first_mml_str = b"<math>" + first_mml_str + b"</math>"
                            first_expr, first_vars = MMLExpression.mml2numpy(first_mml_str, postfix)
                            second_mml_str = etree.tostring(elem[2])
                            second_mml_str = b"<math>" + second_mml_str + b"</math>"
                            second_expr, second_vars = MMLExpression.mml2numpy(second_mml_str, postfix)
                            expr += f"np.maximum({first_expr}, {second_expr})"
                            vars.extend(first_vars)
                            vars.extend(second_vars)
                        elif l_mml_str == "matmul":
                            first_mml_str = etree.tostring(elem[1])
                            first_mml_str = b"<math>" + first_mml_str + b"</math>"
                            first_expr, first_vars = MMLExpression.mml2numpy(first_mml_str, postfix)
                            second_mml_str = etree.tostring(elem[2])
                            second_mml_str = b"<math>" + second_mml_str + b"</math>"
                            second_expr, second_vars = MMLExpression.mml2numpy(second_mml_str, postfix)
                            expr += f"np.matmul({first_expr}, {second_expr})"
                            vars.extend(first_vars)
                            vars.extend(second_vars)
                        else:
                            expr += f"{l_expr}{r_expr}"
                            vars.extend(r_vars)
                    elif len(elem) == 3 and elem[0].tag == "msub" and elem[1].tag == "mspace" and elem[2].tag == "mi":
                        # for variables like k_La
                        l_expr, l_vars = MMLExpression.mml2numpy(b"<math>" + etree.tostring(elem[0]) + b"</math>")
                        r_expr, r_vars = MMLExpression.mml2numpy(b"<math>" + etree.tostring(elem[2]) + b"</math>")
                        expr += f"{l_expr}{r_expr} "
                        vars.extend(f"{l_expr}{r_expr}")
                    else:
                        sub_mml_str = b"".join([etree.tostring(e) for e in elem])
                        sub_mml_str = b"<math>" + sub_mml_str + b"</math>"
                        sub_expr, sub_vars = MMLExpression.mml2numpy(sub_mml_str, postfix)
                        expr += f"{sub_expr} "
                        vars.extend(sub_vars)
                level += 1
            if action == "end" and elem.tag == "mrow":
                level -= 1
            # tag:mspace
            if action == "start" and elem.tag == "mspace":
                expr += " " * int(elem.attrib["nspace"])
            # tag:msqrt
            if action == "start" and elem.tag == "msqrt":
                if level == 0:
                    sub_mml_str = b"".join([etree.tostring(e) for e in elem])
                    sub_mml_str = b"<math>" + sub_mml_str + b"</math>"
                    sub_expr, sub_vars = MMLExpression.mml2numpy(sub_mml_str, postfix)
                    expr += f"({sub_expr}) ** 0.5 "
                    vars.extend(sub_vars)
                level += 1
            if action == "end" and elem.tag == "msqrt":
                level -= 1
            # tag:msub
            if action == "start" and elem.tag == "msub":
                if level == 0:
                    l_mml_str = etree.tostring(elem[0])
                    r_mml_str = etree.tostring(elem[1])
                    l_expr, _ = MMLExpression.mml2numpy(l_mml_str)
                    r_expr, _ = MMLExpression.mml2numpy(r_mml_str)
                    expr += f"{l_expr}_{r_expr}{postfix} "
                    vars.append(f"{l_expr}_{r_expr}")
                level += 1
            if action == "end" and elem.tag == "msub":
                level -= 1
            # tag:msup
            if action == "start" and elem.tag == "msup":
                if level == 0:
                    l_mml_str = etree.tostring(elem[0])
                    r_mml_str = etree.tostring(elem[1])
                    l_expr, l_vars = MMLExpression.mml2numpy(l_mml_str, postfix)
                    r_expr, r_vars = MMLExpression.mml2numpy(r_mml_str, postfix)
                    if r_expr == "*":
                        expr += f"{l_expr}_star "
                        vars.extend(l_vars)
                    else:
                        expr += f"({l_expr}) ** ({r_expr}) "
                        vars.extend(l_vars + r_vars)
                level += 1
            if action == "end" and elem.tag == "msup":
                level -= 1
            # tag:mtext
            if action == "start" and elem.tag == "mtext" and level == 0:
                mtext_expr = elem.text.replace(",", "_").strip(" ")
                expr += mtext_expr
        expr = MMLExpression.sanitize_numpy(expr)
        vars = sorted(list(set(vars)))
        return expr, vars


if __name__ == "__main__":
    import doctest
    doctest.testmod()