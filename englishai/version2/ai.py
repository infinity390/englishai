from .code import *
from .infer import *
def answer(text, return_table=False):
    text = text.strip()
    context, question = text.split("\n\n")
    context, question = context.strip().splitlines(), question.strip().splitlines()
    t = Table()
    for item in context:
        t.context(code(item))
    out = "\n".join([", ".join(t.ask(code(item))) if code(item).name == "who" else str(t.question(code(item))) for item in question])
    if return_table:
        return out, t
    else:
        return out
    
