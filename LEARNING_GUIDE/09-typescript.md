# 09 — TypeScript

**Prerequisites:** none that this chapter will not re-explain. Where an idea
from earlier is needed — what a browser is, what a function is, what a network
request is — it is restated in a sentence before use.

**What this chapter is about.** The browser part of this system is written in
files ending in `.ts` and `.tsx`. Those files look like JavaScript with extra
words sprinkled through them:

```typescript
export const track = (event: string, properties?: Record<string, unknown>) => {
```

Those extra words — `: string`, `?`, `Record<string, unknown>` — are
**TypeScript**. This chapter explains what they are, what problem they solve,
how they work, and why a project this size would be genuinely difficult to
maintain without them.

**The single most important thing to understand, stated up front so nothing
later confuses you:** TypeScript does not exist when the program runs. It is
checked before the program is built, then **completely removed**. Everything it
does, it does while you are writing code. That one fact explains all of its
strengths and every one of its limits.

---

# Part A — The Problem That Types Solve

## A.1 What goes wrong without them

Here is a small program in ordinary JavaScript — the language browsers run.
A quick anchor first: a **function** is a named group of instructions, and an
**object** is a bundle of labelled values.

```javascript
function getGreeting(user) {
  return "Hello, " + user.name;
}

getGreeting({ name: "Priya" });      // "Hello, Priya"
getGreeting({ nmae: "Priya" });      // "Hello, undefined"
getGreeting("Priya");                // "Hello, undefined"
getGreeting();                       // CRASH
```

Look carefully at the second line. The property is misspelled — `nmae` instead
of `name`. JavaScript does not complain. Asking an object for a label it does
not have gives back the special value `undefined`, meaning "nothing is here",
and joining that to text produces the string `"Hello, undefined"`.

**Nothing failed.** No error appeared. A user somewhere saw "Hello,
undefined" on their screen, and the only way anyone found out was that they
complained.

**That is the problem.** In a small program you would notice. In a program of
three hundred files, written over months, where the object came from a server
and passed through six functions before arriving here, you would not.

## A.2 What a "type" actually means

Anchor: a computer stores everything as numbers — Chapter 05 called the
smallest unit a **byte**. The number `5`, the letter `A`, and part of a picture
are all just numbers in memory. What makes them different is **how the program
agrees to interpret them**.

**A type is that agreement: what kind of value this is, and therefore what you
may do with it.**

- If something is text, you may make it uppercase; you may not divide it by
  two.
- If something is a number, you may divide it; asking for its length is
  meaningless.
- If something is an object with a `name` label, you may read `.name`; reading
  `.nmae` is a mistake.

Every language has types. The question is not *whether* values have types —
they always do — but **when the language checks that you are using them
correctly.**

## A.3 Two moments at which checking can happen

There are exactly two options, and the whole history of this subject is the
trade-off between them.

**Dynamic checking** happens *while the program runs*. The program starts, and
when it reaches a line, it looks at the actual value and decides. JavaScript
and Python both work this way.

**Static checking** happens *before the program runs*. A separate program reads
your code, works out what kind of value each thing must be, and reports
mistakes without ever running it.

| | Dynamic | Static |
|---|---|---|
| When mistakes are found | when that line runs, possibly never | before running, always |
| Speed of writing | fast; write and go | slower; must satisfy the checker |
| Confidence in a large change | low | high |
| Small scripts | ideal | overhead |
| Large systems | painful | necessary |

**Neither is "better".** They optimise for different things, and the right
answer depends on how big the program is and how expensive a mistake is.

## A.4 Why JavaScript's dynamism stopped being enough

JavaScript was created in 1995 for scripts of a few dozen lines that made a
menu open. Dynamic checking was obviously right: the program was small enough
to hold in your head, and a mistake meant a menu misbehaved.

By 2012 people were building applications of hundreds of thousands of lines in
the same language, and the same dynamism produced daily pain:

1. **Typos become `undefined`, silently** — A.1's example.
2. **Nobody knows what a function expects.** You must read its body, and the
   bodies of everything it calls.
3. **Renaming is terrifying.** Rename a property and you must find every use by
   searching text, hoping nothing is computed at runtime.
4. **Refactoring is guesswork.** Change a function's shape and you find the
   broken call sites by shipping and waiting.
5. **Editors cannot help.** Autocompletion needs to know what a thing is.

**The scale changed; the language did not.** That gap is what TypeScript was
built to fill.

## A.5 What people tried before, and why TypeScript won

Four earlier attempts, each instructive:

**Comments describing types (JSDoc).** Write the types in a comment above the
function. Tools could read them. It worked, sort of, and it had the fatal
weakness of every comment: **nothing forces it to stay true.** The code changes,
the comment does not, and now you have a confident lie. (Chapter 03 has a whole
argument about this: a control that lies is worse than an absent one.)

**A different language entirely (Dart, CoffeeScript).** These required
abandoning JavaScript and rewriting. Nobody rewrites a working product.

**Flow (Facebook, 2014).** A type checker for JavaScript, technically strong,
but tied to one company's toolchain and with weaker editor support.

**TypeScript (Microsoft, 2012).** It won for one reason above all others, and
it is a reason worth remembering because it recurs throughout technology:

> **Every valid JavaScript file is already a valid TypeScript file.**

You can rename one file from `.js` to `.ts` and it still works. Then add one
annotation. Then another. **A migration path that starts with "change
nothing" is the migration path teams actually take.** Flow required more
commitment; Dart required everything.

---

# Part B — What TypeScript Actually Is

## B.1 A layer that disappears

TypeScript is **JavaScript plus a way to write down what kind of value each
thing is**. Before the code reaches a browser, a program called the **compiler**
reads it, checks that everything is consistent, and then **deletes every type
annotation**, producing plain JavaScript.

```typescript
const name: string = "Priya";          // TypeScript
```

becomes

```javascript
const name = "Priya";                  // what the browser gets
```

This removal is called **type erasure**, and it has three consequences you must
internalise now:

1. **Types cost nothing at runtime.** No speed penalty, no extra memory.
2. **Types cannot check anything at runtime.** If a server sends data of the
   wrong shape, TypeScript will not notice — it is not there any more.
3. **A type is a claim about what *should* be true**, verified against your
   code, not against reality.

**That second point is the most misunderstood thing about TypeScript**, and it
is the subject of Part G. Beginners assume declaring a response type means the
response is checked. It does not.

## B.2 The compiler is a separate program

In this project, checking is a command:

```bash
cd frontend && npx tsc --noEmit
```

`tsc` is the TypeScript compiler. `--noEmit` means "check everything but do not
write any output files" — because the actual build is done by another tool. So
this command's only job is to answer one question: **is this codebase
consistent?**

Chapter 03 mentioned that the repository's `test-runner` role is told to run
exactly this before trusting any frontend change. It is the frontend's
equivalent of a test suite, and it is much faster than one.

## B.3 How it works internally

Four stages, all before your program runs:

1. **Parse.** Read the text into a tree structure representing the code.
2. **Infer.** Work out the type of everything you did *not* annotate. If you
   write `const x = 5`, it knows `x` is a number without being told.
3. **Check.** Walk the program and verify every use is consistent: every
   function call, every property access, every assignment.
4. **Erase.** Strip the annotations and output plain JavaScript.

Stage 2 is why TypeScript is not exhausting to use. **You annotate the
boundaries — what a function takes and returns — and the compiler works out
everything in the middle.**

## B.4 Structural typing — the idea that makes it feel natural

This is a genuinely important concept and it differs from most typed languages.

In many languages (Java, C#), two types are the same only if they have the
**same name**. That is **nominal typing**.

TypeScript compares **shape**. If a value has the properties required, it fits —
whatever it is called or where it came from. That is **structural typing**.

```typescript
interface HasName {
  name: string;
}

function greet(thing: HasName) {
  return "Hello, " + thing.name;
}

greet({ name: "Priya" });                       // fine
greet({ name: "Priya", age: 20 });              // also fine — extra is allowed
greet({ nmae: "Priya" });                       // ERROR — no `name` property
```

**Why this design was chosen.** JavaScript code is full of plain objects that
were never declared as anything. Requiring a declared name for each would have
made adopting TypeScript impossible. Structural typing lets existing code fit
existing types with no changes — the same "start by changing nothing"
philosophy from A.5.

**The practical consequence:** you describe the *shape you need*, not the
*class you have*. `greet` says "I need something with a name", not "I need a
User".

---

# Part C — The Syntax, From Zero

## C.1 Annotating a variable

Anchor: a **variable** is a name that refers to a value.

```typescript
let count: number = 5;
let username: string = "priya";
let isReady: boolean = true;
```

The pattern is `name: type`. The colon is not punctuation you can leave out —
it is what marks the type.

## C.2 Inference — and why you should mostly not annotate

```typescript
let count = 5;               // TypeScript already knows: number
count = "hello";             // ERROR: Type 'string' is not assignable to type 'number'
```

You did not write a type, and it caught the mistake anyway. TypeScript infers
from the value you assigned.

**So when should you write annotations?** The rule used by nearly every
professional codebase, including this one:

- **Annotate the boundaries**: what a function accepts and returns, and the
  shape of data crossing between parts of the system.
- **Let inference handle the inside**: local variables inside a function.

**Why.** Annotating a local variable repeats what the compiler already knows —
noise that must be kept in step. Annotating a function's inputs and outputs is
a *contract*, and a contract is exactly the thing that should be written down.

## C.3 Functions

```typescript
function add(a: number, b: number): number {
  return a + b;
}

add(2, 3);          // 5
add("2", 3);        // ERROR: Argument of type 'string' is not assignable to parameter of type 'number'
```

`(a: number, b: number)` are the inputs. The `: number` after the brackets is
the **return type**.

**Should you write the return type?** It is inferred, so it is optional — but
writing it is a good habit for anything non-trivial. It makes the compiler check
that *your function does what you claimed*, rather than silently agreeing with
whatever you happened to return.

This project writes it on its API functions, from
[`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts):

```typescript
export const listDocuments = async (
  workspaceId?: string,
  chatSessionId?: string,
): Promise<Document[]> => {
```

Read the return type: `Promise<Document[]>`. A **promise** is an object standing
for a result that is not ready yet — a network request takes time, so the value
arrives later. `Document[]` means "a list of Documents". So this function
promises to eventually produce a list of documents. `Document` and the angle
brackets are explained in C.5 and C.9.

## C.4 Arrays and objects

```typescript
const names: string[] = ["alice", "bob"];
const scores: number[] = [0.9, 0.4];

const user: { name: string; age: number } = { name: "Priya", age: 20 };
```

That last line is unpleasant to read and worse to repeat, which is exactly why
the next section exists.

## C.5 Interfaces — naming a shape

**The problem.** The same object shape appears in twenty places. Writing it out
each time is unreadable and impossible to change.

**An interface gives a shape a name.**

```typescript
interface User {
  name: string;
  age: number;
}

const priya: User = { name: "Priya", age: 20 };

function greet(u: User): string {
  return `Hello, ${u.name}`;
}
```

Here is a real one from this project, and it is worth reading closely because it
is the shape of a document as the browser understands it:

```typescript
export interface Document {
  id: string;
  filename: string;
  status: 'PENDING_UPLOAD' | 'UPLOADED' | 'PROCESSING' | 'EXTRACTED' | 'INDEXING' | 'READY' | 'FAILED' | 'DEDUPLICATED';
  duplicate_of?: string;
  workspace_id?: string;
  chat_session_id?: string | null;  // P1: per-chat isolation
  created_at: string;
  source?: string; // "upload" | "clip" | "scan"
}
```

Six things in eight lines, and every one is a decision:

- **`export`** makes it usable from other files.
- **`id: string`** — the identifier is text, not a number. It is a long unique
  code, and treating it as text prevents anyone accidentally doing arithmetic
  on it.
- **`status: 'PENDING_UPLOAD' | ... `** — this is a **literal union type**
  (C.7): the status may be *one of exactly these eight words*. Not any string.
  Misspell one and the compiler stops you.
- **`duplicate_of?: string`** — the `?` means **optional**: this property may be
  absent. Reading it gives `string | undefined`, and TypeScript will insist you
  handle the `undefined` case.
- **`chat_session_id?: string | null`** — optional *and* possibly `null`. Three
  states: absent, explicitly null, or a value. That is not over-engineering —
  the server genuinely distinguishes "field not sent" from "sent as no chat".
- **`created_at: string`** — a date, carried as text. Chapter 05 explained that
  JSON — the text format used to send data over a network — has no date type,
  so dates travel as text and are converted when needed.

**Compare that interface with the eight status values in the Python model on
the server.** They are the same eight. Two languages, two files, one agreed
vocabulary — and nothing automatically keeps them in step. That is a real risk,
and it appears in the critique in Part L.

## C.6 `type` versus `interface`

There are two ways to name a shape:

```typescript
interface User { name: string }
type User = { name: string };
```

For objects they are nearly interchangeable. The difference that matters:
**`type` can name things that are not objects**, which interfaces cannot.

```typescript
type Theme = "light" | "dark" | "system";
```

That is real, from
[`frontend/src/hooks/useTheme.ts`](../frontend/src/hooks/useTheme.ts). It is
not an object — it is "one of these three words" — so it must be a `type`.

**The convention in most codebases**, and in this one: `interface` for object
shapes, `type` for unions and everything else.

## C.7 Union types — "one of these"

**The problem.** A value may legitimately be one of several kinds, and the code
must handle each.

```typescript
type Result = string | number;

let x: Result = "hello";      // fine
x = 42;                       // fine
x = true;                     // ERROR
```

The `|` reads as "or".

**The most useful version is a union of exact values** — a **literal union**:

```typescript
type Theme = "light" | "dark" | "system";
let t: Theme = "dark";        // fine
let u: Theme = "purple";      // ERROR: Type '"purple"' is not assignable to type 'Theme'
```

**Why this is so valuable.** It turns a whole class of typo into a compile
error, and it makes the editor offer you the three valid options as you type.
Before literal unions, you would write `theme: string` and discover `"purpel"`
in production.

This project uses them heavily, and
[`frontend/src/lib/analytics.ts`](../frontend/src/lib/analytics.ts) is the
clearest example:

```typescript
  documentUploaded: (workspace: string, file_type: string, file_size_mb_bucket: '0-1' | '1-5' | '5+') =>
    track('document_uploaded', { workspace, file_type, file_size_mb_bucket }),

  upgradeModalShown: (trigger: 'limit_reached' | 'feature_locked' | 'user_click') =>
    track('upgrade_modal_shown', { trigger }),

  exportDownloaded: (format: 'pdf' | 'docx' | 'md' | 'csv', workspace: string) =>
    track('export_downloaded', { format, workspace }),
```

**Why this matters beyond typos.** Analytics data is only useful if the values
are consistent. If one part of the app records `'pdf'` and another records
`'PDF'`, the numbers split into two categories and every chart is wrong — and
nobody notices for months, because there is no error anywhere. **The literal
union makes the data consistent by construction**, which is the same idea as
the enum on the server side and the same idea as Chapter 03's choke point.

Notice too what is *not* a literal union: `workspace: string`. That is a
looser choice — the workspace names are also a fixed set of seven, so they
could be one too. A small missed opportunity, and worth noticing as a reader.

## C.8 Narrowing — proving which one it is

If a value might be a string or a number, you cannot use it as either until you
establish which. TypeScript follows your checks and **narrows** the type:

```typescript
function describe(value: string | number): string {
  if (typeof value === "string") {
    return value.toUpperCase();     // here, TypeScript knows it is a string
  }
  return value.toFixed(2);          // here, it must be a number
}
```

`typeof` asks what kind of value something is at runtime. Inside the `if`, the
compiler *knows* it is text; after it, the only remaining possibility is a
number.

**This is the feature that makes unions usable.** Without narrowing you could
declare a union and never safely use it.

Narrowing also happens with `null` checks — which is the single most common one
in real code:

```typescript
const reader = res.body?.getReader();
if (!reader) throw new Error("No readable stream");
// below this line, TypeScript knows `reader` is not undefined
```

That is real code from this project's streaming reader. The `?.` guards against
a missing body; the `if (!reader) throw` both handles the error **and** proves
to the compiler that everything below is safe.

## C.9 Generics — a type with a hole in it

**The problem.** You write a function that returns the first item of a list. It
works for any list. What is its return type?

Saying `any` throws away all information. Writing one version per kind of list
is absurd.

**A generic is a type with a placeholder that gets filled in at each use.**

```typescript
function first<T>(items: T[]): T | undefined {
  return items[0];
}

first([1, 2, 3]);            // TypeScript knows: number | undefined
first(["a", "b"]);           // string | undefined
```

`<T>` declares a placeholder — a name for "whatever type this is used with". It
is filled in automatically from the argument.

**Why the letter `T`?** Convention, for "Type". You may name it anything;
`T`, `K` (key), `V` (value) and `E` (element) are conventional.

**You will use generics long before you write one**, because they appear in
every library:

```typescript
Promise<Document[]>      // a promise that will produce a list of Documents
Array<string>            // the same as string[]
Record<string, unknown>  // an object whose keys are text and values are unknown
```

All three appear in this project. `Record<string, unknown>` is the type of the
analytics properties bag: *some object with text keys, whose values we make no
claim about*. Which brings us to the most important distinction in the chapter.

## C.10 `any`, `unknown`, and `never`

**`any` switches off type checking for that value.**

```typescript
let x: any = "hello";
x.toFixed(2);            // no error at compile time — CRASHES at runtime
x.anything.at.all;       // no error — crashes
```

**`any` is not "some type". It is "stop checking".** It is contagious: anything
derived from an `any` also becomes unchecked, so one `any` in the wrong place
can quietly disable checking across a whole area of code.

**`unknown` is the safe version.** It also means "I do not know what this is" —
but it forces you to find out before using it:

```typescript
let y: unknown = "hello";
y.toUpperCase();                       // ERROR — must narrow first
if (typeof y === "string") {
  y.toUpperCase();                     // fine
}
```

**The rule to carry:** when you genuinely do not know a type, use `unknown`, not
`any`. `unknown` moves the check to where the value is used; `any` removes it
entirely.

This project's analytics function does this correctly:

```typescript
export const track = (event: string, properties?: Record<string, unknown>) => {
```

The properties can be anything, so their values are `unknown`. Nobody can
accidentally call a method on them without checking first.

But elsewhere it does not:

```typescript
  onMetadata: (metadata: any) => void,
  onTrustReport?: (trust: any) => void,
```

Those are `any`, so everything the callback does with the metadata is
unchecked. It is convenient, and it means the compiler cannot help when the
server's metadata shape changes. There are **80 uses of `any` in the frontend**,
which is the largest single item in this chapter's critique.

**`never`** is the type of something that can never happen — a function that
always throws, or a branch that cannot be reached. You will meet it in
error messages before you ever write it.

## C.11 Type assertions — the escape hatch, and its price

Sometimes you know something the compiler cannot. An **assertion** tells it to
believe you:

```typescript
const el = document.getElementById("title") as HTMLInputElement;
```

`getElementById` returns "an element or null"; you assert it is specifically an
input element.

**The danger, stated plainly: an assertion is not a check. It is a promise, and
the compiler cannot verify it.** If you are wrong, the code compiles cleanly
and fails at runtime — with the checker having actively helped you hide the
problem.

**A real assertion in this project**, from `useTheme.ts`:

```typescript
const saved = (localStorage.getItem("theme") as Theme) || "system";
```

Work through what this does. `localStorage` is the browser's small permanent
store; `getItem` returns *text or null*, because the key may not exist. The
assertion claims the text is one of `"light" | "dark" | "system"`.

Is that true? Usually — the only code that writes this key writes one of those
three. And the `|| "system"` handles the null case, because null is falsy.

But **it is not guaranteed**. `localStorage` is under the user's control; anyone
can open the browser console and set it to `"purple"`. Then `saved` is
`"purple"`, the assertion is a lie, `|| "system"` does not help because a
non-empty string is truthy, and the theme logic falls through to light mode.

The consequence here is trivial — a wrong colour scheme. The *pattern* is not:
**an assertion applied to data from outside your program is a claim you cannot
back up.** The safe version validates instead of asserting:

```typescript
const raw = localStorage.getItem("theme");
const saved: Theme =
  raw === "light" || raw === "dark" || raw === "system" ? raw : "system";
```

Three comparisons, no assertion, and now the type is *earned* rather than
declared. This is the same distinction Chapter 03 drew between a control that
exists and a control that is claimed.

---

# Part D — Strict Mode

## D.1 What it is

TypeScript can be lenient or demanding. The setting lives in
[`frontend/tsconfig.json`](../frontend/tsconfig.json), and this project chooses
demanding:

```json
{
  "compilerOptions": {
    "strict": true,
    "noEmit": true,
    ...
  }
}
```

`strict: true` switches on a group of stricter checks at once. Two matter most.

## D.2 `strictNullChecks` — the billion-dollar mistake

Without it, every type silently includes `null` and `undefined`:

```typescript
let name: string = null;      // allowed when strict is off!
name.toUpperCase();           // crashes at runtime
```

With it, `null` is a separate thing you must handle:

```typescript
let name: string = null;               // ERROR
let maybe: string | null = null;       // fine, and now you MUST check before use
```

**Why this is the most valuable single flag in TypeScript.** The inventor of the
null reference, Tony Hoare, called it his "billion-dollar mistake" — an
estimate of the cost of the crashes it has caused across the industry since
1965. Strict null checking is the practical answer: **absence becomes part of
the type, so the compiler forces you to deal with it.**

This is why the `Document` interface writes `chat_session_id?: string | null`
rather than just `string`. The absence is *modelled*, so no code can forget it.

## D.3 `noImplicitAny`

Also included in `strict`. Without it, a parameter you forget to annotate
silently becomes `any` — checking quietly switches off. With it, you are forced
to say what you mean.

## D.4 The other settings in this file

```json
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "jsx": "react-jsx",
    "paths": { "@/*": ["./src/*"] }
```

- **`target`** — which version of JavaScript to produce. Newer features are
  rewritten into older equivalents if the target is old.
- **`lib: ["dom", ...]`** — which built-in things exist. `dom` is what tells
  TypeScript that `window`, `document` and `fetch` are real. **This is why the
  same code would not type-check in a Node.js project without adjusting this
  line** — a different runtime has different built-ins.
- **`allowJs`** — plain `.js` files are permitted alongside `.ts`. The gradual
  migration path from A.5, left switched on.
- **`skipLibCheck`** — do not type-check the thousands of files inside
  installed libraries. A large speed win, and a small honesty cost: a
  library's own type errors are not your problem, and checking them can
  paralyse a build over something you cannot fix.
- **`paths`** — lets `@/lib/api` mean `./src/lib/api`, so imports do not become
  `../../../lib/api`.

---

# Part E — The Real Incident: A Bug Fixed at the Type

This is the chapter's centrepiece, because it shows types doing something no
test could do.

## E.1 The problem

A user in the HR workspace uploads a batch of résumés. Every one of them lands
in the **General** workspace instead, where HR's search cannot find them.

Nothing errors. The upload succeeds. The documents exist. They are simply
invisible to the feature that was supposed to use them.

## E.2 The mechanism

The upload function looked roughly like this:

```typescript
export const uploadDocument = async (
  file: File,
  workspaceId?: string,          // ← optional
  chatSessionId?: string,
): Promise<Document> => {
```

The `?` means the caller may leave it out. And one caller did:

```typescript
uploadDocument(file, undefined, chatId)
```

When no workspace is sent, the server falls back to a value in the login token —
which, for every user in this system, is the constant `"general"`. So the
document is stored under General.

From the commit that fixed it (`8638c9c`):

> *"With no workspace sent, the backend falls back to the JWT claim, which is
> the constant 'general', so every batch-uploaded resume landed in the General
> workspace and was invisible to HR retrieval and rankings. Bulk resume ingest
> is HR's headline feature, and it had never once stored a document where HR
> could find it."*

**"Had never once."** The feature had never worked, and nothing had ever
complained.

## E.3 Why fixing the call site would not have been enough

The same defect had already been fixed once before, at a different call site.
This was the second occurrence. The commit is explicit about the reasoning:

> *"This is the same defect as 31c7119, at the sibling call site that commit did
> not check. Fixing line 1614 alone would close the instance and leave the class
> open — the next `uploadDocument` call is one omitted argument away from
> repeating it, and this is the second occurrence, not the first."*

Chapter 03's vocabulary: an **instance** is one bug; a **class** is the family
of bugs sharing a cause. Fixing the call site closes the instance. The class
stays open, because the *contract still permits the mistake*.

## E.4 The fix, and why it is a type change

One character removed:

```typescript
export const uploadDocument = async (
  file: File,
  workspaceId: string,           // ← no longer optional
  chatSessionId?: string,
): Promise<Document> => {
```

And the comment left in the real file explains the reasoning to whoever reads
it next:

```typescript
  // F1: REQUIRED, not optional. When this was `workspaceId?: string` a caller
  // could omit it and the backend fell back to the JWT claim — the constant
  // "general" — so the document landed in the wrong workspace and became
  // invisible to that workspace's retrieval. That happened twice: once in
  // handleFileChange, and again on the HR batch path, which was missed when
  // the first was fixed. Requiring it makes the compiler reject a third
  // instance instead of leaving it to be found in an audit.
```

**The compiler is now the enforcement.** Not a review, not a test, not
discipline.

## E.5 How it was verified — and the sentence that matters most

```
  src/components/WorkspaceUI.tsx(1617,58): error TS2345:
  Argument of type 'undefined' is not assignable to parameter of type 'string'.
```

Two things were proved:

1. **The guard bites.** Putting the defect back produces that exact error. A
   check nobody has watched fail is not evidence (Chapter 03's rule).
2. **`npx tsc --noEmit` is clean** — and, as the commit points out, *that is
   itself the proof that no third call site exists*: **a required parameter
   cannot be omitted anywhere without a compile error.** One command exhaustively
   proves a property across the entire codebase. No test suite can do that.

And then the line that explains why this belongs in a chapter about types at
all:

> *"Test that was absent: none could exist, because the contract permitted the
> mistake; that is why the repair is a type change rather than a test."*

Read it twice. **You cannot write a test for "somebody might omit this
argument", because omitting it was legal.** The only repair that closes the
class is one that makes the mistake unwriteable.

**This is the general lesson of the chapter:**

> Some bugs are best fixed with a test. Some are best fixed with a type. When
> the defect is *"a caller can leave something out"* or *"a value can be a word
> we do not expect"*, the type is the right layer, because it eliminates the
> possibility rather than detecting the occurrence.

---

# Part F — Where TypeScript Stops

## F.1 The boundary

Recall B.1: types are erased before the program runs. So when data arrives from
the network, **nothing checks it**.

```typescript
const res = await apiFetch('/documents');
const docs: Document[] = await res.json();       // a CLAIM, not a check
```

`res.json()` produces whatever the server actually sent. Writing `: Document[]`
tells the compiler to *treat* it as a list of documents. If the server changed a
field name last Tuesday, this line compiles perfectly and every use of the
missing field silently becomes `undefined`.

**This surprises people, so state it clearly: TypeScript checks your code
against itself. It does not check the world.**

## F.2 The two honest ways to handle it

**Option 1 — validate at runtime.** Use a library that checks the shape when
the data arrives and throws when it does not match. In the JavaScript world that
is usually Zod or Valibot.

**Option 2 — accept the risk and keep the contract narrow**, which is what this
project does. The types describe the agreed shape, the server is written by the
same person, and the API contract is documented and treated as an invariant.

**Both are defensible.** What is not defensible is *believing you have option 1
when you have option 2*, which is the mistake this section exists to prevent.

## F.3 The comparison worth carrying to interviews

The server side of this system does the opposite. Its request models validate at
runtime:

```python
class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
```

Because it inherits Pydantic's `BaseModel`, a request missing `query` is
rejected before any handler runs, and `"twelve"` in `top_k` is rejected while
`"12"` is converted.

**Two languages, two philosophies, and both are right for their side:**

| | Frontend (TypeScript) | Backend (Pydantic) |
|---|---|---|
| When it checks | before running | while running |
| What it checks against | your own code | actual incoming data |
| Cost | zero at runtime | a little time per request |
| Protects against | your mistakes | the outside world's mistakes |

**The rule that unifies them:** *check at the boundary where untrusted data
enters.* For the server, that boundary is the request, so it validates at
runtime. For the browser, the "untrusted" input is mostly the developer, so
compile-time checking is the right tool. **The browser's own data from the
server is a third boundary that this project leaves unchecked**, and that is a
real, small, knowingly-accepted gap.

---

# Part G — Reading Real Types From This Repository

Three examples, increasing in subtlety.

## G.1 The response shape

```typescript
export interface QueryResponse {
  query: string;
  answer: string;
  confidence_score: number;
  evidence: EvidenceChunk[];
  diagnostics: TracingDiagnostics;
  /** C10 — false when the backend answered from general knowledge (no documents indexed for this workspace). */
  grounded?: boolean;
  /** C10 — "grounded" | "general". Frontend shows an Ungrounded badge for "general". */
  mode?: "grounded" | "general";
}
```

- **`evidence: EvidenceChunk[]`** — a list of another named shape. Types
  compose.
- **`/** ... */` comments** are **doc comments**: editors show them when you
  hover over the field. They are documentation attached to the type itself.
- **`grounded?: boolean` and `mode?: "grounded" | "general"`** are optional
  because older responses may not include them. The `?` is how a contract
  evolves without breaking existing clients.

**And there is a subtle design question here worth noticing as a reader.**
`grounded` and `mode` say the same thing in two ways. Two fields that must agree
is a state that can become inconsistent — exactly the kind of thing Chapter 03
warns about. A single `mode` field would be impossible to contradict. It is a
minor issue; noticing it is the skill.

## G.2 A function type as a parameter

```typescript
export const askQuestionStream = async (
  query: string,
  topK: number,
  onStatus: (msg: string) => void,
  onMetadata: (metadata: any) => void,
  onToken: (token: string) => void,
  onError: (err: string) => void,
  onDone: () => void,
  signal?: AbortSignal,
  ...
```

`onStatus: (msg: string) => void` is a **function type**: something that takes
one string and returns nothing. `void` means "returns nothing useful".

**Why declare it.** Passing a function that expects a number where a string is
expected would otherwise be found only at runtime, when the answer is already
streaming.

**And why this signature is also a weakness.** Fourteen positional parameters,
six of them functions with similar shapes. `onToken` and `onError` are both
`(x: string) => void` — **so swapping them compiles cleanly and produces error
messages rendered as answer text.** The type system cannot save you from
argument order. An options object would fix it, and that is Chapter 08's
critique restated here with the type-level reason.

## G.3 A type used to constrain a whole feature

```typescript
type Theme = "light" | "dark" | "system";

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("system");

  const applyTheme = useCallback((t: Theme) => {
    const root = document.documentElement;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const isDark = t === "dark" || (t === "system" && prefersDark);
    root.setAttribute("data-theme", isDark ? "dark" : "light");
    root.classList.toggle("dark", isDark);
  }, []);
```

- **`useState<Theme>("system")`** — a generic (C.9) filling the placeholder with
  `Theme`, so the stored value can only ever be one of the three words. Anything
  that tries to set a fourth is a compile error. *(What `useState` and
  `useCallback` are is Chapter 21's subject; the point here is the type.)*
- **`t === "dark" || (t === "system" && prefersDark)`** — because `t` is a
  literal union, the editor autocompletes those exact strings, and a typo like
  `"darkk"` is an immediate error rather than a condition that is silently never
  true.

**That last point is worth dwelling on.** Without the type, `t === "darkk"`
compiles, runs, and is simply always false. Dark mode never activates and no
error appears anywhere. **A literal union converts a silent always-false
condition into a red squiggle.**

---

# Part H — Mistakes and Debugging

## H.1 Beginner mistakes

1. **Annotating everything.** `const count: number = 5;` — the compiler already
   knew. Annotate boundaries, not locals.
2. **Reaching for `any` when stuck.** It makes the error disappear and the bug
   remain. Use `unknown` and narrow.
3. **Using `as` to silence an error.** An assertion is a promise, not a check.
   If you need `as` more than rarely, your types are wrong somewhere upstream.
4. **Thinking types validate server data.** They do not (Part F).
5. **Confusing `?` with `| null`.** `?` means the property may be missing;
   `| null` means it may be present and empty. The `Document` interface uses
   both together on purpose.
6. **Fighting a library's types instead of reading them.** Hover over the
   symbol; the answer is usually right there.

## H.2 Production mistakes

1. **`any` at the network boundary.** The place with the least information gets
   the least checking — precisely backwards. This project's
   `onMetadata: (metadata: any)` is an example.
2. **Duplicating a type instead of importing it**, so two copies drift.
3. **Letting the type check fall out of the build pipeline.** If `tsc --noEmit`
   does not run automatically, errors accumulate until nobody can fix them.
4. **Two sources of truth for one vocabulary** — the eight document statuses
   exist in a Python file and a TypeScript file with nothing keeping them in
   step. Adding a ninth on the server would not produce any error in the
   browser; it would produce a status the browser silently does not understand.

## H.3 How to read a TypeScript error

They look intimidating and follow a fixed shape:

```
src/components/WorkspaceUI.tsx(1617,58): error TS2345:
Argument of type 'undefined' is not assignable to parameter of type 'string'.
```

- **`src/components/WorkspaceUI.tsx`** — the file.
- **`(1617,58)`** — line 1617, character 58.
- **`TS2345`** — the error's number; searchable if the message is unclear.
- **The message** always follows the same pattern: *this thing you have* is not
  assignable to *this thing that is wanted*.

**The rule for reading any TypeScript error: find the two types and ask which
one is wrong.** Sometimes your value is wrong. Sometimes your declaration is
wrong. It is never the compiler.

**For long errors involving nested objects**, read from the **bottom** up: the
last lines say precisely which property mismatched, and the earlier lines are
the path down to it.

## H.4 Debugging techniques

1. **Hover over anything** in an editor to see its inferred type. This answers
   most questions instantly.
2. **Ask the compiler what it thinks**, with a deliberate mistake:
   ```typescript
   const check: number = someValue;   // error message names someValue's real type
   ```
3. **Run `npx tsc --noEmit` after every non-trivial change**, exactly as this
   project's rules require.
4. **When a type is `any` and you do not know why**, look upstream: `any` spreads
   from wherever it entered.
5. **Remember it is erased.** If something behaves oddly *at runtime*, the type
   system is not involved. Debug it as JavaScript.

---

# Part I — How Companies Use This

- **Most large frontends are TypeScript now**, including Google's,
  Microsoft's, Airbnb's and Slack's. The industry moved between roughly 2017
  and 2021, and the argument that settled it was refactoring confidence, not
  bug counts.
- **Strict mode is the norm in new projects** and a long migration in old ones.
  Teams typically switch on `strictNullChecks` last, because it produces the
  most errors — and finds the most real bugs.
- **The frontend/backend split you see here is standard**: compile-time checking
  in the browser, runtime validation at the server's edge.
- **Some companies generate the frontend types from the backend automatically**,
  from an OpenAPI description, so the two vocabularies cannot drift. This
  project's backend already produces such a description — `main.py` sets
  `openapi_url=f"{settings.API_V1_STR}/openapi.json"` — so the generator is one
  build step away from being possible. That is the single highest-value
  improvement available here, and it appears in the critique.
- **In interviews**, the questions are almost always: `any` versus `unknown`;
  what strict null checking buys; whether types exist at runtime; and "tell me
  about a bug a type caught". Part M gives answers to all four.

---

# Part J — Exercises

Use an editor with TypeScript, or the TypeScript Playground in a browser
(`typescriptlang.org/play`), which needs nothing installed.

### Level 0 — First contact

**J1.** Declare a `const` holding your name with an explicit `: string`. Then
declare one without an annotation. Hover over both. What does the compiler
already know?

**J2.** Write `let count: number = 5;` then `count = "five";`. Read the error
message and name the two types it mentions.

**J3.** Write a function `double(n: number): number`. Call it with `4`, then
with `"4"`. Explain what the second error is telling you.

### Level 1 — Shapes

**J4.** Write an interface `Chunk` with `id: string`, `page: number`, and an
optional `score?: number`. Create one object with the score and one without.
Then try to read `.score` and add ten to it. What does the compiler say, and
why is it right?

**J5.** Write `type Status = "PENDING" | "READY" | "FAILED"`. Assign each valid
value, then try `"Ready"`. Explain in one sentence why this catches a bug that
`string` would not.

**J6.** Given `interface User { name: string }`, write a function that takes a
`User` and call it with `{ name: "P", age: 20 }`. Does it work? Explain what
structural typing means using this result.

### Level 2 — Absence and narrowing

**J7.** With strict mode on, write `let title: string = null;`. Read the error.
Now change the type so that `null` is allowed, and write code that uses `title`
safely.

**J8.** Write a function `describe(value: string | number): string` that returns
the uppercase text for a string and a two-decimal version for a number. Explain
which line does the narrowing.

**J9.** Write a function that takes `Chunk | undefined` and returns the page
number or `-1`. Do it twice: once with an `if`, once with `?.` and `??`.

### Level 3 — Generics and safety

**J10.** Write `first<T>(items: T[]): T | undefined`. Call it with numbers and
with strings, and confirm the inferred return type differs.

**J11.** Take this and improve it without using `any`:

```typescript
function parse(input: any) {
  return input.value.toUpperCase();
}
```

State what could go wrong at runtime with the original, and what your version
forces the caller to do.

**J12.** Explain the difference between these two, and say which you would use
for data arriving from a network request:

```typescript
const a = data as Document;
const b: Document = validateDocument(data);
```

### Level 4 — Repository-shaped

**J13.** Rewrite this real line so the type is *earned* rather than asserted,
and say what user action breaks the original:

```typescript
const saved = (localStorage.getItem("theme") as Theme) || "system";
```

**J14.** The upload function's `workspaceId` was changed from optional to
required, and the fix was verified by running `npx tsc --noEmit`. Explain, in
your own words, why a clean run of that command proves something a passing test
suite could not.

**J15.** The eight document statuses exist twice: as a Python enum on the server
and as a literal union in `api.ts`. Describe the failure that happens when
someone adds a ninth status on the server only — including what the user sees
and why nothing errors. Then propose two different fixes and say what each
costs.

---

# Part K — Answer Key

**K1.** Both are `string`. The compiler infers from the assigned value, so the
annotation adds nothing here. This is why the convention is to annotate
boundaries — function inputs and outputs — and let inference handle locals,
where an annotation is duplication that must be maintained.

**K2.** `Type 'string' is not assignable to type 'number'.` The two types are
`string` (what you supplied) and `number` (what was wanted). Every TypeScript
error follows this shape: *what you have* versus *what is expected*.

**K3.** `Argument of type 'string' is not assignable to parameter of type
'number'.` It is telling you the call site is wrong — the function's contract
says it needs a number. Note it names the *parameter*, which tells you the
problem is at the call, not inside the function.

**K4.**
```typescript
interface Chunk {
  id: string;
  page: number;
  score?: number;
}
const withScore: Chunk = { id: "a", page: 1, score: 0.9 };
const without: Chunk = { id: "b", page: 2 };

without.score + 10;   // ERROR: 'without.score' is possibly 'undefined'
```
The compiler is right because `score` may genuinely be absent, and adding ten to
"nothing" produces `NaN` — a silent wrong number rather than a crash. You must
handle it: `(without.score ?? 0) + 10`.

**K5.** `"Ready"` fails: `Type '"Ready"' is not assignable to type 'Status'`.
With `status: string`, both `"READY"` and `"Ready"` compile, so a
capitalisation mistake becomes a comparison that is silently always false — no
error, no crash, a feature that simply never triggers. **A literal union turns a
silent wrong-value bug into a compile error.**

**K6.** It works. Structural typing means a value fits a type if it *has the
required shape*, regardless of what it is called or whether extra properties are
present. The function asked for something with a `name`; the object has one.
This is what made TypeScript adoptable — existing JavaScript objects fit
existing types without being rewritten.

**K7.** The error is `Type 'null' is not assignable to type 'string'.` The fix:
```typescript
let title: string | null = null;
if (title !== null) {
  title.toUpperCase();       // narrowed to string here
}
```
Absence is now part of the type, so the compiler forces you to handle it. This
is `strictNullChecks`, and it is the single most valuable flag in TypeScript.

**K8.**
```typescript
function describe(value: string | number): string {
  if (typeof value === "string") {
    return value.toUpperCase();
  }
  return value.toFixed(2);
}
```
The `if (typeof value === "string")` line does the narrowing. Inside it the
compiler knows the value is text; after it, `string` has been eliminated, so the
only remaining possibility is `number`. Narrowing is what makes unions usable —
without it you could declare one and never safely use it.

**K9.**
```typescript
function pageOf(c: Chunk | undefined): number {
  if (!c) return -1;
  return c.page;
}

const pageOf2 = (c: Chunk | undefined): number => c?.page ?? -1;
```
Both are correct. The second is shorter; the first has room for a log line or a
different error path, which is often what you want in production code.

**K10.**
```typescript
function first<T>(items: T[]): T | undefined {
  return items[0];
}
first([1, 2, 3]);       // number | undefined
first(["a", "b"]);      // string | undefined
```
The placeholder `T` is filled in from the argument at each call. `| undefined`
is honest: an empty list has no first item, and pretending otherwise is exactly
the kind of lie that produces a runtime crash.

**K11.** With `any`, `input` could be a number, `null`, or an object whose
`value` is not text — and every one of those crashes at runtime with no
compile-time warning. `any` did not describe the input; it switched off
checking.

```typescript
function parse(input: unknown): string {
  if (
    typeof input === "object" && input !== null &&
    "value" in input && typeof (input as { value: unknown }).value === "string"
  ) {
    return (input as { value: string }).value.toUpperCase();
  }
  throw new Error("parse: expected an object with a string `value`");
}
```
`unknown` forces the caller's data to be *proved* before use. The two remaining
assertions are safe because each is guarded by a check immediately above it —
which is the only kind of assertion worth writing.

**K12.** `as Document` is an assertion: a claim the compiler accepts without
verifying, so wrong data compiles cleanly and fails later, somewhere else.
`validateDocument(data)` is a check: it inspects the actual value and either
returns a `Document` or fails immediately.

For network data, use the second. TypeScript is erased before the program runs,
so it cannot check anything the server sends — and the network is exactly where
your assumptions are least likely to hold.

**K13.**
```typescript
const raw = localStorage.getItem("theme");
const saved: Theme =
  raw === "light" || raw === "dark" || raw === "system" ? raw : "system";
```
The original breaks when a user edits `localStorage` in their browser console
and sets `theme` to any other text — say `"purple"`. The assertion tells the
compiler it is a `Theme`, so no error appears; `|| "system"` does not rescue it
because a non-empty string is truthy; and the theme logic falls through to
light mode with no explanation. `localStorage` is under the user's control,
which makes it exactly the kind of place an assertion cannot be trusted.

**K14.** A test proves that *the paths the test exercises* behave correctly. It
cannot prove that no other call site anywhere omits the argument — you would
have to test every call site, and you cannot test the one somebody writes next
month.

A required parameter makes the omission **impossible to express**. So a clean
`tsc --noEmit` is an exhaustive proof over the entire codebase: if any call had
omitted the workspace, compilation would have failed. **The test detects
occurrences; the type eliminates the possibility.** That is the difference
between closing an instance and closing a class.

**K15.** **The failure:** the server begins sending, say, `"QUARANTINED"`. The
browser's `Document` interface does not include it, but types are erased, so
nothing checks the incoming value — the string arrives and is stored. Any code
comparing against the eight known statuses matches none of them, so the document
falls through every branch: no status badge, no progress indicator, possibly not
displayed at all. **The user sees a document that appears stuck or missing, and
no error appears anywhere** — not in the console, not in the server logs, not in
the type checker.

**Fix 1 — generate the frontend types from the server's OpenAPI description.**
The backend already publishes one at `/api/v1/openapi.json`. A build step
regenerates the interfaces, so a new status appears in the browser's type
immediately and every place that handles statuses fails to compile until it is
updated. *Cost:* a build step to maintain, a generated file in the repository,
and a discipline that the generator is re-run.

**Fix 2 — validate responses at runtime** with a schema library, and log loudly
when a value is outside the known set. *Cost:* a dependency, a small runtime
cost per response, and schemas that must be kept in step by hand — which is the
same drift problem one layer along, though at least it now fails loudly.

A pragmatic third option: keep the types as they are, but add a
`default:` branch wherever status is handled that logs an unknown value. It
costs almost nothing and converts a silent failure into a visible one — which,
by this project's own loud-degradation rule, is the minimum acceptable
behaviour.

---

# Part L — Senior Critique: The TypeScript in This Repository

### Strengths

1. **`strict: true` is on.** Many codebases never manage this, and it is where
   most of the value lives — particularly strict null checking.
2. **Literal unions are used where they matter**: document statuses, themes,
   export formats, analytics buckets. Each converts a whole family of
   typo-and-inconsistency bugs into compile errors.
3. **The API surface is typed at the boundary** — twenty exported interfaces
   describing what crosses between browser and server, which is exactly where
   annotations pay.
4. **A real defect was fixed at the type level**, with the compiler error
   observed and recorded, and with an explicit argument for why a test could not
   have done it.
5. **`Record<string, unknown>` rather than `any`** in the analytics helper —
   the correct instinct in the one place values are genuinely unknown.

### Weaknesses

1. **80 uses of `any`.** Several are at the network boundary
   (`onMetadata: (metadata: any)`, `onTrustReport?: (trust: any)`), which is
   precisely backwards: the place with the least certainty gets the least
   checking. `unknown` plus narrowing would cost a few lines and restore the
   guarantee.
2. **Two sources of truth for shared vocabularies.** The eight document
   statuses exist independently in Python and in TypeScript. Nothing detects
   drift, and the failure mode is silent (K15).
3. **No runtime validation of responses.** Every `await res.json()` is an
   unverified claim. Defensible for a single-author system; it should be a
   stated decision rather than an omission.
4. **Assertions on external data.** `localStorage.getItem("theme") as Theme` is
   the clearest case: a value the user controls, asserted rather than checked.
   Low impact here, wrong pattern generally.
5. **Type-level safety does not extend to argument order.** `askQuestionStream`
   takes six callbacks, several with identical signatures, so swapping
   `onToken` and `onError` compiles cleanly and renders errors as answer text.
   An options object would make each argument named and order-independent.
6. **`skipLibCheck: true`** is pragmatic and standard, but it does mean a
   library shipping broken types goes unnoticed until something misbehaves.

### The one improvement I would make first

**Generate the frontend types from the backend's OpenAPI description.** The
server already publishes it. One build step would eliminate the drift class
entirely, make `tsc --noEmit` a genuine contract check between the two halves of
the system, and turn "the server added a field" from a silent frontend gap into
a compile error. Everything else on this list is smaller.

---

# Part M — Interview Questions With Model Answers

**M1. "What is the difference between `any` and `unknown`?"**

> `any` switches off type checking for that value — you can call anything on it
> and the compiler stays silent, so a mistake becomes a runtime crash. It is
> also contagious: values derived from it are unchecked too.
>
> `unknown` also means "I do not know what this is", but it forces you to
> narrow before use. You must check `typeof`, or test for a property, before the
> compiler lets you do anything.
>
> The practical rule is that `unknown` moves the check to the point of use,
> while `any` removes it. In our analytics helper the properties bag is
> `Record<string, unknown>`, which is right. Elsewhere we have callbacks typed
> `(metadata: any)`, which is a real weakness — the network boundary is where I
> have the least certainty, so it is the worst place to switch checking off.

**M2. "Do TypeScript types exist at runtime?"**

> No. They are checked before the build and then erased entirely, so the browser
> receives plain JavaScript. That has two consequences.
>
> The good one: types cost nothing at runtime. The important one: they cannot
> validate anything the program receives. Writing `const docs: Document[] =
> await res.json()` is a claim, not a check — if the server changed a field
> name, that line compiles fine and every use of the missing field silently
> becomes `undefined`.
>
> That is why our backend uses Pydantic, which validates at runtime, at the
> boundary where untrusted data actually arrives. Compile-time checking protects
> against my mistakes; runtime validation protects against the world's.

**M3. "Tell me about a bug that a type caught."**

> We had an upload function whose `workspaceId` parameter was optional. One
> caller — the HR batch upload — passed `undefined`. With no workspace, the
> server fell back to a value in the login token, which is the constant
> "general", so every batch-uploaded résumé landed in the General workspace and
> was invisible to HR's own search. Bulk résumé ingest is HR's headline feature
> and it had never once worked, with no error anywhere.
>
> It was the second occurrence of the same defect at a sibling call site, so
> fixing the call would have closed the instance and left the class open. We
> made the parameter required instead. Restoring the bug produces
> `error TS2345: Argument of type 'undefined' is not assignable to parameter of
> type 'string'`, and a clean `tsc --noEmit` proves no other call site omits it —
> which is a stronger guarantee than any test, because a required parameter
> cannot be omitted anywhere without a compile error.
>
> No test could have covered it, because omitting the argument was legal. That
> is the case where the type is the right layer for the fix.

**M4. "What does strict mode give you?"**

> The flag I care about most is `strictNullChecks`. Without it every type
> silently includes `null` and `undefined`, so `let name: string = null` is
> legal and crashes later. With it, absence becomes part of the type and the
> compiler forces you to handle it.
>
> That is why our `Document` interface writes
> `chat_session_id?: string | null` rather than `string`. The `?` says the
> property may be missing and the `| null` says it may be present and empty —
> three genuinely different states that the server distinguishes, so the type
> distinguishes them too.
>
> `noImplicitAny` matters as well: without it a parameter you forget to annotate
> silently becomes `any`, and checking quietly switches off in that area.

**M5. "When would you not use TypeScript?"**

> For a script of fifty lines that one person runs occasionally, the setup and
> the checker are overhead with no payoff — the whole thing fits in your head.
>
> The value comes from scale and from time: many files, many people, and code
> that will be changed months after it was written. The strongest argument is
> not bug counts, it is refactoring confidence. Renaming a field across three
> hundred files is a five-minute job with types and a genuinely frightening one
> without.
>
> And I would be honest about what it does not give you. It checks your code
> against itself, not against reality — so it is not a substitute for validating
> data at the point it enters the system.

---

# Part N — Validation Checklist

- [ ] I can explain, without notes, what happens to a type annotation before
      the program runs, and the two consequences of that. *(B.1)*
- [ ] I can explain structural typing and why it made TypeScript adoptable.
      *(B.4)*
- [ ] I can say when to annotate and when to let inference work, with a reason.
      *(C.2)*
- [ ] I can write an interface with a required field, an optional field, and a
      literal union, and explain each choice. *(C.5, C.7)*
- [ ] I can explain narrowing and point to the line that does it. *(C.8)*
- [ ] I can explain the difference between `any` and `unknown`, and why `any`
      at a network boundary is backwards. *(C.10)*
- [ ] I can explain why `as` is a promise rather than a check, using the
      `localStorage` example. *(C.11, K13)*
- [ ] I can explain what `strictNullChecks` prevents and why it is worth the
      errors it produces. *(D.2)*
- [ ] I can retell the `workspaceId` incident: the mechanism, why fixing the
      call site was insufficient, and why `tsc --noEmit` proved more than a test
      could. *(E, K14)*
- [ ] I can explain why the backend validates at runtime while the frontend
      checks at compile time, and why both are right. *(F.3)*
- [ ] I can read a TypeScript error and say which of the two types is wrong.
      *(H.3)*
- [ ] I completed J11, J13 and J15 with written reasoning.
- [ ] **The real test:** open
      [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts) and read the first
      forty lines — the `Document`, `EvidenceChunk`, `TracingDiagnostics` and
      `QueryResponse` interfaces. For every field, say what its type means, why
      it is optional or required, what it would break if it were wrong, and
      whether anything actually checks it when the data arrives.

If the last box is ticked, you can read the typed frontend of this system with
confidence — and Chapter 21 can be about React's ideas rather than about the
punctuation surrounding them.

---

*Next: [10-sql-from-zero.md](10-sql-from-zero.md) — the language of the
database: tables, rows, keys, joins, indexes and transactions, taught before any
tool that hides them.*
