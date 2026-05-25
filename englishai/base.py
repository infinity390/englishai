import copy
def streq(node):
    if not node.children:
        return node.name
    return node.name + "(" + ",".join(streq(c) for c in node.children) + ")"
def str_form(node):
    def recursive_str(node, depth=0):
        result = "{}{}".format(' ' * depth, node.name)
        for child in node.children:
            result += "\n" + recursive_str(child, depth + 1)
        return result
    if not isinstance(node, TreeNode):
        return "d_"+str(node)
    return recursive_str(node)
def tree_form(tabbed_strings):
    lines = tabbed_strings.split("\n")
    root = TreeNode("Root")
    current_level_nodes = {0: root}
    stack = [root]
    for line in lines:
        level = line.count(' ')
        node_name = line.strip()
        node = TreeNode(node_name)
        while len(stack) > level + 1:
            stack.pop()
        parent_node = stack[-1]
        parent_node.children.append(node)
        current_level_nodes[level] = node
        stack.append(node)
    return root.children[0]
class TreeNode:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children if children else []
    def fx(self, name):
        return TreeNode(name, [self])
    def __repr__(self):
        return streq(self)
    def __hash__(self):
        return hash(str_form(self))
    def __eq__(self, other):
        return isinstance(other, TreeNode) and str_form(self) == str_form(other)
def gender(eq):
    male = ["father", "son", "bob", "brother", "john", "he"]
    female = ["mother", "daughter", "sister", "lucy", "mary", "she", "girl-friend", "sister"]
    if eq.name in male:
        return "male"
    elif eq.name in female:
        return "female"
    return "unknown"
def replace(equation, find, r):
  if str_form(equation) == str_form(find):
    return r
  col = TreeNode(equation.name, [])
  for child in equation.children:
    col.children.append(replace(child, find, r))
  return col
def contain2(equation, what):
    if equation.name == what:
        return True
    if equation.children == []:
        return False
    return any(contain2(child, what) for child in equation.children)
def contain(equation, what):
    if equation == what:
        return True
    if equation.children == []:
        return False
    return any(contain(child, what) for child in equation.children)
def dowhile(eq, fx):
    if eq is None:
        return None
    while True:
        orig = copy.deepcopy(eq)
        eq2 = fx(eq)
        if eq2 is None:
            return None
        eq = copy.deepcopy(eq2)
        if eq == orig:
            return orig
