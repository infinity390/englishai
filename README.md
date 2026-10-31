# EnglishAI

EnglishAI is a symbolic English parser and reasoning engine written in Python.

Instead of using statistical prediction, EnglishAI tries to represent language using explicit symbolic structures and grammar rules.

The project is experimental and under active development.

## Code Example for Demonstration

```py
from englishai import code, decode, answer
s = "my mother's mother's daughter was mary"
eq = code(s)
print(f"EQUATION: {eq}\nSENTENCE: {s}\nSENTENCE AFTER DECODING EQUATION IN PRESENT TENSE: {decode(eq)}")
print()
# basic question answerer based on context
question_context = [
    ("who are you", "i am your father. you are a boy."),
    ("is mary alive", "your father is my father. your mother is my mother. you are mary. i killed my sister"),
    ("am i alive", "am alive i"), # invalid sentence
    ("am i alive", "i killed john"),
    ("who is my mother", "my mother's mother's daughter is mary"),
    ("is bob alive", "i am your father. my son is bob. i killed my son."),
    ("who is john", "john is my mother."), # john is a boy name and boys can't be mother
    ("is john alive", "i kills john's father"), # wrong grammar
    ("is john alive", "she kills john's father"), # corrected grammar
]
for question, context in question_context:
  try:
    out = answer(question, context)
  except:
    out = None
  print(f"CONTEXT: {context}")
  print(f"QUESTION: {question} ?")
  if out is not None:
    print(f"ANSWER: {'{'+', '.join(out)+'}' if isinstance(out, list) else out}")
  else:
    print("ANSWER: the reasoning proves that the context is contradictory / grammar error / incorrect format or spelling error / unsupported sentence or out of vocabulary")
  print()
```

## Output of the Code

```
EQUATION: equal(daughter(mother(mother(i))),mary)
SENTENCE: my mother's mother's daughter was mary
SENTENCE AFTER DECODING EQUATION IN PRESENT TENSE: my mother's mother's daughter is mary

CONTEXT: i am your father. you are a boy.
QUESTION: who are you ?
ANSWER: {i, your son}

CONTEXT: your father is my father. your mother is my mother. you are mary. i killed my sister
QUESTION: is mary alive ?
ANSWER: no

CONTEXT: am alive i
QUESTION: am i alive ?
ANSWER: the reasoning proves that the context is contradictory / grammar error / incorrect format or spelling error / unsupported sentence or out of vocabulary

CONTEXT: i killed john
QUESTION: am i alive ?
ANSWER: yes

CONTEXT: my mother's mother's daughter is mary
QUESTION: who is my mother ?
ANSWER: {your mother, mary, mary's mother's daughter}

CONTEXT: i am your father. my son is bob. i killed my son.
QUESTION: is bob alive ?
ANSWER: no

CONTEXT: john is my mother.
QUESTION: who is john ?
ANSWER: the reasoning proves that the context is contradictory / grammar error / incorrect format or spelling error / unsupported sentence or out of vocabulary

CONTEXT: i kills john's father
QUESTION: is john alive ?
ANSWER: the reasoning proves that the context is contradictory / grammar error / incorrect format or spelling error / unsupported sentence or out of vocabulary

CONTEXT: she kills john's father
QUESTION: is john alive ?
ANSWER: yes
```

## Demonstration of Version 2 which is in Development

```py
from englishai.version2 import Table, code
def run_test_suite(name, suite_text):
    print(f"=== RUNNING TEST SUITE: {name} ===")
    t = Table()
    section = None    
    for line in suite_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper() == "CONTEXT:":
            section = "CONTEXT"
            continue
        elif line.upper() == "QUESTIONS:":
            section = "QUESTIONS"
            continue            
        if section == "CONTEXT":
            res = t.context(code(line))
            print(f"Context added [{line}]: {res}")
        elif section == "QUESTIONS":
            eq = code(line)
            res = None
            if eq.name == "who":
                res = t.ask(eq)
            else:
                res = t.question(eq)
            print(f"Q: {line}\n  -> {res}\n")
    print("\n")
suites = {
    "Basic Family & Identity": """
CONTEXT:
john is your father
mary is your mother
you are my sister
i am a boy

QUESTIONS:
who am i
who are you
who is john
who is mary
is john a boy
is mary a girl
are you john's son
is mary your mother
am i your brother
""",
    "Sibling Derivation": """
CONTEXT:
john is your father
mary is your mother
john is my father
mary is my mother
you are a girl

QUESTIONS:
who is my sister
who is my brother
""",
    "Gender Mutual Exclusivity": """
CONTEXT:
alice is a girl
bob is a boy

QUESTIONS:
is alice a boy
is bob a girl
is alice a girl
is bob a boy
"""
}
for name, text in suites.items():
    run_test_suite(name, text)
```

## Output of the code

```
=== RUNNING TEST SUITE: Basic Family & Identity ===
Context added [john is your father]: True
Context added [mary is your mother]: True
Context added [you are my sister]: True
Context added [i am a boy]: True
Q: who am i
  -> ['you', "john's son", 'my brother', "mary's son"]

Q: who are you
  -> ['i', "john's daughter", "mary's daughter", 'your sister']

Q: who is john
  -> ['john', 'my father', 'your father']

Q: who is mary
  -> ['mary', 'my mother', 'your mother']

Q: is john a boy
  -> True

Q: is mary a girl
  -> True

Q: are you john's son
  -> False

Q: is mary your mother
  -> True

Q: am i your brother
  -> True



=== RUNNING TEST SUITE: Sibling Derivation ===
Context added [john is your father]: True
Context added [mary is your mother]: True
Context added [john is my father]: True
Context added [mary is my mother]: True
Context added [you are a girl]: True
Q: who is my sister
  -> ['i', "john's daughter", "mary's daughter", 'your sister']

Q: who is my brother
  -> ["john's son", "mary's son", 'your brother']



=== RUNNING TEST SUITE: Gender Mutual Exclusivity ===
Context added [alice is a girl]: True
Context added [bob is a boy]: True
Q: is alice a boy
  -> False

Q: is bob a girl
  -> False

Q: is alice a girl
  -> True

Q: is bob a boy
  -> True
```