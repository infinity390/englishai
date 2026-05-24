from .code import *
from .infer import *
def answer(question, conversation=[]):
    table = Table()
    a = [code(item) for item in conversation]
    q = code(question)
    for item in a:
        table.equate(item)
    return table.lambda_compute(q)
