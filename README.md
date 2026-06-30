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

