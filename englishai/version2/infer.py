from .base import *
import itertools
import copy
from .decode import *
from .code import *
class Condition:
    def __init__(self, expr, true=None, false=None, unknown=None):
        self.expr = expr
        self.true = true or []
        self.false = false or []
        self.unknown = unknown or []
    def __repr__(self):
        return (
            f"Condition("
            f"{self.expr!r}, "
            f"true={self.true!r}, "
            f"false={self.false!r}, "
            f"unknown={self.unknown!r})"
        )
def parse(s):
    lines = [
        (len(x) - len(x.lstrip()), x.strip())
        for x in s.splitlines()
        if x.strip()
    ]
    def parse_block(i, indent):
        result = []
        while i < len(lines):
            level, text = lines[i]
            if level < indent:
                break
            if level > indent:
                raise SyntaxError(f"Unexpected indentation: {text}")
            if text.startswith("IF "):
                expr = text[3:]
                condition = Condition(
                    code(expr),
                    [],
                    [],
                    []
                )
                i += 1
                branches = {
                    "TRUE": condition.true,
                    "FALSE": condition.false,
                    "UNKNOWN": condition.unknown
                }
                while i < len(lines):
                    level2, text2 = lines[i]
                    if level2 <= indent:
                        break
                    if text2 not in branches:
                        raise SyntaxError(
                            f"Expected TRUE/FALSE/UNKNOWN, got {text2!r}"
                        )
                    i += 1
                    branch, i = parse_block(i, level2 + 1)
                    branches[text2].extend(branch)
                result.append(condition)
            else:
                head, *sentence = text.split(maxsplit=1)
                if sentence:
                    equation = code(sentence[0])
                else:
                    equation = None
                result.append((head, equation))
                i += 1
        return result, i
    return parse_block(0, lines[0][0])[0]
def show(x, level=0):
    space = " " * level
    for item in x:
        if isinstance(item, Condition):
            print(space + "IF", item.expr)
            print(space + " TRUE")
            show(item.true, level + 2)
            print(space + " FALSE")
            show(item.false, level + 2)
            print(space + " UNKNOWN")
            show(item.unknown, level + 2)
        else:
            head, equation = item
            if equation is None:
                print(space + head)
            else:
                print(space + head, equation)
def id_helper(a, b):
    a = set(a)
    b = set(b)
    a, b = a-b, b-a
    if len(a) == 1 and len(b) == 1:
        return list(a)[0], list(b)[0]
    return None
def collect_id_nodes(node):
    out = []
    if (
        isinstance(node, TreeNode)
        and node.name == "id"
    ):
        out.append(node)
    for child in getattr(node, "children", []):
        out.extend(collect_id_nodes(child))
    return out
def valid_actor_eq(eq):
    try:
        eq = actor_to_phrase(eq)
    except:
        return False
    return True
class Table:
    def __init__(self):
        self.id_system = []
        self.table_entry_list = {}
        self.curr = 0
        self.create_new_nodes = True
        s = """
IF x is mary
 TRUE
  ASSERT x is a girl
IF x is john
 TRUE
  ASSERT x is a boy
IF x is a girl
 FALSE
  ASSERT x is a boy
IF x is y
 TRUE
  ASSERT x's mother is y's mother
IF x is a boy
 TRUE
  IF x is a girl
   TRUE
    THROW
 FALSE
  ASSERT x is a girl
IF x is y's mother
 TRUE
  ASSERT x is a girl
  IF Y is a girl
   TRUE
    ASSERT y is x's daughter
   FALSE
IF x is y's father
 TRUE
  ASSERT x is a boy
  IF Y is a girl
   TRUE
    ASSERT y is x's daughter
   FALSE
"""
        self.rule = parse(s)
    def find_human(self, node):
        for key in self.table_entry_list.keys():
            if node in self.table_entry_list[key].entry:
                return key
        out = self.create()
        self.table_entry_list[out].entry += [node]
        return out
    def create(self):
        out = TableEntry()
        self.table_entry_list[self.curr] = out
        self.curr = self.curr+1
        return self.curr - 1
    def find_id(self,eq):
        return self.normalize_id(self.find_human(eq))
    def equate_id(self, a, b):
        if a==b:
            return a
        n = TableEntry()
        p, q = self.table_entry_list[a], self.table_entry_list[b]
        n.entry = list(set(p.entry + q.entry))
        n.attr = p.attr
        for key, item in q.attr.items():
            if key not in n.attr.keys():
                n.attr[key] = item
            else:
                if key in ["mother", "father"]:
                    self.equate_id(item, n.attr[key])
                if key in ["girl", "boy"]:
                    if n.attr[key] == "true" and item == "false" or\
                       n.attr[key] == "false" and item == "true":
                        return None
        g = self.create()
        self.id_system.append(list(sorted([g,a,b])))
        self.table_entry_list[g] = n
        del self.table_entry_list[a]
        del self.table_entry_list[b]
        return g
    def reduce_table(self):
        for item in self.id_system:
            for item2 in item[1:]:
                if item2 in self.table_entry_list.keys():
                    self.table_entry_list[item[0]] = self.table_entry_list[item2]
                    del self.table_entry_list[item2]
        for key2 in self.table_entry_list.keys():
            for key in self.table_entry_list[key2].attr.keys():
                if isinstance(self.table_entry_list[key2].attr[key], int):
                    for item in self.id_system:
                        for item2 in item[1:]:
                            if self.table_entry_list[key2].attr[key] == item2:
                                self.table_entry_list[key2].attr[key] = item[0]
        self.id_system = []                        
    def process_rule(self, rule, x=None, y=None):
        def helper(lst, x, y):
            out = []
            for item in lst:
                item = replace(item, TreeNode("x"), TreeNode(f"d_{x}"))
                item = replace(item, TreeNode("y"), TreeNode(f"d_{y}"))
                out.append(self.create_node(item))
            return out
        log = []
        if rule == []:
            return 0
        if isinstance(rule, list):
            for item in rule:
                if isinstance(item, Condition):
                    log.append(self.process_rule(item, x, y))
                elif isinstance(item, tuple):
                    if item[0] == "THROW":
                        return None
                    if item[0] == "ASSERT":
                        if item[1].name in ["girl", "boy"]:
                            self.table_entry_list[helper([item[1].children[0]],x,y)[0]].attr[item[1].name] = "true"
        if isinstance(rule, Condition):
            if rule.expr.name == "equal":
                out = helper(rule.expr.children, x, y)
                if None in out:
                    log.append(self.process_rule(rule.unknown, x, y))
                elif out[0] == out[1]:
                    log.append(self.process_rule(rule.true, x, y))
                else:
                    log.append(self.process_rule(rule.false, x, y))
            if rule.expr.name in ["girl", "boy"]:
                out = helper([rule.expr.children[0]],x,y)[0]
                if out is not None:
                    out2 = 0
                    if rule.expr.name in self.table_entry_list[out].attr.keys():
                        if rule.expr.name not in self.table_entry_list[out].attr.keys():
                            log.append(self.process_rule(rule.unknown, x, y))
                        else:
                            out2 = self.table_entry_list[out].attr[rule.expr.name]
                            if out2 == "true":
                                log.append(self.process_rule(rule.true, x, y))
                            elif out2 == "false":
                                log.append(self.process_rule(rule.false, x, y))
        if None in log:
            return None
        return 0
    def create_node(self, node):
        if node.name.startswith("d_"):
            return int(node.name[2:])
        if node.children == []:
            for key in self.table_entry_list.keys():
                if node in self.table_entry_list[key].entry:
                    return key
            out = self.create()
            self.table_entry_list[out].entry += [node]
            return out
        out = self.create_node(node.children[0])
        if node.name in ["mother", "father"]:
            if node.name in self.table_entry_list[out].attr.keys():
                return self.table_entry_list[out].attr[node.name]
            elif self.table_entry_list[out].entry != []:
                new = self.create()
                self.table_entry_list[out].attr[node.name] = new
                return new
        return None
    def equate_eq(self, a, b):
        if not valid_actor_eq(a) or not valid_actor_eq(b):
            return None
        p = self.create_node(a)
        q = self.create_node(b)
        if p == q:
            return 0
        if self.process_all_rule() is None:
            return None
        if self.equate_id(p, q) is None:
            return None
        if self.process_all_rule() is None:
            return None
        return 0
    def process_all_rule(self):
        orig = str(self)
        done = True
        out = None
        if len(self.table_entry_list.keys()) == 1:
            out = self.create()
        while done:
            done = False
            id_lst = list(self.table_entry_list.keys())
            for item in self.rule:
                if len(id_lst) == 1:
                    if self.process_rule(item, id_lst[0], out) is None:
                        return None
                else:
                    for item2 in itertools.permutations(id_lst, 2):
                        if self.process_rule(item, *item2) is None:
                            return None
            if orig != str(self):
                done = True
                orig = str(self)
        return 0
    def equate_bool_eq(self, eq):
        if len(eq.children) != 1 or not valid_actor_eq(eq.children[0]):
            return None
        out = self.create_node(eq.children[0])
        if out is None:
            return None
        if eq.name != "not":
            if eq.name not in self.table_entry_list[out].attr.keys():
                self.table_entry_list[out].attr[eq.name] = "true"
        if self.process_all_rule() is None:
            return None
        return out
    def lambda_compute(self, eq):
        if eq.name == "lambda":
            output = []
            for key, item in self.table_entry_list.items():
                c = replace(eq.children[1], eq.children[0], TreeNode(str(key)).fx("id"))
                s = replace(eq.children[2], eq.children[0], TreeNode(str(key)).fx("id"))
                u = replace(eq.children[3], eq.children[0], TreeNode(str(key)).fx("id"))
                out = self.bool_eq(c)
                if out is True:
                    output.append(s)
                elif out is False:
                    output.append(u)                    
            for i in range(len(output)-1,-1,-1):
                if output[i] == TreeNode("DELETE") or contain2(output[i], TreeNode("DELETE")):
                    output.pop(i)
            output2 = []
            for item in output:
                output2 += self.rm_eq_id(item)
            output = list(set(output2))
            if len(output) == 1:
                return output[0]
            return output
        return []
    def bool_eq(self, eq):
        number_lst = []
        number = None
        if eq.name == "equal":
            for item in eq.children:
                if item.name == "id":
                    number_lst.append([int(item.children[0].name)])
                elif valid_actor_eq(item):
                    tmp = self.find_id(item)
                    if tmp is None:
                        return None
                    number_lst.append(tmp)
                else:
                    return None
            
            if number_lst is None:
                return None
            if number_lst[0][0] in number_lst[1]:
                return True
            else:
                return False
        elif len(eq.children) == 1:
            item = eq.children[0]
            if item.name == "id":
                number = [int(item.children[0])]
            elif valid_actor_eq(item):
                number = self.find_id(item)
                if number is None:
                    return None
            else:
                return None
        elif len(eq.children) == 2 and eq.name == "kill":
            number_lst = []
            for item in eq.children:
                if item.name == "id":
                    number_lst.append([int(item.children[0].name)])
                elif valid_actor_eq(item):
                    tmp = self.find_id(item)
                    if tmp is None:
                        return None
                    number_lst.append(tmp)
                else:
                    return None
            if self.table_entry_list[number_lst[0][0]].killed == []:
                return False
            if set(number_lst[1]) <= set(self.table_entry_list[number_lst[0][0]].killed):
                return True
            return False
        else:
            return None
        lst = number
        lst2= []
        for number in lst:
            if eq.name == "live":
                lst2.append(self.table_entry_list[number].living_state)
            if eq.name == "die":
                lst2.append(not self.table_entry_list[number].living_state)
            if eq.name == "girl":
                if len(self.table_entry_list[number].gender) == 1:
                    lst2.append(not self.table_entry_list[number].gender[0])
            if eq.name == "boy":
                if len(self.table_entry_list[number].gender) == 1:
                    lst2.append(self.table_entry_list[number].gender[0])
        if len(set(lst2)) != 1:
            return None
        return lst2[0]
    def equate_verb(self, eq):
        if eq.name in ["kill"] and len(eq.children) == 2:
            index = self.find_id(eq.children[0])
            index2 = self.find_id(eq.children[1])
            if len(index) != 1 or len(index2) == 0:
                return None
            self.table_entry_list[index[0]].killed += index2
            return index
        return None
    def copy_table(a, b):
        a.table_entry_list = copy.deepcopy(b.table_entry_list)
        a.id_system = copy.deepcopy(b.id_system)
    def equate(self, eq):
        orig = copy.deepcopy(self)
        a = self.equate_bool_eq(eq)
        b = None
        c = None
        d = None
        if eq.name == "equal":
            b = self.equate_eq(*eq.children)
            if b is None:
                self = orig
                return None
            else:
                self.reduce_table()
                return b
        if eq.name == "kill":
            c = self.equate_verb(eq)
            d = self.equate_bool_eq(eq.children[1].fx("die"))
            if c is None or d is None:
                self = orig
                return None
            else:
                return c
        if a is not None:
            return a
        self.copy_table(orig)
        return None
    def alias_gen(self):
        for key, item in self.table_entry_list.items():
            item.alias = list(item.entry)

        relations = [
            "mother",
            "father",
            "son",
            "daughter",
            "sister",
            "brother"
        ]
        for _ in range(2):
            snapshot = {
                k: list(v.alias)
                for k, v in self.table_entry_list.items()
            }
            for key, aliases in snapshot.items():
                if not aliases:
                    continue
                # shortest alias
                base = min(
                    aliases,
                    key=lambda x: len(str_form(x))
                )
                # FIX:
                # avoid TreeNode(TreeNode(...))
                base_node = (
                    base
                    if isinstance(base, TreeNode)
                    else TreeNode(base)
                )
                for relation in relations:
                    targets = self.find_human(
                        key,
                        [relation],
                        False
                    )
                    if len(targets) != 1:
                        continue
                    # normalize single value -> list
                    if not isinstance(targets, list):
                        targets = [targets]
                    new_alias = base_node.fx(relation)
                    for target in targets:
                        if target not in self.table_entry_list:
                            continue
                        if (
                            new_alias
                            not in self.table_entry_list[target].alias
                        ):
                            self.table_entry_list[target].alias.append(
                                new_alias
                            )
    def find_from_id(self, number):
        out = [item if isinstance(item, TreeNode) else TreeNode(item) for item in self.table_entry_list[number].alias]
        return list(set(out))
    def rm_eq_id(self, eq):
        self.alias_gen()
        id_nodes = collect_id_nodes(eq)
        if not id_nodes:
            return [eq]
        replacement_choices = []
        for node in id_nodes:
            number = int(node.children[0].name)
            aliases = self.find_from_id(number)
            if aliases == []:
                aliases = [node]
            replacement_choices.append(aliases)
        outputs = []
        for combo in itertools.product(*replacement_choices):
            new_eq = eq
            for old_node, new_node in zip(
                id_nodes,
                combo
            ):
                new_eq = replace(
                    new_eq,
                    old_node,
                    new_node
                )
            outputs.append(new_eq)
        return outputs
    def __repr__(self):
        s = None
        if self.id_system == []:
            s = []
        else:
            s = [str(self.id_system)]
        for key, item in self.table_entry_list.items():
            s.append(f"id {key}")
            s.append(str(item))
            s.append("")
        return "\n".join(s)
class TableEntry:
    def __init__(
        self,
        entry=None,
        attr=None
    ):
        self.entry = entry if entry else []
        self.attr = attr if attr else {}
    def __repr__(self):
        line = "+" + "-" * 60 + "+"
        s = line + "\n"
        for key, item in self.attr.items():
            s += f"{key} : {item}\n"
        s += line + "\n"
        s += "| Entries\n"
        if len(self.entry) == 0:
            s += "|   <empty>\n"
        else:
            for eq in self.entry:
                s += f"|   {eq}\n"
        s += line
        return s
