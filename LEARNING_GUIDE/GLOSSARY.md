# Glossary

Every technical word used in this course, explained in one simple sentence.
A term is added here the first time it appears in a chapter.

Sorted A–Z. The "First seen" column tells you which chapter introduced it,
so you can go back and read it in context.

| Term | Simple explanation | First seen |
|---|---|---|
| **0.0.0.0** | Used when a server starts, it means "accept connections arriving on any of my network interfaces". | 05 |
| **127.0.0.1 (localhost)** | The address meaning "this same machine"; traffic to it never leaves the computer. | 05 |
| **ACID** | The four promises a transaction makes: atomicity, consistency, isolation, durability. | 10 |
| **ADR (Architecture Decision Record)** | A short written note recording one decision, the options rejected, and why. | 02 |
| **Agent (AI agent)** | A loop around a language model, plus tools it may use and a stopping condition, working towards a goal. | 04 |
| **Acknowledgement (queue)** | A worker telling the broker "I have finished with this message; you may forget it". | 12 |
| **Alembic** | The tool that version-controls a database schema: ordered, recorded, reversible changes. | 14 |
| **Aliasing** | Two names referring to the same object, so a change made through one is visible through the other. | 06 |
| **Autogenerate** | Alembic comparing your models to the live database and writing a draft migration — which must always be read before running. | 14 |
| **At-least-once delivery** | Acknowledging after the work, so a crash means the job is repeated rather than lost. | 12 |
| **At-most-once delivery** | Acknowledging before the work, so a crash means the job is lost rather than repeated. | 12 |
| **any** | The TypeScript type that switches off checking for a value; not "some type" but "stop checking". | 09 |
| **API** | A defined way for one program to use another, meant for programs rather than people. | 05 |
| **Architectural decay** | The slow drift of a system away from its intended structure, because no one is responsible for noticing. | 04 |
| **Argument** | The actual value passed into a function when you call it. | 06 |
| **Array** | An ordered list of values, counted from zero. | 08 |
| **Arrow function** | JavaScript's short way of writing a function, `x => x * 2`, which also avoids the `this` confusion. | 08 |
| **ASCII** | An old agreement mapping 128 numbers to English letters, digits and punctuation. | 05 |
| **ASGI** | The Python standard for asynchronous web applications, where a request can pause and a response can be sent in several messages. | 13 |
| **Assertion (type assertion)** | Telling the type checker to believe a value is a certain type; a promise it cannot verify, not a check. | 09 |
| **Alerting** | Being told automatically when a measured signal crosses a threshold, instead of finding out from users. | 17 |
| **Artifact** | The deployable output of a build — here, a container image. | 17 |
| **Assignment** | Attaching a name to a value, written with a single `=`. | 06 |
| **Asymmetric encryption** | Encryption with a key pair, where what one key locks only the other can unlock. | 05 |
| **async def** | Defines a coroutine function: calling it builds a paused computation instead of running the body. | 07 |
| **async for** | Looping over an async generator, where getting each next value may need to wait. | 07 |
| **async generator** | A coroutine containing `yield` that produces values over time, waiting between them. | 07 |
| **async with** | A `with` block whose setup and cleanup steps are allowed to wait. | 07 |
| **asyncio** | Python's standard library for asynchronous programming: the event loop, tasks, timeouts and locks. | 07 |
| **Attribute** | A piece of data stored on an object, reached with a dot. | 06 |
| **await** | Suspends the current function and hands control back to the event loop until the awaited thing is ready. | 07, 08 |
| **Authentication** | Checking who someone is. | 15 |
| **Authorisation** | Checking what someone is allowed to do. | 15 |
| **Availability** | The fraction of time a system is working, often written as "nines" such as 99.9%. | 02 |
| **Back-of-the-envelope estimate** | A rough calculation done in a minute to find the right order of magnitude before choosing anything. | 02 |
| **Backend** | The program running on a server that receives requests and does the real work. | 01 |
| **Backpressure** | The way a slow reader tells a fast writer to slow down, so data does not pile up between them. | 03 |
| **Batching** | Collecting several small pieces of work and doing them together to get more done per second. | 02 |
| **Beat (Celery Beat)** | A small program that starts scheduled jobs at fixed times, like an alarm clock for the system. | 01 |
| **Binary** | Writing numbers using only 0 and 1, because hardware can tell two states apart reliably. | 05 |
| **bcrypt** | A password-hashing algorithm that adds a salt automatically and is deliberately slow. | 15 |
| **Bind (a port)** | A program telling the operating system "deliver anything arriving for this port to me". | 05 |
| **Bit** | One single 0 or 1, the smallest piece of information a computer stores. | 05 |
| **Blast radius** | How much of a system is affected when one change or one failure goes wrong. | 02 |
| **Blocking** | A call that does not return until it finishes, during which its thread can do nothing else. | 07 |
| **Blocking generator** | An object you ask for items one at a time, where each request waits and does not let other work run. | 03 |
| **Bottleneck** | The one slowest or scarcest part that limits how fast the whole system can go. | 02 |
| **Branch** | A separate line of commits, so unfinished work does not affect the main line. | 05 |
| **Attention** | The mechanism by which a model compares every token with every other, which is why context windows are limited. | 16 |
| **Backoff (exponential)** | Waiting longer after each failed attempt, so retries do not hammer something already struggling. | 12 |
| **Bi-encoder** | A model that embeds question and document separately so results can be precomputed; fast, less accurate. | 16 |
| **BM25** | The classic keyword scoring method: more occurrences help, rare words matter more, shorter documents rank higher. | 16 |
| **Broker** | The program that holds the queue, accepting messages from producers and handing them to consumers. | 12 |
| **B-tree** | The usual index structure: a sorted tree of signposts, so a lookup touches a few levels instead of every row. | 10 |
| **Build step** | A tool that turns source files into the single, plain output a browser can actually run. | 08 |
| **Byte** | Eight bits together, able to hold 256 different values; one English character in older encodings. | 05 |
| **Bytecode** | The intermediate instructions Python compiles your text into, which its interpreter then runs. | 06 |
| **Bystander effect (diffusion of responsibility)** | When two or more parties partly cover a job, so each assumes the other did it and nobody does. | 04 |
| **C10K problem** | The historic challenge of serving ten thousand simultaneous connections on one machine. | 07 |
| **Cache** | A store of already-computed results, kept so the same request can be answered without repeating the work. | 11 |
| **Cache hit / miss** | A hit is finding the value already stored; a miss is not finding it, so the work runs. | 11 |
| **Cache penetration** | Repeated requests for something that does not exist, which miss every time and reach the database every time. | 11 |
| **Cache stampede** | Many requests missing at once when a popular entry expires, all starting the same expensive work together. | 11 |
| **Callback** | A function you hand to something else so it can call you back when an event happens. | 08 |
| **Callback hell** | Deeply nested callback functions, where ordinary loops, returns and error handling stop working normally. | 07 |
| **Cancellation** | Stopping work whose result is no longer wanted, delivered as an error at the coroutine's next suspension point. | 07 |
| **Celery** | A Python tool that lets one program hand slow jobs to another program to do later. | 01 |
| **Certificate** | A signed document saying which public key belongs to which website name. | 05 |
| **Certificate authority** | An organisation that browsers already trust, whose signature makes a certificate believable. | 05 |
| **CHECK constraint** | A database rule rejecting any row whose values fall outside an allowed condition. | 10 |
| **Choke point** | The one place every path must pass through to do something, so a rule can be enforced once instead of many times. | 03 |
| **Chunk** | A small piece of a document's text, cut so that it fits an AI model and can be searched on its own. | 01 |
| **CI (continuous integration)** | A fresh machine that installs everything and runs the tests automatically on every push. | 05 |
| **Circuit breaker** | A protection that stops accepting requests after too many failures, to avoid making things worse. | 05 |
| **Citation** | A pointer in an answer saying which document and page the information came from. | 01 |
| **Class** | A description of a new kind of object: what data it holds and what it can do. | 06 |
| **Class (of bug)** | The family of bugs that share one cause, as opposed to one single occurrence. | 03 |
| **Client** | A program that makes requests; a role, not a machine. | 05 |
| **Closure** | A function that keeps access to the variables that existed where it was written, even after that code has finished. | 08 |
| **Coercion (type coercion)** | Silently converting one kind of value into another before comparing or combining them. | 08 |
| **Cold start** | Starting from nothing: for a serverless function, the delay before it can answer; for an agent, beginning with no memory of anything earlier. | 02, 04 |
| **Commit** | One saved snapshot of a project, with a message saying why it changed. | 05 |
| **Compiler** | A program that turns your whole source file into machine instructions before it is run. | 06 |
| **Comprehension** | A compact way to build a list, dictionary or set from another collection in one expression. | 06 |
| **Component** | One named part of a system with one clear job, which could be replaced by something else doing that job. | 02 |
| **Component diagram** | A picture showing what parts exist and which parts talk to each other. | 02 |
| **Concurrency** | Dealing with many things at once by switching between them, without necessarily doing two at the same instant. | 05 |
| **Constraint** | Something you do not get to choose: a budget, a deadline, a platform limit, a legal rule. | 02 |
| **Container** | A sealed box holding a program plus everything it needs to run, so it behaves the same on every computer. | 01 |
| **Context manager** | An object used with `with`, which guarantees its cleanup step runs however the block ends. | 06 |
| **Context pollution** | Filling an agent's working space with material that is not relevant, which makes its answers worse. | 04 |
| **Context variable** | A value stored so that it is private to one request or task, and not shared with others running at the same time. | 03 |
| **Context window** | The maximum amount of text a model can hold in view at one time, counted in tokens. | 04 |
| **Contract (API contract)** | The agreed set of names and shapes that two sides of a system both must use, or they stop understanding each other. | 01 |
| **Cooperative multitasking** | Work switches only when a task voluntarily yields; the scheduler cannot interrupt it. | 07 |
| **Configuration drift** | The same setting having different values in different places, with nobody noticing. | 17 |
| **Coordinator (main thread)** | The single component that plans, implements, routes findings and verifies results; specialists report to it. | 04 |
| **Cookie** | A small piece of data the server gives your browser, which the browser sends back on every later request. | 01 |
| **Core (CPU core)** | One independent copy of the instruction-following machinery, letting a CPU truly do several things at once. | 05 |
| **Coroutine** | A paused computation that can suspend itself and resume later with its local variables intact. | 07 |
| **Correction of error** | A written analysis after a defect that fixes the mechanism which allowed it, not only the defect. | 04 |
| **Context poisoning** | Getting a document into the searchable corpus so it is retrieved and influences answers, without touching any code. | 16 |
| **Correlation id** | A unique number attached to one request so all its log lines can be found together later. | 02 |
| **Cosine distance** | A number saying how different two lists of numbers point in direction; small means similar meaning. | 01 |
| **CPU** | The part of a computer that follows instructions, one after another, billions of times a second. | 05 |
| **CPU-bound** | Work limited by how fast the processor can compute; async does not help it. | 07 |
| **Cross-encoder** | A model that reads the question and one passage together and scores the pair; slower but more accurate than comparing embeddings. | 02 |
| **Cross-encoder** | A model that reads question and passage together and scores the pair; much more accurate, far slower, cannot be precomputed. | 16 |
| **CSRF** | An attack where another website makes your browser send a request to this site using your cookie. | 01 |
| **CSRF token** | A secret value the real website knows and an attacker's page cannot read, sent along to prove the request is genuine. | 01 |
| **CTE (common table expression)** | A named sub-query written with `WITH`, so a multi-step query stays readable. | 10 |
| **Custom event** | A named message broadcast inside the browser so unrelated parts of an app can react without importing each other. | 08 |
| **Database** | A program that stores data in an organised way and answers questions about it quickly. | 01 |
| **Dataclass** | A class whose boilerplate (`__init__`, printing, equality) is written for you by a decorator. | 06 |
| **Dead-letter queue** | A separate place failed messages are kept after too many attempts, so a human can inspect and replay them. | 12 |
| **Deadlock** | Two transactions each holding what the other needs, so neither can proceed until one is killed. | 10 |
| **Defence in depth** | Several independent controls, so one failing does not open the door. | 15 |
| **Dependency injection** | A function declaring what it needs instead of fetching it, and the framework providing it. | 13 |
| **Decoupling** | Two parts working through a shared queue or contract, so neither needs to know the other exists. | 12 |
| **Decorator** | A function that takes a function and returns a replacement with extra behaviour, written with `@` above a definition. | 06 |
| **Denormalisation** | Deliberately storing the same value in two places so a common query does not need a join. | 02 |
| **Destructuring** | Pulling several values out of an object or array into named variables in one line. | 08 |
| **Deterministic failure** | A failure that will happen again in exactly the same way if you retry with the same input. | 04 |
| **Diff** | The difference between two versions: which lines were added and which removed. | 05 |
| **DNS** | The system that turns a name like `example.com` into an IP address. | 05 |
| **Docker Compose** | A tool that starts several containers together with one command, using one configuration file. | 01 |
| **Docstring** | A string at the top of a function, class or module that documents it and travels with the code. | 06 |
| **Document** | One uploaded file (or pasted text) that the system can read and answer from. | 01 |
| **DOM** | The tree of objects the browser builds from a page, which JavaScript changes to change the screen. | 08 |
| **DRY (don't repeat yourself)** | The rule against duplicating a piece of knowledge; it assumes every reader can see the shared copy. | 04 |
| **Dunder method** | A method with double underscores at both ends, which Python calls for you at defined moments, such as `__init__`. | 06 |
| **Dynamic checking** | Checking that values are used correctly while the program runs. | 09 |
| **Driver (database)** | The low-level library that speaks the database's network protocol, such as asyncpg or psycopg2. | 14 |
| **Durability** | The promise that data you accepted will still be there later, even after crashes. | 02 |
| **Eager loading** | Fetching related rows along with the main ones, on purpose, instead of when they are first touched. | 14 |
| **Engine** | The SQLAlchemy object that knows how to reach the database and owns the connection pool. | 14 |
| **Dynamic typing** | Not declaring types in advance; a name may refer to different kinds of value over time. | 06 |
| **ECMAScript** | The official name of the JavaScript standard, so that no single company owns it. | 08 |
| **Embedding** | A list of numbers that represents the meaning of a piece of text, so similar meanings give similar numbers. | 01 |
| **Encoding (character)** | The agreed rule for turning characters into bytes and back, such as UTF-8. | 05 |
| **Endpoint** | One specific address on the server that accepts requests, such as `/query/stream`. | 01 |
| **Enum** | A named, fixed set of allowed values, so a typo becomes an error instead of bad data. | 06 |
| **Enumeration oracle** | Any difference in a reply that lets an attacker learn which identifiers really exist. | 03 |
| **Environment variable** | A named piece of text the operating system hands to a program when it starts. | 05 |
| **ER diagram** | A picture showing the stored data as tables and the relationships between them. | 02 |
| **Erasure (type erasure)** | Removing every type annotation before the program runs, so types cost nothing and check nothing at runtime. | 09 |
| **Escalation tag** | The label on a blocker saying who can act on it: the agent, someone with access, or someone who must decide. | 04 |
| **Event listener** | A function registered to run when a named event happens, which must be removed when it is no longer needed. | 08 |
| **Event loop** | The scheduler that runs one piece of work at a time, parks whatever is waiting, and resumes it when its data arrives. | 07 |
| **Event loop starvation** | When one piece of code holds the single shared thread so long that every other request is frozen. | 03 |
| **Eviction policy** | The rule deciding what a full cache throws away, such as the least recently used key. | 11 |
| **Exception** | Python's way of saying "I cannot continue normally here", which stops the current line and travels up to a handler. | 06 |
| **Exclusion constraint** | A database rule that forbids two rows from overlapping, used to make double-booking impossible. | 03 |
| **Executor (thread pool)** | A group of worker threads that blocking work can be handed to, so the event loop stays free. | 07 |
| **Exit code** | The number a finished program reports; 0 means success, anything else means failure. | 05 |
| **EXPLAIN** | The command that shows how the database plans to run a query, and with `ANALYZE`, what it actually cost. | 10 |
| **Expression** | Anything that produces a value, such as `2 + 3` or a function call. | 06 |
| **f-string** | A string prefixed with `f` where anything inside `{ }` is evaluated and inserted. | 06 |
| **FastAPI** | A Python web framework built on Starlette and Pydantic, which uses type annotations for validation, serialisation and documentation. | 13 |
| **Fail-closed** | When something is missing or uncertain, refuse rather than allow. | 03 |
| **Fail-open** | When something is missing or uncertain, allow or continue rather than refuse. | 03 |
| **Failing fast** | Crashing immediately on a bad configuration instead of starting up in a broken or unsafe state. | 02 |
| **fetch** | The browser's function for making an HTTP request; it rejects only if no answer could be obtained at all. | 08 |
| **File** | A named sequence of bytes stored on a disk. | 05 |
| **Floor division** | Division with `//` that discards the remainder and gives a whole number. | 06 |
| **Folder (directory)** | A file that holds a list of other files and folders. | 05 |
| **Foreign key** | A column that points at a row in another table, so the database can keep the link honest. | 02 |
| **Fork** | Creating a new process by copying an existing one, which also copies its open files and connections. | 05 |
| **Frontend** | The part of the app that runs inside the user's browser and draws the screen. | 01 |
| **Full-text search** | Searching by the actual words in text, the way a search box in a document reader works. | 01 |
| **Function** | A named, reusable group of instructions. | 06 |
| **Functional requirement (FR)** | Something the system must do, written as an action a user can check. | 02 |
| **Future** | A placeholder for a value that is not ready yet; a Task is one kind of Future. | 07 |
| **gather** | Runs several coroutines concurrently and waits for all of them, returning results in argument order. | 07 |
| **Generator** | A function containing `yield` that produces values one at a time, on demand, without building them all. | 06 |
| **Generic** | A type with a placeholder that is filled in at each use, such as `Promise<Document[]>`. | 09 |
| **GIL (Global Interpreter Lock)** | A rule inside Python allowing only one thread to run Python code at a time. | 06 |
| **Git** | A program that records snapshots of a folder over time, with a message explaining each change. | 05 |
| **GitHub** | A website that hosts copies of Git repositories and adds collaboration features. | 05 |
| **Graceful shutdown** | Finishing current work before stopping, instead of being cut off mid-request. | 05 |
| **Golden set** | A fixed collection of questions with known correct answers and sources, used to measure whether a change helped. | 16 |
| **Grounded answer** | An answer built only from text found in the user's own documents, with a pointer back to the source. | 01 |
| **Groundedness** | Whether every claim in an answer is supported by the supplied evidence. | 16 |
| **Hallucination** | A model producing fluent, confident text that is not true — the expected result of optimising for likely rather than true. | 16 |
| **Guard (regression guard)** | A test written to stop one specific bug ever coming back; it counts only once you have watched it fail. | 03 |
| **Handoff chain** | A written rule saying which component takes over after another finishes, such as detection then verdict. | 04 |
| **Hash function** | A function turning any input into a short fixed-length fingerprint, where the same input always gives the same result. | 11 |
| **HttpOnly** | A cookie flag meaning JavaScript cannot read it, so a script-injection bug cannot steal the session. | 15 |
| **Hash table** | The structure behind a dictionary, where a key is turned into a number saying roughly where to look. | 06 |
| **Header (HTTP)** | A `Name: value` line carrying information about a request or response. | 05 |
| **Heartbeat test** | A test that ticks a counter every few milliseconds to prove the event loop was never blocked. | 07 |
| **HNSW** | A layered neighbour graph used to find similar vectors quickly, at the cost of being approximate. | 10 |
| **Hit rate** | The share of cache accesses that find a value; the number that decides whether a cache is worth having. | 11 |
| **Horizontal scaling** | Handling more load by running more machines or more copies of a program. | 02 |
| **HSTS** | A response header telling the browser never to contact this site over plain HTTP again. | 05 |
| **HTTP** | The set of rules browsers and servers use to talk to each other over the internet. | 01 |
| **HTTP method** | The word at the start of a request saying what kind of action it is: GET to read, POST to send, and others. | 01 |
| **HTTP status code** | A number in the reply saying how it went, such as 200 for success, 401 for not logged in, 402 for payment needed. | 01 |
| **HTTPS** | HTTP running inside TLS, so the conversation is encrypted and the server's identity is checked. | 05 |
| **Idempotency key** | A unique id the client sends so the server can recognise a repeated request and not do the work twice. | 03 |
| **Idempotent** | Doing something twice has the same effect as doing it once, which is what makes retries safe. | 12 |
| **Identity map** | A session's guarantee that one database row is always the same object in memory. | 14 |
| **Image (container image)** | A sealed read-only package of operating-system files, dependencies, code and a start command; a container is one running copy. | 17 |
| **Immutable** | Unable to be changed after it is created; numbers, strings and tuples are immutable in Python. | 06 |
| **Incident story** | A rehearsed one-minute account of a real defect, told as symptom → cause → why it hid → fix → lesson; the most-asked interview question and the hardest to invent. | 18 |
| **Import** | Reusing code written in another file or library. | 06 |
| **In-flight de-duplication** | Storing a running operation's promise so that repeat callers await the same one instead of starting another. | 08 |
| **Index (database)** | An extra data structure that lets the database find matching rows without reading every row. | 02 |
| **Inference (type inference)** | The checker working out a type from the value you assigned, so you do not have to write it. | 09 |
| **Information hiding** | Designing a module so it keeps its most changeable decisions inside itself, where others cannot depend on them. | 03 |
| **Inheritance** | Defining a class as a kind of another class, so it gets that class's behaviour. | 06 |
| **Instance (of bug)** | One single occurrence of a bug at one place in the code. | 03 |
| **Interface** | The agreed way two parts talk: what you send, what you get back. | 02 |
| **Inversion of control** | The framework calling your code rather than your code calling the framework. | 13 |
| **Interpreter** | A program that reads code and performs it as it goes, rather than producing a separate machine-code file. | 06 |
| **Invalidation** | Removing or replacing a cached copy that has stopped being true. | 11 |
| **Invariant** | A fact about the system that must always stay true, or things break in ways that are hard to find. | 01 |
| **I/O-bound** | Work limited by waiting for something outside the processor, such as a database or a network call. | 07 |
| **IP address** | A number identifying one machine on a network. | 05 |
| **Isolation level** | How much one transaction may see of another's unfinished work; PostgreSQL defaults to Read Committed. | 10 |
| **Iterator** | An object that produces items one at a time and remembers where it has reached. | 06 |
| **Join** | Combining rows from two tables by matching a column, such as a chunk to the document it belongs to. | 10 |
| **JSON** | A plain-text way of writing structured data so it can be sent over a network. | 01 |
| **JWT (JSON Web Token)** | A small block of text holding facts about a user plus a mathematical seal proving the server issued it. | 01 |
| **Kernel** | The core of the operating system, the only part with full hardware access. | 05 |
| **Keyword argument** | Passing a value by naming the parameter, such as `top_k=12`, instead of relying on position. | 06 |
| **Latency** | How long one single operation takes, measured in milliseconds. | 02 |
| **Least privilege** | Giving a component the smallest set of powers it needs, so it cannot do damage it was never meant to do. | 04 |
| **Linux** | A free, open-source operating system kernel that runs most servers. | 05 |
| **Literal union** | A type listing the exact allowed values, such as `"light" \| "dark" \| "system"`, so a typo is a compile error. | 09 |
| **Layer (Docker)** | One saved filesystem change in an image; layers are cached, which is why instruction order matters. | 17 |
| **Liveness** | Is the process alive? If not, restart it. | 17 |
| **Load balancer** | A component that spreads incoming requests across several copies of a program. | 02 |
| **Lazy loading** | Fetching related rows only when they are first touched, which hides a network round trip behind an attribute. | 14 |
| **Locality** | The tendency of recently or nearby-used things to be used again, which is the only reason caching works. | 11 |
| **localStorage** | Browser storage that survives closing the browser and is readable by any script on the page. | 08 |
| **Lock** | A control that lets only one holder into a section of code at a time, protecting shared state. | 07 |
| **Logger** | A tool that records messages with a severity level, a timestamp and the module they came from. | 06 |
| **LLM (large language model)** | A model that predicts the next piece of text, over and over; fluency and hallucination both follow from that. | 16 |
| **Lost update** | Two writers each reading a value, computing from it, and writing back, so one change disappears. | 10 |
| **Loud degradation** | The rule that when a feature fails, the system must show or log the failure and never silently pretend it worked. | 01 |
| **Memory hierarchy** | The ladder from registers to cache to RAM to disk to network, each much slower and much bigger than the last. | 05 |
| **Memory leak** | Memory a program takes and never gives back, so its usage grows until it is killed. | 05 |
| **Message broker** | The middleman that holds jobs or messages until another program takes them out. | 02 |
| **Method** | A function that belongs to an object and is called with a dot. | 06 |
| **Microservices** | An architecture where a system is split into many small programs deployed independently. | 02 |
| **Middleware** | Code that runs on every request before the real handler, without the handler having to ask for it. | 01 |
| **Migration** | One recorded, ordered change to a database schema, with a parent and a way to apply it. | 14 |
| **Mixin** | A small class that exists to add one capability to other classes that inherit it. | 06 |
| **Modular monolith** | One deployable application with strong internal boundaries between its parts. | 02 |
| **Module** | One file of code, which can be imported by others; anything it does not export stays private to it. | 06, 08 |
| **Monolith** | One single deployable program containing the whole application. | 02 |
| **Multi-agent system** | Several agents, each with its own responsibility, working on one larger task under some coordination. | 04 |
| **Multi-tenant** | One running copy of the software serving many separate customers, where no customer can see another's data. | 01 |
| **Mutable** | Able to be changed after creation; lists, dictionaries and sets are mutable in Python. | 06 |
| **N+1 query problem** | Fetching a list, then querying once per item, turning two round trips into dozens. | 10 |
| **Namespace package** | A folder treated as a package even though it has no `__init__.py` file. | 06 |
| **Narrowing** | Using a check such as `typeof` or a null test to prove which member of a union a value is. | 09 |
| **Negative control** | A check that the thing which should be blocked really is blocked. | 03 |
| **Node.js** | A program that runs JavaScript outside a browser, used here to build and serve the frontend. | 08 |
| **Nominal typing** | Types match only if they have the same declared name; the opposite of structural typing. | 09 |
| **Non-functional requirement (NFR)** | A quality the system must have — fast, available, secure, cheap — rather than something it does. | 02 |
| **Normalisation** | Storing each fact exactly once, so an update cannot leave two versions of the truth. | 10 |
| **null** | JavaScript's value meaning "deliberately nothing". | 08 |
| **Nullish coalescing (`??`)** | Falls back to a default only when a value is `null` or `undefined`, never when it is `0` or `""`. | 08 |
| **Object** | A value that carries both data and the operations belonging to it; in JavaScript, a labelled collection of values. | 06, 08 |
| **Object storage** | A service for storing whole files by name, used instead of putting large files in a database. | 02 |
| **Observability** | Being able to tell what a running system is doing from its logs, metrics and traces, without a debugger. | 02 |
| **OCR** | Reading text out of a picture of text, used for scanned documents. | 01 |
| **Operating system** | A program that manages the machine's hardware and runs your programs for you. | 05 |
| **OpenAPI** | A standard JSON description of an HTTP API, which FastAPI generates automatically from your types. | 13 |
| **ORM** | A library that maps classes to tables and objects to rows, in both directions, so you write code instead of SQL strings. | 14 |
| **Optimistic update** | Showing the expected result on screen immediately, before the server confirms, then replacing it with the real one. | 03 |
| **Optional chaining (`?.`)** | Reaching into something that might not exist, giving `undefined` instead of crashing. | 08 |
| **Orchestration** | The system of rules deciding who does what, in what order, with what inputs, and who checks the result. | 04 |
| **p50 / p95 / p99** | Percentile timings: the value that 50%, 95% or 99% of requests are faster than. | 02 |
| **Package** | A folder of modules that can be imported as one unit. | 06 |
| **Packet** | A small piece of data with an address on it, travelling independently across a network. | 05 |
| **Parallelism** | Genuinely doing several things at the same instant, which needs several CPU cores. | 05 |
| **Parameter** | The name given to an input in a function's definition. | 06 |
| **PATH** | An environment variable listing the folders searched, in order, when you type a command name. | 05 |
| **Path (file)** | The route to a file, written as folder names separated by `/` or `\`. | 05 |
| **PEP 8** | Python's style guide: naming, indentation and layout conventions that make code look consistent. | 06 |
| **Percentile** | A way of describing a spread of numbers by saying what fraction falls below a value. | 02 |
| **Percent-encoding** | Writing a special character in a URL as `%` followed by its value in hexadecimal, such as `@` as `%40`. | 05 |
| **PgBouncer** | A middleman that keeps a small pool of database connections and shares them among many users. | 01 |
| **pgvector** | An add-on for PostgreSQL that lets the database store and compare embeddings. | 01 |
| **PID (process id)** | The number that identifies a running process. | 05 |
| **Pipe** | Connecting one program's output straight into another program's input. | 05 |
| **Pipeline** | A series of stages where each stage's output becomes the next stage's input. | 02 |
| **Pool (connection pool)** | A small set of already-open database connections that requests borrow and return instead of opening new ones. | 02 |
| **Port** | A number from 1 to 65535 saying which program on a machine a message is for. | 05 |
| **Port mapping** | Forwarding a port on your machine to a different port inside a container. | 05 |
| **Polling** | Repeatedly asking "is it ready yet?" instead of being told, which is simple and survives dropped connections. | 12 |
| **Positive control** | A check that the same operation still works for someone who is allowed, proving your blocked result came from the check and not a mistake. | 03 |
| **PostgreSQL** | A well-known, free, reliable database program. | 01 |
| **Preemptive multitasking** | The system interrupts a running task whenever it likes and gives the processor to another. | 07 |
| **Primary key** | The column that uniquely identifies each row, which the database indexes automatically. | 02 |
| **Process** | A running program, with its own private memory that other processes cannot read. | 05 |
| **Process pool** | A group of worker processes used for CPU-heavy work, each with its own interpreter and its own GIL. | 07 |
| **Prefetch count** | How many messages a worker reserves at once; high helps throughput, low helps fairness. | 12 |
| **Producer / consumer** | The part that creates work and puts it on a queue, and the part that takes it off and does it. | 12 |
| **Program** | A file containing instructions, doing nothing until it is run. | 05 |
| **Promise** | A JavaScript object standing for a result that is not ready yet; it is pending, then fulfilled or rejected, once and for all. | 08 |
| **Precision** | Of the results returned, the fraction that are relevant. | 16 |
| **Prompt injection** | An attack where text inside a document tells the AI model to ignore its instructions. | 02 |
| **Protocol** | An agreed format for a conversation: what may be said, in what order, and what it means. | 05 |
| **Prototype** | The hidden object a JavaScript object falls back to when a property is not found on itself. | 08 |
| **Proxy metric** | A number you measure because it is easy, standing in for the one you really care about — and able to look fine while the real thing is broken. | 04 |
| **Pydantic** | A Python library where a class of typed fields validates and converts data at runtime. | 06 |
| **QPS** | Queries per second — a measure of throughput. | 02 |
| **Query planner** | The database component that decides how to run a query, choosing scans, indexes and join methods. | 10 |
| **Queue** | A waiting line of jobs, where one program adds work and another program takes it out to do. | 01 |
| **Queue depth** | How many messages are waiting; the single most useful number for telling whether a system is keeping up. | 12 |
| **Race condition** | A bug where the result depends on which of two things happens first, and both can happen at once. | 03 |
| **Readiness** | Can this process serve traffic right now? If not, stop routing to it — but do not restart it. | 17 |
| **Reverse proxy** | A server that receives requests from the internet, terminates TLS, and forwards them to your application. | 17 |
| **Rolling deployment** | Replacing instances one at a time so the service stays up, which means old and new code run together for a while. | 17 |
| **RBAC** | Role-based access control: permissions attach to roles, and users are given roles. | 15 |
| **RAG** | Retrieval-Augmented Generation: find relevant text first, then let the AI model write using only that text. | 01 |
| **RAM** | Fast working memory that a running program uses, and which forgets everything when power is lost. | 05 |
| **Rate limit** | A cap on how many requests something will accept in a period of time. | 02 |
| **Response model** | A declared output shape that filters a response to exactly those fields, so internal ones cannot leak. | 13 |
| **Router (APIRouter)** | A group of related endpoints that can be attached to an application as one unit, usually with a shared prefix. | 13 |
| **Routing** | Deciding which of your functions handles a given path and method. | 13 |
| **Ratchet** | A test holding a list of known-bad cases that is only ever allowed to get shorter, so things cannot get worse. | 03 |
| **Ready queue** | The event loop's list of work that can run right now. | 07 |
| **Reconciliation** | Replacing a temporary on-screen item with the real one from the server, matched by the same identity. | 03 |
| **Recursion** | A function calling itself, with a condition that eventually stops it. | 08 |
| **Referential integrity** | The guarantee that every link between tables points at a row that really exists. | 10 |
| **Referral** | An existing employee putting your application in front of a human, which usually bypasses the automated CGPA and keyword filters entirely. | 18 |
| **Rubric** | A written scale for judging an answer, so a mock interview produces a score you can act on rather than a feeling. | 18 |
| **Redirection** | Sending a program's output to a file instead of the screen, using `>`. | 05 |
| **Recall** | Of all the relevant results that exist, the fraction that were found. | 16 |
| **Redis** | A very fast in-memory store, used here both as a queue and as a cache. | 01 |
| **Re-entrancy** | A function being started again before the previous run has finished, usually from a second click or a second request. | 03 |
| **Regression** | A thing that used to work and stopped working because of a later change. | 03 |
| **REPL** | An interactive prompt: read a line, evaluate it, print the result, loop. | 06 |
| **Repository (git)** | A folder that Git is tracking, together with its whole history. | 05 |
| **Reranking** | A second, slower and more accurate pass that reorders search results by reading each one against the question. | 01 |
| **REST** | A common style of web API where paths name things and methods say what to do to them. | 05 |
| **RLS (Row-Level Security)** | A database feature where the database itself decides which rows a connection may see. | 02 |
| **Root (user)** | The all-powerful administrative user on a Linux system. | 05 |
| **RRF (Reciprocal Rank Fusion)** | A simple formula that merges two ranked lists using positions instead of scores. | 01 |
| **Scope (variable)** | Where a name is visible; names assigned inside a function are local to it unless declared otherwise. | 06 |
| **Second-order consequence** | The effect of your effect: what happens to everything that depended on the thing you just changed. | 03 |
| **Self** | The first parameter of a method, referring to the object it is being called on. | 06 |
| **Semaphore** | A control allowing up to N holders at once, used to bound how much work runs concurrently. | 07 |
| **Salt** | A random per-user value mixed into a password before hashing, so identical passwords produce different results. | 15 |
| **SameSite** | A cookie flag controlling whether the browser sends it on requests started by another site. | 15 |
| **Sentinel value** | A unique object used to mean "nothing left", chosen so it can never be confused with real data. | 03 |
| **Separation of duties** | The rule that whoever does a piece of work must not be the one who approves it. | 04 |
| **Sequence diagram** | A picture showing who calls whom, in what order, over time. | 02 |
| **Session (ORM)** | A workspace holding a database connection, the objects loaded, and the changes made, which it writes out at commit. | 14 |
| **Serialisation** | Flattening structured data into bytes so it can be stored or sent, and rebuilt later. | 05 |
| **Server** | A program that waits for requests and answers them; a role, not a machine. | 01, 05 |
| **Serverless** | Running code as short-lived functions that a platform starts on demand, with no server to manage. | 02 |
| **sessionStorage** | Browser storage that lasts only until the tab is closed. | 08 |
| **Shell** | The program inside a terminal that reads what you type and runs the matching program. | 05 |
| **Short-circuit** | `and`/`&&` and `or`/`||` stopping as soon as the answer is known, so the second part may never run. | 06 |
| **Shotgun surgery** | The smell where one small change forces edits in many scattered files. | 02 |
| **Signal** | A message the operating system sends to a running process, such as "please stop". | 05 |
| **Signature (digital)** | A mathematical seal made with a secret key, which proves data was not changed. | 01 |
| **Silent failure** | A failure that produces no error and no log, so it looks exactly like success. | 03 |
| **Slice** | Taking part of a sequence with `[start:end]`, where the end is not included. | 06 |
| **Socket** | The programming object representing one end of a network connection. | 05 |
| **Spread (`...`)** | Copying the contents of an object or array into a new one, so the original is left untouched. | 08 |
| **SQL** | The declarative language for asking a relational database what you want, without saying how to get it. | 10 |
| **SQL injection** | An attack where user text becomes part of a query, changing what it means; prevented by parameters. | 10 |
| **SSD** | A storage device that keeps data without power; much slower than RAM, much larger. | 05 |
| **SSE (Server-Sent Events)** | A way for a server to keep a connection open and keep pushing small updates to the browser. | 01 |
| **Standing-defect mode** | Auditing code that nobody has changed, against a stated claim, rather than reviewing a change. | 04 |
| **Statement** | An instruction that does something, such as assigning, deciding or looping. | 06 |
| **Stateless** | A component that keeps nothing important in its own memory between requests, so any copy can serve any request. | 02 |
| **Starlette** | The small ASGI toolkit underneath FastAPI, providing routing, requests, responses and middleware. | 13 |
| **Static checking** | Checking that values are used correctly before the program runs, without executing it. | 09 |
| **Structured logging** | Writing each log line as machine-readable data rather than a sentence, so millions can be searched. | 17 |
| **Static method** | A method that belongs to a class for naming purposes but receives no object state. | 06 |
| **stdin / stdout / stderr** | The three channels every program starts with: input, normal output, and error output. | 05 |
| **Streaming** | Sending an answer piece by piece as it is produced, instead of waiting for all of it. | 01 |
| **strict mode (TypeScript)** | A group of stricter checks, the most valuable being `strictNullChecks`, which makes absence part of the type. | 09 |
| **Structural typing** | Types match if the shape fits, whatever the value is called or where it came from. | 09 |
| **Structured concurrency** | Bounding a task's lifetime to a visible block, so no task can outlive its scope. | 07 |
| **Superset** | A language that adds to another while keeping every existing file valid, as TypeScript does with JavaScript. | 09 |
| **Symmetric encryption** | Encryption where the same shared secret both locks and unlocks; fast, but the secret must be shared first. | 05 |
| **System call** | A formal request from your program to the kernel to do something privileged, like reading a file. | 05 |
| **Task (Celery)** | An ordinary function marked so it can be run later, in another process, from a queued message. | 12 |
| **Task (asyncio)** | A coroutine the event loop has been told to run, so it progresses whenever the loop gets a chance. | 07 |
| **TaskGroup** | A block that runs several tasks and does not exit until all finish, cancelling the rest if one fails. | 07 |
| **TCP** | A protocol that turns unreliable packets into a reliable, ordered stream. | 05 |
| **Template literal** | JavaScript text written in backticks, where `${ }` inserts a computed value. | 08 |
| **Tenant key** | The single field used to decide which customer a row of data belongs to; here it is `owner_id`. | 01 |
| **Terminal** | A window that shows text and accepts typed text. | 05 |
| **Ternary operator** | A compact `if`/`else` that produces a value: `condition ? a : b`. | 08 |
| **Thread** | One line of execution inside a process; threads in a process share memory. | 05 |
| **Three-tier architecture** | The classic split of browser, application server, and database. | 02 |
| **Throughput** | How much work a system completes per unit of time, such as requests per second. | 02 |
| **Temperature** | How much randomness is allowed when picking the next token; low means consistent, high means varied. | 16 |
| **Timeout** | Cancellation on a timer: give up if something has not finished in a set time. | 07 |
| **Timing attack** | Learning a secret from how long a comparison takes, defeated by constant-time comparison. | 15 |
| **TLS** | The protocol that encrypts a connection and proves the server's identity; HTTPS is HTTP inside TLS. | 05 |
| **TOCTOU** | Time-of-check to time-of-use: acting on a value that another request may have changed since you checked it. | 10 |
| **Token (AI)** | A piece of a word; AI models measure and charge text in tokens, not characters. | 01 |
| **Token budget** | A limit on how much evidence text may be sent to the model, because models have a maximum input size. | 01 |
| **Tool grant** | The exact set of actions an agent is allowed to perform; its power is this set and nothing more. | 04 |
| **Trace (distributed)** | A record following one request across components, showing where the time went. | 17 |
| **Traceback** | The printed chain of calls leading to an error, with the actual error on the last line. | 06 |
| **Transaction** | A group of database statements that either all take effect or none do. | 10 |
| **Transient failure** | A failure that may succeed if you simply try again, such as a timeout or a rate limit. | 04 |
| **Trigger mode** | Whether a check is started by a change to the code, or by an audit of code nobody has touched. | 04 |
| **Trust score** | A computed number saying how well the produced answer is supported by the retrieved evidence. | 01 |
| **Truthiness** | Treating non-boolean values as true or false in a condition — convenient, and a trap when the states differ. | 06, 08 |
| **TTL (time to live)** | How long a cached value stays valid before it is thrown away. | 02 |
| **Type hint** | An annotation stating what type a value should be; documentation that tools can check but Python does not enforce. | 06 |
| **TypeScript** | JavaScript plus written-down types, checked by a separate compiler (`tsc`) and erased before the browser sees it. | 09 |
| **UDP** | A protocol that sends packets without guaranteeing order or delivery; used where late data is worthless. | 05 |
| **undefined** | JavaScript's value meaning "nothing has been put here yet", distinct from `null`. | 08 |
| **Ungrounded answer** | An answer the model wrote from its own general training rather than from the user's documents. | 01 |
| **unknown** | The safe version of `any`: it also means "I do not know", but forces you to narrow before use. | 09 |
| **Unicode** | One huge table giving every character in every writing system its own number. | 05 |
| **Unit of work** | Changing objects and letting the session work out which statements to send, and in what order, at commit time. | 14 |
| **Unpacking** | Assigning several names at once from a collection, such as `text, chunks = ...`. | 06 |
| **Uvicorn** | The ASGI server used here: it owns the socket, speaks HTTP, and calls the application. | 13 |
| **User space** | Where ordinary programs run, with no direct hardware access. | 05 |
| **UTF-8** | The dominant rule for turning Unicode characters into bytes; old English text is already valid UTF-8. | 05 |
| **Variable** | A name that refers to a value in memory. | 06 |
| **Vertical scaling** | Handling more load by using one bigger machine with more CPU and memory. | 02 |
| **Virtual environment** | A private folder holding one project's own Python interpreter and libraries. | 05 |
| **void** | The return type of a function that produces nothing useful. | 09 |
| **Volume (Docker)** | Storage that lives outside a container so files survive the container being replaced. | 05 |
| **Waiting set** | The event loop's record of paused work and what each piece is waiting for. | 07 |
| **WAL (write-ahead log)** | A sequential log the database writes before changing data files, so a crash can be replayed and nothing committed is lost. | 10 |
| **Web framework** | A program that handles everything between the network and your logic, and calls your code rather than being called by it. | 13 |
| **Working directory** | The folder a program is currently "standing in", which relative paths are measured from. | 05 |
| **WSGI** | The older Python web standard: an application is one synchronous function returning a whole response. | 13 |
| **Worker** | A separate running program that takes jobs from a queue and does slow work outside the web request. | 01 |
| **Workspace** | One mode of this app (General, HR, Legal, Finance, Study, Research, Exam) sharing code but differing in prompts and rules. | 01 |
| **Wrapper** | A function that adds extra behaviour around another function so callers do not repeat that behaviour. | 01 |
| **Write-through** | Updating the cache at the same moment as the database, so the copy is never stale. | 11 |
| **XSS (cross-site scripting)** | Getting your own JavaScript to run on someone else's page, usually by supplying text that is displayed without being neutralised. | 15 |
| **YAML** | A human-friendly configuration format, used by Docker Compose and CI files. | 05 |
| **Zero trust** | Assuming nothing is safe merely because it is "inside", so every request re-establishes identity and permission. | 15 |
| **yield** | The keyword that makes a function a generator, handing over one value and freezing until asked for the next. | 06 |
