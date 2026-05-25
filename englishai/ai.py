from .code import *
from .infer import *
def swap_i_you(node):
    if node is None:
        return None
    node.children = [
        swap_i_you(child)
        for child in node.children
    ]
    if node.children == []:
        if node.name == "i":
            return TreeNode("you")
        elif node.name == "you":
            return TreeNode("i")
    return node
def answer(question, conversation=[]):
    table = Table()
    a = [code(item) for item in conversation]
    q = code(question)
    for item in a:
        table.equate(item)
    for key in table.table_entry_list.keys():
        table.table_entry_list[key].detect_gender()
    table.create_new_nodes = False
    out = table.lambda_compute(q)
    if not isinstance(out, list):
        out = [out]
    out = [actor_to_phrase(swap_i_you(item)) for item in out]
    if len(out) == 1:
        return out[0]
    return out
