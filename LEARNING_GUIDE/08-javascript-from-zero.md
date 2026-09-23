# 08 — JavaScript From Zero

**Prerequisites:** none beyond curiosity. Where this chapter needs an idea from
earlier — a process, a request, an event loop — it re-explains it in one or two
sentences rather than assuming you remember.

**Why there is a second language at all.** This system is written in two
languages. The part that runs on the server is Python. The part that runs
inside the user's web browser is JavaScript. Neither is a fashion choice, and
the reason is not that one is better. It is that **the browser can only run
JavaScript**, and the server can only usefully run something that has libraries
for reading documents and doing machine-learning work. Those are two different
requirements, so they got two different answers.

**One note before we begin, so nothing confuses you later.** The real files in
this project's browser code end in `.ts` or `.tsx`, not `.js`. That is
**TypeScript**, which is JavaScript plus extra words that describe what kind of
value each thing is. Those extra words are Chapter 09's subject. In this
chapter, whenever real code contains them, I will point them out and show you
the same code as plain JavaScript. **Everything you learn here is true of
TypeScript too**, because TypeScript *is* JavaScript with additions.

---

# Part A — Where JavaScript Came From and Why It Is Unavoidable

## A.1 The real-world problem

In 1994 a web page was a document. The server sent some text with formatting
instructions, the browser drew it, and that was the end. If you filled in a
form and made a mistake, you found out only after sending it to the server and
waiting several seconds for a reply. If you wanted a menu to open when you
moved the mouse over it, you could not have one.

**The problem: the page was dead.** Everything interesting had to be a round
trip to a computer somewhere else.

## A.2 What a browser actually is

A quick anchor, because the rest of the chapter depends on it.

When you open Chrome or Firefox, the operating system starts a **process** — a
running program with its own private area of memory that other programs cannot
read. That process downloads text from a server and draws it on your screen.

**A browser is a program that draws documents and, in modern times, also runs
programs inside those documents.** The programs it runs must be safe: a web
page from a stranger must not be able to read your files, install anything, or
watch what you type into another tab. That safety requirement shaped
everything about the language that ended up inside it.

## A.3 Why the server's language cannot simply be used

An obvious idea: if the server is written in Python, let the browser run Python
too.

It fails for four reasons, and they are worth stating because they explain why
the situation will not change soon:

1. **Every browser would have to agree.** A web page is sent to browsers made
   by different companies. They must all understand the same language, or the
   page works for some people and not others.
2. **Safety.** The language must be unable to touch the user's files or other
   tabs. Python can read your whole disk; a browser language must not be able
   to.
3. **It must start instantly.** A page should appear in under a second. There
   is no time to install anything.
4. **History decided it.** JavaScript arrived first, every browser
   implemented it, and millions of pages depend on it. **Once a standard is
   everywhere, replacing it is nearly impossible** regardless of merit.

## A.4 The history, briefly, because it explains the weirdness

JavaScript was created in 1995 by Brendan Eich at Netscape, reportedly in about
ten days, to make pages interactive. It was named "JavaScript" for marketing
reasons — Java was popular at the time — and the two languages are unrelated.
That name has confused beginners for thirty years.

Being designed in ten days had consequences. Some genuinely strange decisions
were made and could never be removed, because removing them would break
existing web pages. **This is the most important thing to understand about
JavaScript's oddities: they are not mistakes that nobody noticed. They are
mistakes that cannot be fixed, because the web must not break.** Old pages must
keep working forever.

The standard was later given a neutral name, **ECMAScript**, so that no single
company owned it. Versions are known by year: ES2015 (also called ES6) was the
turning point that added most of the modern features you will see in this
chapter — proper variables, arrow functions, classes, modules, promises.

**Where JavaScript runs today:**

- **In browsers**, which is where this project's frontend runs.
- **On servers**, through Node.js — a program that runs JavaScript outside a
  browser. This project uses Node to *build* the frontend and to run the
  development server, even though the application code ends up in the browser.
- **At the network edge**, on small servers close to users.

## A.5 Why this repository has both languages

The server side needs libraries for reading PDFs, doing optical character
recognition on scans, and running machine-learning models. Those libraries are
overwhelmingly Python. The browser side needs to run in a browser, which means
JavaScript. **There is no version of this system that uses only one language**,
and every serious web product you will work on will have the same split.

---

# Part B — Running JavaScript

## B.1 The console — your practice ground

Every browser has a built-in place to type JavaScript and see results
immediately. Press **F12** (or right-click the page and choose *Inspect*), then
open the tab labelled **Console**.

Type this and press Enter:

```javascript
2 + 3
```

It prints `5`. You now have a working programming environment with nothing
installed. Everything in Parts C to E can be tried here, and **you should try
it** — reading about a language and using it are different activities.

## B.2 A script inside a page

A web page is a text file describing what to show. A `<script>` tag inside it
contains a program:

```html
<!DOCTYPE html>
<html>
  <body>
    <h1 id="title">Hello</h1>
    <script>
      document.getElementById("title").textContent = "Changed by JavaScript";
    </script>
  </body>
</html>
```

Save that as `test.html`, open it in a browser, and the heading says "Changed
by JavaScript". The browser drew the page, then ran the program, and the
program changed the page.

## B.3 Node — JavaScript without a browser

Node.js is a program that runs JavaScript files directly:

```bash
node hello.js
```

**Why it exists:** once browsers had fast JavaScript engines, people realised
that engine could run anywhere. Node made it possible to use one language for
both sides of a web application.

**Where this repository uses Node:** to run the development server and to build
the frontend. The `node_modules/` folder listed in `.gitignore` is where its
libraries are installed — thousands of files, generated from a recipe, never
stored in version control.

## B.4 What actually happens to this project's frontend code

Important, because it explains why you cannot just open the project's files in
a browser.

The code is written in TypeScript, spread across hundreds of files, and uses
`import` statements to refer to each other. A browser cannot use that directly.
So a **build step** runs first: a tool reads all the files, removes the
TypeScript type words, joins the files together, shrinks the result, and
produces plain JavaScript that browsers understand.

That is what `npm run build` does, and it is why Chapter 01 warned that editing
a frontend file inside the running container has no effect until the container
is restarted — **the browser is served the built output, not your file.** A
multi-hour debugging session was once lost to exactly that.

---

# Part C — Values and Variables

## C.1 Storing a value

**The problem.** A program computes something and needs to use it later. Without
names, every value would have to be recomputed or written out again.

**A variable is a name that refers to a value.**

```javascript
let name = "Priya";
const chunks = 200;
```

**Why there are two words**, and this is a real design lesson:

- **`const`** means the name will always refer to this same value. Trying to
  reassign it is an error.
- **`let`** means the name may be pointed at something else later.

```javascript
let count = 1;
count = 2;          // fine

const limit = 10;
limit = 20;         // TypeError: Assignment to constant variable.
```

**Which should you use?** `const` by default, `let` only when you genuinely
reassign. **The reason is not tidiness, it is reading speed:** when you see
`const`, you know that name will never change meaning anywhere below, so you do
not have to search. That is a small saving on one line and an enormous saving
across a large file.

**A warning about `const` that catches everyone once.** `const` protects the
*name*, not the contents:

```javascript
const list = [1, 2, 3];
list.push(4);        // ALLOWED — the list changed
list = [9];          // ERROR — the name cannot point somewhere else
```

This is the same idea as Chapter 06's model of variables in Python: **a
variable is a name tag attached to a value, not a box holding it.** `const`
nails the tag to one object; it does not freeze the object.

**And a third word you will meet in old code: `var`.** It is the original one
from 1995, and it behaves in surprising ways — it ignores block boundaries, and
it can be used before the line that declares it. It is not removed because old
pages depend on it. **Never write `var` in new code.** If you see it, you are
reading something old.

## C.2 The kinds of value

| Kind | Example | What it is |
|---|---|---|
| number | `5`, `0.1`, `-3` | any number — there is only one number type |
| string | `"hello"` | text |
| boolean | `true`, `false` | a yes/no value |
| `null` | `null` | "deliberately nothing" |
| `undefined` | `undefined` | "nothing has been put here yet" |
| object | `{ name: "Priya" }` | a labelled collection |
| array | `[1, 2, 3]` | an ordered list |

**Two things here are unusual and both cause real bugs.**

**First: there is only one number type.** JavaScript does not distinguish whole
numbers from decimals. Everything is a decimal number internally, which means:

```javascript
0.1 + 0.2      // 0.30000000000000004
```

That is not a bug in the language; it is how nearly all computers store
decimals — some fractions have no exact form in binary, just as one third has
no exact form in decimal. **The practical rule: never use plain numbers for
money.** Store paise or cents as whole numbers, or use a library built for it.
This project uses numbers for scores and timings, where a tiny imprecision
changes nothing, which is the correct place to accept it.

**Second: there are two different kinds of "nothing".**

- `undefined` means *nobody has given this a value*. A variable you declared
  but did not set, or a property that does not exist, is `undefined`.
- `null` means *someone deliberately put "nothing" here*.

```javascript
let a;                     // undefined — never assigned
const user = { name: "P" };
user.age;                  // undefined — no such property
const chosen = null;       // null — a deliberate "no selection"
```

**Why two?** History. `null` was in the language from the start; `undefined`
appeared as what the engine returns when there is nothing. They were never
merged because merging them would change the behaviour of existing pages.

**Why it matters practically:** they are different values, so code that checks
for one may miss the other. That is exactly why the "nullish" operator in D.6
exists — it treats both as "no value", which is almost always what you mean.

## C.3 Comparing values — the most famous trap in the language

JavaScript has two ways to ask "are these equal", and one of them is dangerous.

```javascript
"5" == 5         // true   ← converts types first, then compares
"5" === 5        // false  ← compares type AND value
```

`==` performs **type coercion**: if the two sides are different kinds, it
converts one and then compares. The conversion rules are complicated and produce
famously strange results:

```javascript
0 == ""          // true
0 == "0"         // true
"" == "0"        // false      ← so equality is not even consistent
null == undefined // true
```

**Why this exists:** in 1995 web forms gave everything to you as text, so
comparing the text `"5"` to the number `5` and getting `true` felt helpful. It
was a convenience that turned into a permanent hazard.

**The rule, with no exceptions worth learning as a beginner: always use `===`
and `!==`.** Every serious codebase and every linting tool enforces this. You
will see `===` throughout this project's frontend, including in
[`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts):

```javascript
if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
```

## C.4 Truthiness, and a trap you must be able to spot

In a condition, JavaScript accepts values that are not `true` or `false` and
decides what they mean.

**These are treated as false:** `false`, `0`, `""` (empty text), `null`,
`undefined`, and `NaN` (the result of an impossible calculation, meaning "not a
number"). **Everything else is true**, including `"0"`, `[]` and `{}` — note
that an empty array is *true* in JavaScript, unlike Python.

This enables a very common shorthand:

```javascript
const workspace = workspaceType || "general";     // use "general" if nothing was given
```

`||` (or) returns the left side if it is truthy, otherwise the right side.

**Where this is safe, and where it is a bug.** In the line above it is safe,
because an empty workspace name is meaningless anyway — treating `""` as
"nothing given" is correct.

Now consider:

```javascript
const remaining = queriesRemaining || 10;
```

If the user has **0** queries remaining, `0` is falsy, so this quietly says 10.
**A user who has run out of trial questions is told they have ten.** The
mistake is not obvious, and it is one of the most common real bugs in
JavaScript.

**The fix, added to the language in 2020, is `??` — the "nullish coalescing"
operator.** It falls back only for `null` and `undefined`, never for `0` or
`""`:

```javascript
const remaining = queriesRemaining ?? 10;   // 0 stays 0
```

**The rule to carry:** use `||` when *empty and missing mean the same thing*;
use `??` when *empty is a real value*. This is exactly the lesson from Chapter
06's Python section — where an empty list was used to mean "we failed" and
merged two different states — appearing again in a different language. **Two
distinct states must never share one value.**

Real code from this project uses both correctly:

```javascript
const isMutation = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method?.toUpperCase() || 'GET');
...
onTrialStatus?.(lastTrialStatus);
```

The first uses `||` because a missing method means GET and an empty method
string is meaningless. We will explain the `?.` marks in D.6.

## C.5 Text with values inside

```javascript
const name = "Priya";
const count = 12;
console.log(`${name} asked with ${count} chunks`);
```

Backticks (`` ` ``) create a **template literal**. Anything inside `${ }` is
computed and inserted. They can also span several lines, which ordinary quotes
cannot.

This is exactly the same idea as Python's f-strings from Chapter 06, with
different punctuation.

---

# Part D — Objects and Arrays

## D.1 Objects — the structure everything is built from

**The problem.** A user has a name, an email and a plan. Three separate
variables means passing three things everywhere and forgetting one.

**An object groups labelled values together.**

```javascript
const user = {
  name: "Priya",
  email: "priya@example.com",
  plan: "trial",
};

user.name;              // "Priya"
user["name"];           // same thing
user.age;               // undefined — no error, just "nothing there"
user.plan = "paid";     // change a value
user.city = "Hyderabad";// add a new one
```

**Two ways to reach inside**, and the difference matters:

- `user.name` — dot form, when you know the label while writing the code.
- `user["name"]` — bracket form, when the label is itself in a variable:
  `user[fieldName]`.

**A behaviour that surprises people from other languages:** asking for a
property that does not exist gives `undefined` rather than an error. That is
convenient and it is also how a typo becomes a silent bug —
`user.emial` is `undefined`, not a crash. (This is one of the main problems
TypeScript solves, in Chapter 09.)

## D.2 Arrays — ordered lists

```javascript
const names = ["alice", "bob", "carol"];
names[0];              // "alice"  — counting starts at 0
names.length;          // 3
names.push("dan");     // add to the end
names.includes("bob"); // true
```

**Counting from zero** is universal in programming; the index is a distance
from the start, and the first item is zero away.

## D.3 Array methods — the heart of everyday JavaScript

These are used constantly, and understanding them is most of what "writing
JavaScript" means in practice.

```javascript
const scores = [0.9, 0.4, 0.7, 0.2];

scores.map(s => s * 100);          // [90, 40, 70, 20]   transform each
scores.filter(s => s > 0.5);       // [0.9, 0.7]         keep some
scores.find(s => s > 0.5);         // 0.9                first match, or undefined
scores.some(s => s > 0.8);         // true               is any true?
scores.every(s => s > 0.1);        // true               are all true?
scores.reduce((a, b) => a + b, 0); // 2.2                combine into one value
```

**What is `s => s * 100`?** It is a short way of writing a function — an
**arrow function**, covered properly in E.1. Read it as: *given `s`, produce
`s * 100`*.

**Why these exist instead of loops.** Compare:

```javascript
const percentages = [];
for (let i = 0; i < scores.length; i++) {
  percentages.push(scores[i] * 100);
}
```

against

```javascript
const percentages = scores.map(s => s * 100);
```

The loop spends four lines on mechanics — create, count, index, append — and
one on the idea. The `map` version *is* the idea. And it says something the
loop does not: **`map` always produces exactly one output per input**, so a
reader knows the length is unchanged without checking.

**The one rule that makes these safe:** `map`, `filter` and the rest **return a
new array and do not change the original**. That matters enormously in the
frontend, because Chapter 21 will show that React decides what to redraw by
noticing when a value has been *replaced*, not when it has been modified in
place.

## D.4 Destructuring — taking things out by name

```javascript
const { name, plan } = user;        // two variables from one object
const [first, second] = names;      // two variables from a list
```

**Why it exists.** Without it you write `const name = user.name;` on every
line. With it, one line takes several values and — more importantly — the code
*states which fields it uses*, which is a form of documentation.

You will see this in every React component, and in this project's own code:

```javascript
const { value, done } = await reader.read();
```

One call returns an object with two fields, and both are pulled out at once.

## D.5 Spread — copying and combining

```javascript
const a = [1, 2];
const b = [...a, 3];              // [1, 2, 3] — a new array
const settings = { ...defaults, theme: "dark" };   // copy, then override
```

The three dots mean "spread the contents out here".

**Why this matters more in JavaScript than it sounds.** Objects and arrays are
shared by reference — two names can point at the same one, and changing it
through either name changes it for both. Spread creates a **new** object with
the same contents, which is how you change something without disturbing anyone
else holding the old version.

Real code in this project's request wrapper does exactly that:

```javascript
response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers, credentials: 'include' });
```

*Take everything the caller passed, then add or replace `headers` and
`credentials`.* The caller's object is untouched — which is what makes this
wrapper safe to use everywhere.

## D.6 Optional chaining and nullish coalescing

**The problem.** Reaching into something that might not exist crashes:

```javascript
const reader = res.body.getReader();   // if body is null → TypeError, page breaks
```

**The solution, `?.`** — "if this is null or undefined, stop and give
`undefined` instead of crashing":

```javascript
const reader = res.body?.getReader();
```

It works for calling functions that may not exist, too:

```javascript
onTrialStatus?.(lastTrialStatus);   // call it only if it was provided
```

That line is real, from this project's streaming reader. `onTrialStatus` is an
optional function the caller may or may not supply. Without `?.` you would
write `if (onTrialStatus) { onTrialStatus(...) }` every time.

**And `??`**, from C.4, is its partner: fall back only when the value is `null`
or `undefined`.

```javascript
chat_session_id: chatSessionId ?? null,
```

Also real, from the upload code. If no chat was given, send `null` explicitly —
because the server distinguishes "no chat" from "field missing".

---

# Part E — Functions

## E.1 Three ways to write one, and why

**A function is a named, reusable group of instructions.**

```javascript
// 1. Declaration
function greet(name) {
  return `Hello, ${name}`;
}

// 2. Expression — a function stored in a variable
const greet2 = function (name) {
  return `Hello, ${name}`;
};

// 3. Arrow function — the modern short form
const greet3 = (name) => `Hello, ${name}`;
```

All three do the same thing here. **Why three?** History again: declarations
came first, expressions were needed to pass functions around as values, and
arrows were added in 2015 to make short functions readable and to fix a
long-standing confusion about the word `this` (E.5).

**Arrow function shorthand rules**, because they look cryptic until you know
them:

```javascript
(a, b) => a + b        // one expression: its value is returned automatically
a => a * 2             // one parameter: brackets optional
() => doSomething()    // no parameters: empty brackets required
(a) => {               // braces mean a full body — then you must write `return`
  const x = a * 2;
  return x + 1;
}
```

The trap: adding braces silently changes the meaning. `a => a * 2` returns
`a * 2`; `a => { a * 2 }` returns **nothing**.

## E.2 Functions are values

This is the idea that unlocks the rest of the chapter.

```javascript
const shout = (t) => t.toUpperCase();
const f = shout;              // the function itself, not its result
f("hello");                   // "HELLO"

["a", "b"].map(shout);        // pass a function INTO another function
```

A function can be stored, passed as an argument, and returned from another
function. That is why `map(s => s * 100)` works at all, and why the event
listeners in Part F work.

## E.3 Closures — the concept that seems mysterious and is not

**The problem.** A function sometimes needs to remember something between calls,
without that something being visible to the whole program.

**A closure is a function that remembers the variables that existed where it
was created**, even after that surrounding code has finished.

```javascript
function makeCounter() {
  let count = 0;                 // lives inside makeCounter
  return function () {
    count = count + 1;
    return count;
  };
}

const next = makeCounter();
next();     // 1
next();     // 2
```

`count` is not global — nothing else can see or change it — and yet it survives
between calls, because the returned function holds on to it.

**Why this matters here.** It is how privacy is achieved without classes, and
it is the mechanism behind almost every pattern in the frontend. This project
uses it at module level:

```javascript
let csrfToken = '';
let deviceFingerprint = '';
let _csrfPromise = null;
```

Those three variables live in the file, not in the browser's global space. Every
function in the file can see them; nothing outside the file can. **A module is
a closure over its own top level** — which is exactly why the export list in
Part I matters: it is the only door in.

## E.4 Callbacks — passing a function to be called later

```javascript
setTimeout(() => console.log("3 seconds later"), 3000);
```

You hand `setTimeout` a function and it calls it later. That function is a
**callback**.

**Why this shape is everywhere in the browser.** The browser has no idea when a
user will click, when data will arrive, or when three seconds will pass. It
cannot make your code wait, because waiting would freeze the screen. So instead
you say: *here is what to do when it happens.*

This project's streaming reader takes six callbacks for exactly that reason:

```javascript
export const askQuestionStream = async (
  query,
  topK,
  onStatus,
  onMetadata,
  onToken,
  onError,
  onDone,
  ...
```

The caller cannot know when a token will arrive, so it supplies *what to do*
when one does. `onToken` is called dozens of times as the answer streams in;
`onDone` once at the end.

**A senior note on this design.** Six positional callbacks is a lot, and it is
easy to pass them in the wrong order — a bug the language will not catch. An
object of named handlers (`{ onToken, onDone, onError }`) would be safer and
self-documenting. This is a real, mild weakness, and it appears in the critique
in Part P.

## E.5 `this` — the one genuinely confusing thing

In JavaScript, `this` inside a function does not mean what it means in most
other languages. Its value depends on **how the function was called**, not
where it was written.

```javascript
const obj = {
  name: "Priya",
  greet: function () { return this.name; },
};
obj.greet();                    // "Priya" — called ON obj, so this === obj

const loose = obj.greet;
loose();                        // undefined — no object, so `this` is not obj
```

That second case has broken more beginner code than any other feature.

**Arrow functions fixed it.** An arrow function does not get its own `this`; it
uses whatever `this` meant where it was written. That is one of the main
reasons arrows are now the default for callbacks.

**And the practical advice for this repository:** the frontend is built from
plain functions and React components, so `this` barely appears. You need to
recognise it in older code and otherwise avoid it.

---

# Part F — The Browser Runtime

The language itself has no idea what a web page is. Everything in this part
comes from the *browser*, not from JavaScript.

## F.1 The DOM

When the browser reads the text of a page, it builds a tree of objects in
memory representing it — a heading contains text, a section contains
paragraphs. This tree is the **DOM** (Document Object Model), and it is what
your program manipulates.

```javascript
const el = document.getElementById("title");
el.textContent = "New heading";
el.classList.add("highlighted");
```

Changing the DOM changes what is on screen. That is the whole mechanism.

**Real code from this project**, in
[`frontend/src/hooks/useTheme.ts`](../frontend/src/hooks/useTheme.ts):

```javascript
const root = document.documentElement;
root.setAttribute("data-theme", isDark ? "dark" : "light");
root.classList.toggle("dark", isDark);
```

`document.documentElement` is the outermost element of the page. Setting an
attribute and toggling a class on it changes how *everything inside* is
styled — because the styling rules are written to respond to that attribute.
**One line changes the entire appearance of the application**, which is a very
deliberate design (Chapter 23 covers why).

Also note `isDark ? "dark" : "light"` — the **ternary operator**: a compact
`if`/`else` that produces a value. `condition ? valueIfTrue : valueIfFalse`.

**A modern warning.** You will rarely write direct DOM code in this project,
because React (Chapter 21) does it for you. You still need to understand it,
because when something goes wrong you are looking at the DOM in the browser's
inspector.

## F.2 Events and the event loop

**The problem.** A program must react to things that happen at unpredictable
times — clicks, key presses, data arriving — while never freezing the screen.

**The solution: one loop, and everything is a message.**

The browser runs your JavaScript on **one single thread**. There is exactly one
of you. When you click, the browser puts a "click happened" message in a queue.
When the current piece of code finishes, the loop takes the next message and
runs the function registered for it.

**Two consequences follow, and they are the whole model:**

1. **Your code is never interrupted mid-function.** Whatever you are doing runs
   to the end before anything else happens. That is why you never need locks in
   browser JavaScript.
2. **If your code takes a long time, the page freezes.** No clicks respond, no
   animation moves, nothing scrolls — because the one thread is busy. A loop
   counting to a billion makes the browser appear crashed.

That second point may feel familiar if you have read Chapter 07: it is exactly
the same cooperative model as Python's event loop. **The difference is that
Python chose it and JavaScript was born with it**, because a browser cannot
afford a frozen screen.

## F.3 Listening for events, and cleaning up

```javascript
function handler() {
  console.log("clicked");
}
button.addEventListener("click", handler);
button.removeEventListener("click", handler);
```

**Why removal matters, and this is a real category of bug.** A listener holds a
reference to your function, and that function may hold references to other
things (E.3, closures). If the element or component goes away and the listener
is not removed, that memory can never be reclaimed. Repeat that a hundred times
as a user navigates around, and the page becomes slow — a **memory leak**.

Worse, the old listener may still *run*, acting on data that no longer belongs
to anything on screen.

**Real code that does this correctly**, in
[`frontend/src/hooks/useSessionExpiry.ts`](../frontend/src/hooks/useSessionExpiry.ts):

```javascript
    window.addEventListener("session:expired", handler)
    return () => window.removeEventListener("session:expired", handler)
```

The second line returns a function that undoes the first. React calls that
returned function when the component disappears (Chapter 21). **Notice that the
same `handler` variable is used in both lines** — removal only works if you
pass the exact same function object, which is why you cannot write the handler
inline in both places.

## F.4 Custom events — how far-apart parts of an app talk

**The problem.** The code that makes network requests discovers that the user's
session has expired. The code that shows a "session expired" message is
somewhere else entirely — a different file, a different part of the screen.
Wiring them together directly would mean one importing the other and knowing
about its internals.

**The solution: shout into the room, and let whoever cares listen.**

```javascript
window.dispatchEvent(new CustomEvent('session:expired'));
```

That line is real, in `api.ts`, at the point a token refresh fails. And
somewhere else entirely, in `useSessionExpiry.ts`:

```javascript
    window.addEventListener("session:expired", handler)
```

**Neither file imports the other.** They agree only on a name — the string
`"session:expired"`. The network layer does not know a modal exists; the modal
does not know how requests work.

**Recognise the pattern?** It is the same shape as the SSE event names between
the server and the browser (Chapter 01), and the same shape as jobs on a queue
(Chapter 02): **a shared name is the entire contract, and nothing else is
coupled.** It also carries the same risk — if one side renames the string, the
feature silently stops working and nothing errors. That is precisely why this
project treats such names as invariants that must be kept in step.

**And here is a lovely detail in the real handler** that shows careful
thinking:

```javascript
      const pathname = window.location.pathname
      if (
        pathname === "/login" ||
        pathname === "/register" ||
        pathname === "/forgot-password" ||
        pathname === "/"
      ) {
        return
      }
      setSessionExpired(true)
```

With the comment above it explaining why:

> *"Never show the session-expired overlay on auth/public pages. These pages
> have no session to expire; unauthenticated API calls (e.g. billing status
> fetched by LayoutWrapperInner) return 401 which would otherwise trigger a
> false 'session expired' modal."*

**A broadcast reaches listeners that were not the intended audience.** That is
the cost of loose coupling, and the fix is for the listener to know when the
message does not apply to it.

## F.5 Storing things in the browser

Three places, with three different purposes. Confusing them is a common
mistake.

| Where | Lives for | Sent to the server? | Readable by JavaScript? |
|---|---|---|---|
| `localStorage` | forever, until cleared | no | yes |
| `sessionStorage` | until the tab closes | no | yes |
| cookie | until it expires | **yes, automatically** | only if not `httpOnly` |

**Real uses of each in this project:**

```javascript
    const saved = (localStorage.getItem("theme") as Theme) || "system";
    ...
    localStorage.setItem("theme", t);
```

Theme preference in `localStorage` — it must survive closing the browser, and
the server does not need to know.

```javascript
      sessionStorage.setItem("returnTo", window.location.pathname);
      window.location.href = "/login?expired=true";
```

Where the user was before being sent to log in, in `sessionStorage` — needed
only for this tab, only for the next few seconds.

And the login token is in a **cookie**, which the browser attaches to every
request to this site automatically. Chapter 01 explained the consequence: that
automatic attachment is convenient and is exactly what makes the CSRF attack
possible, which is why a separate token is added by hand.

**The security rule that follows.** Anything in `localStorage` or
`sessionStorage` can be read by any JavaScript running on the page. If an
attacker manages to inject a script, they can take it. That is why the login
token is stored in an `httpOnly` cookie — a cookie that JavaScript is not
allowed to read at all. **Storage choice is a security decision.**

---

# Part G — Asynchronous JavaScript

## G.1 Why the language is built around waiting

Recall F.2: one thread, and a frozen thread means a frozen page. Now consider
that a network request takes 50 to 2000 milliseconds.

**If JavaScript waited for a network reply, the page would be unusable for two
seconds** — no scrolling, no typing, no cancel button. That is not acceptable,
so the language has never had a "wait for this" instruction for I/O. It has
always been asynchronous.

## G.2 The three generations

**Generation 1 — callbacks (1995–2012).** Hand over a function to be called
later:

```javascript
fetchData(url, function (data) {
  processData(data, function (result) {
    save(result, function () {
      console.log("done");
    });
  });
});
```

This works and becomes unreadable as soon as steps depend on each other —
the shape known as **callback hell**. Worse, errors have no natural home: a
`try` block around the outer call catches nothing from the inner ones, because
by the time they run the outer call has long finished.

**Generation 2 — promises (2015).** A **promise** is an object representing a
result that is not ready yet.

```javascript
fetchData(url)
  .then(data => processData(data))
  .then(result => save(result))
  .then(() => console.log("done"))
  .catch(err => console.error("something failed", err));
```

Flat instead of nested, and one `.catch` at the end handles a failure at any
step. A promise is always in one of three states: **pending** (still working),
**fulfilled** (has a value), or **rejected** (has an error). Once it leaves
pending it never changes again.

**Generation 3 — `async` / `await` (2017).** Promises with syntax that reads
like ordinary sequential code:

```javascript
async function run() {
  try {
    const data = await fetchData(url);
    const result = await processData(data);
    await save(result);
    console.log("done");
  } catch (err) {
    console.error("something failed", err);
  }
}
```

**This is the same idea as Chapter 07's Python async, with different keywords.**
`await` pauses this function and hands control back to the browser's event loop,
which continues drawing the page and handling clicks. When the promise settles,
the function resumes on the line after the `await`, with all its variables
intact.

**Three things `await` does not do**, and they are worth stating explicitly
because beginners assume all three:

- It does not create a thread. There is still exactly one.
- It does not freeze the page. That is the entire point.
- It does not make anything faster. It makes waiting free.

**And one rule:** `await` may only appear inside a function marked `async`.
Calling an `async` function gives you a promise immediately — the body runs
until its first `await` and then returns control to the caller.

## G.3 The most common beginner mistake in modern JavaScript

Forgetting `await`:

```javascript
const res = fetch(url);        // MISSING await
console.log(res.status);       // undefined — res is a promise, not a response
```

No error is thrown. You get a promise object where you expected data, and the
symptom appears somewhere else entirely. **If a value is mysteriously
`undefined` or prints as `Promise { <pending> }`, look for a missing `await`
first.**

## G.4 Doing several things at once

`await` on its own is sequential — each line waits for the one before:

```javascript
const a = await fetchUser();      // 300ms
const b = await fetchDocuments(); // 300ms
// total: 600ms
```

If they do not depend on each other, start both and then wait:

```javascript
const [a, b] = await Promise.all([fetchUser(), fetchDocuments()]);
// total: ~300ms
```

`Promise.all` waits for every promise and returns their results in the order
given. If any one rejects, the whole thing rejects immediately.

**The judgement call**, and it is the same one as Chapter 07: use `Promise.all`
for genuinely independent work; do not use it to fire a thousand requests at
once, because you will overwhelm the server and receive errors instead of
speed.

## G.5 `fetch` — how the browser makes a request

```javascript
const res = await fetch("https://example.com/api/things", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "Priya" }),
  credentials: "include",
});

if (!res.ok) {
  throw new Error("Request failed");
}
const data = await res.json();
```

Every part:

- `fetch(url, options)` returns a promise for a **response**.
- `method` — the kind of request: `GET` to read, `POST` to send.
- `headers` — extra information about the request. `Content-Type` tells the
  server how to interpret the body.
- `body: JSON.stringify(...)` — turns a JavaScript object into text, because a
  network carries text and bytes, not live objects.
- `credentials: "include"` — **send cookies**. Without this, a request to a
  different origin carries no cookie and the server sees an anonymous stranger.
- `res.ok` — true for status codes 200–299.
- `await res.json()` — reading the *body* is itself asynchronous, because the
  body may still be arriving. This is the second `await`, and forgetting it is
  a classic mistake.

**A trap worth knowing:** `fetch` does **not** reject for a 404 or a 500. It
rejects only when the request could not be made at all — no network, wrong
address. A server saying "not found" is a *successful* request with an
unsuccessful status. That is why `if (!res.ok)` must be written by hand, every
time.

## G.6 The real wrapper, line by line

Now read production code. This is
[`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts), the function every
network call in the application goes through. The `: string` and `: RequestInit`
parts are TypeScript, which Chapter 09 explains — ignore them and the rest is
plain JavaScript.

```javascript
export const apiFetch = async (endpoint, options = {}, _retried = false) => {
  const isMutation = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method?.toUpperCase() || 'GET');

  if (isMutation && !csrfToken && !endpoint.startsWith('/auth/')) {
    await _fetchCsrf();
  }
  const headers = new Headers(options.headers || {});
  if (isMutation && csrfToken) headers.set('X-CSRF-Token', csrfToken);
  if (deviceFingerprint) headers.set('X-Device-ID', deviceFingerprint);

  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers, credentials: 'include' });
  } catch (error) {
    if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
      throw new Error('Network error: The server is unreachable. Please check your connection.');
    }
    throw error;
  }

  if (response.status === 401 && !_retried) {
    if (!_isRefreshing) {
      _isRefreshing = true;
      _refreshPromise = doRefreshToken().finally(() => { _isRefreshing = false; _refreshPromise = null; });
    }
    const refreshed = await _refreshPromise;
    if (refreshed) return apiFetch(endpoint, options, true);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('session:expired'));
    }
    throw new Error('Session expired');
  }

  return response;
};
```

Working through it:

**1.** `options = {}` is a **default parameter** — if the caller passes nothing,
use an empty object, so `options.method` does not crash.

**2.** `options.method?.toUpperCase() || 'GET'` — optional chaining in case
`method` was not given, then `||` to default to GET. Then `.includes(...)`
checks membership in the list. One line answering "does this request change
anything?"

**3.** `!csrfToken` uses truthiness: an empty string is falsy, so this means
"we do not have a token yet". `await _fetchCsrf()` fetches one and **waits**,
because sending the request without it would be rejected by the server.

**4.** `new Headers(options.headers || {})` builds a headers object, copying
anything the caller supplied so we do not modify their object.

**5.** `{ ...options, headers, credentials: 'include' }` — spread the caller's
options, then override two fields. `headers` alone is shorthand for
`headers: headers`.

**6.** The `try`/`catch` translates the browser's unhelpful `"Failed to fetch"`
into a sentence a human can act on — and re-throws anything else unchanged,
which matters: **catching everything and reporting one message would hide
unrelated errors.** This is the same discipline as Chapter 06's rule about
narrow exception handling, expressed in a different language.

**7. The refresh block is the most interesting part.** If the server says 401
(not authenticated), try once to renew the session, then retry the original
request.

The subtle piece is `_isRefreshing` and `_refreshPromise`. Suppose five
requests fail with 401 at the same moment. Without this guard, all five would
try to refresh, producing five refresh calls — wasteful, and possibly harmful
if the server allows only one. Instead, **the first one starts the refresh and
stores the promise; the other four await the same promise.** One refresh, five
waiters.

That pattern is called **in-flight de-duplication**, it is one of the most
useful things in this file, and it is worth memorising as a shape:

```javascript
if (!inFlight) {
  inFlight = doTheWork().finally(() => { inFlight = null; });
}
const result = await inFlight;
```

`.finally(...)` runs whether the work succeeded or failed, which is what
guarantees the flag is cleared — the exact reasoning behind Python's `finally`
in Chapter 06.

**8.** `return apiFetch(endpoint, options, true)` — the function calls itself,
with `_retried = true` so it can never loop forever. That is **recursion** used
carefully: there is a condition that makes it stop.

**9.** If refresh failed, announce it with a custom event (F.4) and throw.

## G.7 Reading a stream

The final piece of real async code, and the one that makes the answer appear
word by word. Chapter 01 showed it; now every part is explainable.

```javascript
    const reader = res.body?.getReader();
    if (!reader) throw new Error("No readable stream");

    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        ...
      }
    }
```

- **`res.body?.getReader()`** — a response body can be read piece by piece
  instead of all at once. `?.` guards against a missing body.
- **`new TextDecoder("utf-8")`** — the network delivers *bytes*; this turns
  them into text using the UTF-8 rule. Getting the encoding wrong here would
  mangle any non-English character.
- **`await reader.read()`** — waits for the next piece and returns an object
  with `value` (the bytes) and `done` (are we finished). Destructured on one
  line.
- **`{ stream: true }`** — tells the decoder that more bytes are coming, so if
  the chunk ends halfway through a multi-byte character it should wait rather
  than produce a broken symbol.
- **`buffer.split('\n\n')`** — messages are separated by a blank line.
- **`buffer = blocks.pop() || ""`** — **this is the clever line.** `pop()`
  removes and returns the *last* piece, which may be incomplete because the
  network can cut a message anywhere. Putting it back in the buffer means the
  next chunk completes it. Without this, roughly every so often you would lose
  half a word — a bug that appears random and is not.

---

# Part H — Errors

## H.1 Throwing and catching

```javascript
function divide(a, b) {
  if (b === 0) {
    throw new Error("Cannot divide by zero");
  }
  return a / b;
}

try {
  divide(1, 0);
} catch (err) {
  console.error(err.message);
} finally {
  console.log("this always runs");
}
```

`throw` stops the function immediately and travels up through callers until
something catches it. `finally` runs regardless — success, failure, or an early
return — which is what makes it right for cleanup.

## H.2 Errors and promises

A rejected promise is the async version of a thrown error, and `try`/`catch`
around an `await` catches it:

```javascript
try {
  const data = await fetchData();
} catch (err) {
  // catches both thrown errors and rejected promises
}
```

**But only if you `await` it.** This is a common and painful bug:

```javascript
try {
  fetchData();          // no await — the promise floats away
} catch (err) {
  // never runs; the rejection happens after this block has finished
}
```

The rejection becomes an **unhandled promise rejection**, reported in the
console at some later moment with no connection to your code. Exactly the same
family of problem as Chapter 07's fire-and-forget tasks.

## H.3 A deliberate small catch, from this project

```javascript
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Stream failed");
```

Reading it: try to read the error body as JSON; if that fails — perhaps the
server returned HTML or nothing — use an empty object instead. Then use the
server's `detail` message if there is one, otherwise a generic sentence.

**Is this the silent-failure anti-pattern from earlier chapters?** No, and the
distinction is worth being precise about. The failure being swallowed is *the
failure to parse an error body*, at a point where an error is already being
reported. Nothing is being hidden: an error is thrown either way. Swallowing
here loses only detail about a failure that is already surfacing.

**The general test:** ask *what information is lost, and would anyone have
acted on it?* If the answer is "nothing anyone could act on", a small catch is
fine. If the answer is "the reason the feature does not work", it is the
anti-pattern.

---

# Part I — Modules

## I.1 The problem, and how bad it used to be

Early JavaScript had no way to split code across files with any privacy. Every
`<script>` tag shared one global space. Two libraries that both used a variable
called `$` would silently destroy each other, and the order of script tags in
the page determined whether anything worked.

## I.2 The modern answer

```javascript
// analytics.js
export const track = (event, properties) => { ... };
export const Analytics = { ... };

// somewhere else
import { track, Analytics } from './analytics';
```

- **`export`** makes something available to other files. Everything not
  exported is private to the file (E.3 — a module is a closure over itself).
- **`import { name }`** takes specific things by name.
- **`import name from '...'`** takes a file's single "default" export, which is
  what `import posthog from 'posthog-js'` does at the top of this project's
  analytics file.

**Two kinds of import path**, and the difference confuses beginners:

- `'./analytics'` — starts with a dot, so it means *a file in this project*,
  relative to the current file.
- `'posthog-js'` — no dot, so it means *a package installed from the internet*,
  found in `node_modules/`.

## I.3 A real module worth studying

[`frontend/src/lib/analytics.ts`](../frontend/src/lib/analytics.ts) is small,
complete, and contains a genuinely good design decision.

```javascript
import posthog from 'posthog-js'

export const initAnalytics = () => {
  if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, { ... })
  }
}

export const track = (event, properties) => {
  posthog.capture(event, properties)
}

// Typed event helpers — NEVER include query text, document names, answer content, email, or user_id
export const Analytics = {
  querySubmitted: (workspace, query_length_chars, has_documents) =>
    track('query_submitted', { workspace, query_length_chars, has_documents }),

  trialQueryUsed: (queries_used, queries_remaining) =>
    track('trial_query_used', { queries_used, queries_remaining }),
  ...
}
```

Four things to notice:

**1. `typeof window !== 'undefined'`.** This code can run in two places: in a
browser, and on the server during page rendering (Chapter 22). On the server
there is no `window` object, so touching it would crash. This check asks "am I
in a browser?" **It is the standard way to write code that must work in both
places**, and you will see it repeatedly in this project.

**2. `process.env.NEXT_PUBLIC_POSTHOG_KEY`.** Configuration from outside the
code, exactly as Chapter 05 described for the backend. The `NEXT_PUBLIC_`
prefix is a rule of the frontend framework meaning "this value is safe to
send to the browser". **Anything in the browser is public** — a user can read
it — so a secret must never be given that prefix.

**3. `Analytics` is an object of functions.** Rather than letting every part of
the app call `track('query_submitted', ...)` with hand-typed strings and
hand-chosen fields, there is one named function per event. A typo becomes
`Analytics.querySubmited is not a function` — an immediate, obvious error —
instead of a wrongly-named event silently polluting the data.

**This is exactly the choke-point idea from earlier chapters**, applied to
analytics: one place decides the shape of each event.

**4. And the comment above it is a privacy control:**

> *"NEVER include query text, document names, answer content, email, or
> user_id"*

Look at what the functions actually send: `query_length_chars` instead of the
query, `file_size_mb_bucket` instead of a filename, `trust_level` instead of a
document. **The design makes the private version hard to send by accident**,
because the only convenient path is through a function that already omits it.
A rule enforced by structure rather than by memory — the same principle as
Chapter 03's choke point, in a domain that has nothing to do with security
code.

---

# Part J — Classes and Prototypes

## J.1 What is really underneath

JavaScript's inheritance works differently from most languages. Every object
has a hidden link to another object, its **prototype**. When you ask for a
property the object does not have, the language follows that link and asks the
prototype, then the prototype's prototype, until it finds it or runs out.

That is why `"hello".toUpperCase()` works: the string does not have that method
itself; the prototype it links to does.

## J.2 Class syntax

```javascript
class Rectangle {
  constructor(width, height) {
    this.width = width;
    this.height = height;
  }

  area() {
    return this.width * this.height;
  }
}

const r = new Rectangle(3, 4);
r.area();          // 12
```

`class` was added in 2015. It is friendlier syntax over the prototype system,
not a new mechanism. `new` creates a fresh object and runs the constructor with
`this` pointing at it.

## J.3 Why this project barely uses classes

Search the frontend and you will find very few. The reason is the framework:
React builds interfaces from **functions** that receive data and return a
description of what to show. State is held by hooks (Chapter 21), not by object
fields.

**Class components used to be the only option and are now legacy.** You need to
recognise classes when reading older tutorials and libraries; you will write
almost none here.

---

# Part K — Common Beginner Mistakes

1. **Using `==` instead of `===`.** Always `===`.
2. **Using `||` where `??` is needed.** `count || 10` turns a real zero into
   ten.
3. **Forgetting `await`.** You get a promise where you expected a value, and
   the symptom appears far away.
4. **Forgetting the second `await`** on `res.json()`.
5. **Assuming `fetch` rejects on a 404.** It does not. Check `res.ok`.
6. **Modifying an object instead of replacing it.** In React this means the
   screen does not update, and there is no error to tell you why (Chapter 21).
7. **Adding a listener and never removing it.** A leak, and possibly a stale
   handler acting on data that no longer exists.
8. **Believing an empty array is falsy.** In JavaScript `[]` is *truthy* —
   unlike Python. `if (list)` is true even when the list is empty; you want
   `if (list.length)`.
9. **`this` in a plain callback.** Use an arrow function.
10. **Putting a secret in frontend code.** Everything shipped to the browser is
    readable by the user. There is no such thing as a hidden value in a web
    page.

---

# Part L — How Real Companies Use This

- **Every product with a web interface** ships JavaScript, because there is no
  alternative in a browser.
- **Most large frontends are TypeScript**, for the reasons Chapter 09 explains.
- **The array methods and async/await in this chapter are the daily vocabulary
  of a frontend engineer**, far more than classes or prototypes.
- **The patterns you saw in `apiFetch`** — a single wrapper for every request,
  automatic authentication headers, in-flight de-duplication, one retry on 401,
  translated error messages — are what a production API client looks like in
  every company. Learn that function and you have learned a genre.
- **Analytics that deliberately omits personal data** is a legal requirement in
  many places, not a nicety. The pattern in Part I — a named function per event
  that cannot easily send the private field — is how teams keep that promise at
  scale.

---

# Part M — Exercises

Do these in the browser console (F12 → Console) unless a file is mentioned.

### Level 0 — First contact

**M1.** Type `2 + 3`. Then `"2" + 3`. Then `2 + "3"`. Explain what happened in
the last two, in one sentence.

**M2.** Store your name in a `const` and print a greeting using a template
literal.

**M3.** Try to reassign that `const`. What error appears? Now do the same with
`let`.

### Level 1 — Values and comparisons

**M4.** Predict, then check: `0 == ""`, `0 === ""`, `null == undefined`,
`null === undefined`, `[] == false`. Which of these would you ever rely on?

**M5.** Given `let remaining = 0;`, compare `remaining || 10` with
`remaining ?? 10`. Explain which one you would use to show a user how many
trial questions they have left, and why the other is a bug.

**M6.** Make an object with three fields. Read one that exists and one that does
not. What do you get for the missing one, and why is that dangerous?

### Level 2 — Collections and functions

**M7.** Given `const scores = [0.9, 0.4, 0.7, 0.2];`, use `filter` and then
`map` to produce the scores above 0.5, expressed as percentages.

**M8.** Write `makeCounter` from E.3 yourself, without looking. Create two
counters and confirm they count independently. Explain in one sentence why they
do.

**M9.** Write a function that takes an object of options and returns a new
object with `theme: "dark"` added, **without changing the original**. Prove the
original is unchanged.

### Level 3 — Asynchronous

**M10.** Write an async function that waits one second (use
`new Promise(resolve => setTimeout(resolve, 1000))`) and then prints "done".
Call it twice with `await` and time it. Then use `Promise.all` and time it
again.

**M11.** Call `fetch("https://example.com/definitely-not-a-real-page")` and
inspect the result. Did the promise reject? What is `res.ok` and `res.status`?
State the rule this demonstrates.

**M12.** Write the in-flight de-duplication pattern from G.6 yourself: a
function `getToken()` that, if called five times before the first finishes,
performs the underlying work only once. Prove it with a counter.

### Level 4 — Repository-shaped

**M13.** Write a small SSE parser. Given a string of the form
`"event: token\ndata: {\"token\":\"Hi\"}\n\nevent: done\ndata: {}\n\n"`, split
it into blocks, extract the event name and data from each, and print them.
Then explain what your code must do when a block arrives cut in half.

**M14.** Look at this and say what is wrong, what the user would experience, and
how you would fix it:

```javascript
async function loadDocuments() {
  const res = fetch("/api/v1/documents");
  const data = await res.json();
  return data;
}
```

**M15.** Write a `useTheme`-style function (plain JavaScript, no React) that
reads a saved theme from `localStorage`, applies it by setting an attribute on
`document.documentElement`, listens for the system dark-mode preference
changing, and **returns a function that removes the listener**. Explain why
returning that function matters.

---

# Part N — Answer Key

**N1.** `5`, then `"23"`, then `"23"`. When one side of `+` is text, JavaScript
converts the other to text and joins them. This is type coercion, and it is why
`+` is the one operator you must be careful with when types are uncertain.

**N2.**
```javascript
const name = "Priya";
console.log(`Hello, ${name}`);
```

**N3.** `TypeError: Assignment to constant variable.` With `let` it works
silently. Use `const` by default: it tells every future reader that the name
never changes meaning, which removes a question they would otherwise have to
answer by searching.

**N4.** `true`, `false`, `true`, `false`, `true`. You should rely on none of
them. Every "true" in that list comes from coercion rules that are hard to
remember and easy to misapply, which is why `===` is the rule. (`[] == false`
being true is the clearest demonstration that the coercion rules are not
intuitive.)

**N5.** `remaining || 10` gives **10**, because `0` is falsy. `remaining ?? 10`
gives **0**, because `??` only falls back for `null` and `undefined`.

For trial questions you must use `??`. With `||`, a user who has exhausted
their trial is told they have ten questions left — a wrong number shown
confidently, which is worse than an error. **The general rule: `||` when empty
and missing mean the same thing, `??` when empty is a real value.**

**N6.** The missing field gives `undefined`, with no error. Dangerous because a
typed property name — `user.emial` — behaves exactly like a legitimately absent
one, so a typo becomes a silent `undefined` that flows onward and fails
somewhere unrelated. This is one of the main problems TypeScript solves.

**N7.**
```javascript
const good = scores.filter(s => s > 0.5).map(s => s * 100);   // [90, 70]
```
Both return new arrays; `scores` is untouched. Order matters: filtering first
means `map` runs on fewer items.

**N8.**
```javascript
function makeCounter() {
  let count = 0;
  return () => ++count;
}
const a = makeCounter();
const b = makeCounter();
a(); a();      // 2
b();           // 1
```
They are independent because each call to `makeCounter` creates a **new**
`count` variable, and the returned function closes over its own one. A closure
captures a specific set of variables, not a name.

**N9.**
```javascript
function withDarkTheme(options) {
  return { ...options, theme: "dark" };
}
const original = { theme: "light", fontSize: 14 };
const updated = withDarkTheme(original);
original.theme;     // "light" — unchanged
updated.theme;      // "dark"
```
Spread copies the contents into a new object. This matters far beyond tidiness:
React decides what to redraw by checking whether a value was *replaced*, so
modifying in place produces a screen that does not update, with no error.

**N10.** Sequential is about 2 seconds; `Promise.all` is about 1. `await` means
"pause me until this finishes", so two in a row add up. `Promise.all` starts
both before waiting, so the waiting overlaps. Nothing ran in parallel — there is
still one thread; only the *waiting* overlapped.

**N11.** The promise **fulfils**. `res.ok` is `false` and `res.status` is `404`.
The rule: `fetch` rejects only when the request could not be made at all —
no network, bad address. A server replying "not found" is a successful request
with an unsuccessful status, so `if (!res.ok)` must be written by hand.

**N12.**
```javascript
let inFlight = null;
let calls = 0;

function getToken() {
  if (!inFlight) {
    calls++;
    inFlight = new Promise(resolve => setTimeout(() => resolve("token"), 500))
      .finally(() => { inFlight = null; });
  }
  return inFlight;
}

Promise.all([getToken(), getToken(), getToken(), getToken(), getToken()])
  .then(() => console.log("underlying work ran", calls, "time(s)"));   // 1
```
The first call starts the work and stores the promise; the rest find it already
present and await the same one. `.finally` clears the flag whether the work
succeeded or failed — without it, one failure would leave the flag set forever
and every future call would await a promise that has already settled.

**N13.**
```javascript
const raw = "event: token\ndata: {\"token\":\"Hi\"}\n\nevent: done\ndata: {}\n\n";

for (const block of raw.split("\n\n")) {
  if (!block.trim()) continue;
  let event = "message";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7).trim();
    else if (line.startsWith("data: ")) data = line.slice(6).trim();
  }
  console.log(event, data);
}
```
When a block arrives cut in half, the last piece produced by `split` is
incomplete. It must be **kept in a buffer and joined to the next chunk**, not
parsed — which is precisely what `buffer = blocks.pop() || ""` does in the real
code. Parsing it immediately produces silent, intermittent data loss.

**N14.** `fetch` is not awaited, so `res` is a promise, not a response. Calling
`.json()` on a promise throws `res.json is not a function`.

The user sees a page that fails to load its document list, with a console error
that points at `.json()` rather than at the missing `await` — the symptom is one
line away from the cause. The fix is `const res = await fetch(...)`, plus a
`res.ok` check before parsing, because a 401 or 500 would otherwise be parsed as
though it were a document list.

**N15.**
```javascript
function setupTheme() {
  const saved = localStorage.getItem("theme") || "system";
  const mq = window.matchMedia("(prefers-color-scheme: dark)");

  const apply = () => {
    const isDark = saved === "dark" || (saved === "system" && mq.matches);
    document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
  };

  apply();
  mq.addEventListener("change", apply);
  return () => mq.removeEventListener("change", apply);
}

const cleanup = setupTheme();
// later: cleanup();
```
Returning the cleanup function matters because the listener holds a reference to
`apply`, which closes over `saved` and `mq`. If it is never removed, that memory
cannot be reclaimed and the handler keeps running after the thing it served is
gone. Returning the remover puts the cleanup in the hands of whoever controls
the lifetime — which is exactly the shape React expects, and exactly what
`useTheme.ts` and `useSessionExpiry.ts` do.

---

# Part O — Senior Critique: The JavaScript in This Repository

### Strengths

1. **One wrapper for every request.** `apiFetch` centralises CSRF headers,
   cookies, error translation and the 401 refresh. No component has to remember
   any of it — a choke point in the same sense as the backend's tenant scope.
2. **In-flight de-duplication done properly**, with `.finally` clearing the
   flag on both success and failure. Many production codebases get this wrong
   and leave a permanently stuck flag after one error.
3. **Custom events decouple the network layer from the interface**, and the
   listener is defensive about receiving broadcasts that do not concern it.
4. **Listeners are always cleaned up** in the hooks, using the same function
   reference for add and remove.
5. **Analytics is designed so that sending private data is inconvenient** — a
   named helper per event, each already omitting the sensitive field.
6. **`typeof window !== 'undefined'` guards** are used consistently for code
   that may run outside a browser.

### Weaknesses

1. **`askQuestionStream` takes fourteen positional parameters**, six of which
   are callbacks. Nothing prevents passing them in the wrong order, and adding
   one means touching every call site. An options object
   (`{ query, topK, onToken, onDone }`) would be self-documenting and
   order-independent.
2. **Module-level mutable state** (`csrfToken`, `deviceFingerprint`,
   `_isRefreshing`, `_refreshPromise`) is effectively global to the file. It
   works and it is the simplest thing that does — but it is untestable in
   isolation and would behave oddly if the module were ever loaded twice.
3. **The `error.message === 'Failed to fetch'` check is brittle.** That string
   is browser-specific and not standardised; a different browser or a future
   version can change it, and the friendly message would silently stop
   appearing.
4. **Retry logic is limited to a single 401 retry.** There is no backoff for
   transient network failures or for a 429 rate-limit response, so a brief blip
   surfaces as a hard error to the user.
5. **The SSE parser silently ignores unknown event names.** If the server adds
   an event the client does not know, nothing is logged. Given that these names
   are an invariant the project explicitly protects, a single
   `console.warn` on an unrecognised event would turn a silent contract
   violation into a visible one.

### The one improvement I would make first

**Convert `askQuestionStream` to an options object.** It is mechanical, it
removes a whole class of "wrong argument in position nine" bug that the language
cannot catch, and it makes every future addition a non-breaking change. Second
would be the `console.warn` on unknown SSE events — three lines that convert a
silent contract break into a visible one.

---

# Part P — Interview Questions With Model Answers

**P1. "What is the difference between `==` and `===`?"**

> `==` converts the two sides to a common type before comparing; `===` compares
> type and value with no conversion. The conversion rules are surprising — `0`
> equals `""`, `0` equals `"0"`, but `""` does not equal `"0"` — so equality
> under `==` is not even transitive.
>
> I use `===` everywhere. The only place `==` is sometimes defended is
> `x == null` as a shorthand for "null or undefined", and I would rather write
> that out explicitly or use `??`.

**P2. "Explain closures and give a real use."**

> A closure is a function that keeps access to the variables that existed where
> it was defined, even after that surrounding code has finished. It is how you
> get private state without classes.
>
> In our API client the CSRF token and an in-flight refresh promise are stored
> at module level. Every function in that file can read them; nothing outside
> the file can, because they are not exported. That privacy is what makes it
> safe to have a single shared token — no other module can overwrite it.

**P3. "What happens when you `await` something?"**

> The function pauses at that point and control returns to the browser's event
> loop, which keeps rendering the page and handling clicks. When the promise
> settles, the function resumes on the next line with all of its variables
> intact.
>
> It does not create a thread — there is still exactly one — and it does not
> make anything faster. It makes waiting free. Two `await`s in a row are
> sequential; if the operations are independent I use `Promise.all` so the
> waiting overlaps.

**P4. "Why does `fetch` not throw on a 404?"**

> Because a 404 is a successful HTTP exchange: the request reached the server
> and the server answered. `fetch` rejects only when no answer could be
> obtained at all — no network, bad address, blocked by the browser.
>
> That is why every real API client checks `res.ok` by hand. Ours does, and it
> also translates the browser's `"Failed to fetch"` message into something a
> user can act on, while re-throwing anything else unchanged so unrelated
> errors are not disguised.

**P5. "How do two unrelated parts of a frontend communicate?"**

> Several ways, and the choice is about coupling. Passing data down as
> parameters is the most explicit and the right default. Shared state through a
> store is right when many components need the same value.
>
> For a rare, cross-cutting signal we use a browser custom event. Our network
> layer dispatches `session:expired` when a token refresh fails, and a hook
> elsewhere listens for it. Neither file imports the other; they agree only on
> a string.
>
> The cost is the same as any name-based contract: rename one side and the
> feature stops working with no error. And a broadcast reaches listeners it was
> not aimed at — our handler explicitly ignores the event on the login and
> registration pages, because unauthenticated 401s there would otherwise show a
> false "session expired" dialog.

---

# Part Q — Validation Checklist

- [ ] I can explain why a browser can only run JavaScript, in terms of
      agreement, safety and history. *(A.3, A.4)*
- [ ] I can explain the difference between `let`, `const` and `var`, and why
      `const` does not freeze an array's contents. *(C.1)*
- [ ] I can explain the difference between `null` and `undefined`. *(C.2)*
- [ ] I can state the rule for `===` and give one example of `==` behaving
      surprisingly. *(C.3)*
- [ ] I can explain when `||` is a bug and `??` is correct, with the trial-count
      example. *(C.4, N5)*
- [ ] I can use `map`, `filter` and `find`, and say why they are preferred over
      loops. *(D.3)*
- [ ] I can explain a closure and write `makeCounter` from memory. *(E.3, N8)*
- [ ] I can explain why the browser has one thread and what happens if code
      takes too long. *(F.2)*
- [ ] I can explain why event listeners must be removed. *(F.3)*
- [ ] I can explain why `localStorage` is unsuitable for an authentication
      token. *(F.5)*
- [ ] I can explain why `fetch` does not reject on a 404. *(G.5, N11)*
- [ ] I can write the in-flight de-duplication pattern from memory. *(G.6, N12)*
- [ ] I can explain `buffer = blocks.pop() || ""` and what breaks without it.
      *(G.7, N13)*
- [ ] I completed M12, M13 and M15 by running them.
- [ ] **The real test:** open
      [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts) and read
      `apiFetch` and `askQuestionStream` end to end — explaining every `await`,
      every `?.`, every `||`, every spread, every callback, and what would break
      if each were removed. Then do the same for
      [`frontend/src/hooks/useSessionExpiry.ts`](../frontend/src/hooks/useSessionExpiry.ts),
      which is short enough to hold entirely in your head.

If the last box is ticked, you can read the JavaScript in this project — and
Chapter 09 can be about what TypeScript adds, rather than about the language
underneath.

---

*Next: [09-typescript.md](09-typescript.md) — the extra words in those files:
what a type is, why a large frontend needs them, and the real bugs in this
repository that a type would have caught.*
