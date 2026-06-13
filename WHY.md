# Why Naet Exists 🙃

I'll be honest — this started because my university portal was terrible.

Not "could be better" terrible. Genuinely, frustratingly, embarrassingly bad.
Slow on a good day, broken on a bad one, completely useless offline, and somehow
managing to make every interaction feel like it was designed to discourage you
from using it. Checking your fee balance felt like filing a tax return.
Registering for units required a specific browser, a specific time of day,
and apparently the right phase of the moon.

I'm a CS student. I got curious. How hard could it actually be to build
something better?

---

## The problems I kept running into

### 🏚️ The existing systems feel abandoned

Most student portals at Kenyan universities feel like they were built in 2008
and never touched again. The UX assumptions are decade-old. The data models
are rigid. Changing anything requires a vendor contract, a procurement process,
and six months of waiting.

Meanwhile students are on smartphones, expecting the same experience they get
from M-Pesa or their bank app. The gap between expectation and reality is
enormous and nobody seems embarrassed by it.

---

### 🔌 ERP integration is always an afterthought

Every institution I've looked at has the same problem — the student portal
and the finance/HR/academic ERP system don't talk to each other properly.
A student pays fees through the portal, but the finance ledger doesn't know
about it until someone manually reconciles the records at the end of the week.
Results get published in the academic system but students find out through
a notice board.

These systems exist in parallel universes and the students are the ones
who suffer the inconsistency — told their account is cleared by one system
and flagged as owing by another.

Naet treats ERP integration as a first-class concern, not something
bolted on later. Every confirmed payment, enrollment change, deferment, and
published result can automatically notify any external system through a
pluggable event-driven layer. The integration is generic by design — it
doesn't care whether you're syncing to SAP, Oracle, a homegrown PHP system,
or a Google Sheet. You write one class, register it, and it works.

---

### 📶 Offline is not optional in Kenya

The assumption that users have reliable internet is a Silicon Valley assumption.
It doesn't hold in a rural Kenyan campus, or during load shedding, or when
200 students are all trying to check their results at the same time on the
campus WiFi.

A student who can't check their fee balance because the network is down isn't
a edge case — it's Tuesday.

The frontend is built offline-first from the ground up. Service workers cache
the page shells. IndexedDB stores the last known state. Background sync queues
actions that couldn't complete. When the connection returns, everything catches
up automatically. Students on 2G get a usable experience. Students offline get
their last known data and a clear indicator of what's stale.

No native app required. This runs in the browser, installs like a PWA if the
student wants, and works across every device they already own.

---

### 🧩 The experience should be seamless, not fragmented

Why does checking your timetable, paying fees, viewing results, and reporting
for a semester all live in different systems with different logins?

The fragmentation isn't accidental — it's the result of institutions procuring
different systems at different times from different vendors, none of which were
designed to work together. The student is left to navigate the seams.

Naet is one system that handles the full student lifecycle —
admission through graduation. One login. One session context. One place to
check everything. And because the integration layer is generic, it can still
talk to all the legacy systems an institution already has.

---

### 🔄 Moving between institutions is harder than it should be

Transfer students exist. Students who move from one university to another
shouldn't have to start from scratch. Academic records, credit transfers,
fee history — these things should be portable.

More importantly, institutions shouldn't have to rebuild a student portal
from scratch every time they want a new one. The core problems — enrollment,
fees, sessions, roles, timetabling — are the same everywhere. Only the
specifics differ.

This is a template precisely because the wheel has been reinvented too many
times. Build on top of something that already solves the common problems.
Configure what's specific to your institution. Extend what needs extending.
Ship faster.

---

### 🔐 Data protection is not someone else's problem

Kenyan universities hold deeply sensitive personal data — national IDs,
family information, financial records, health details — and most of them
have no formal data governance framework for their student systems.

The Kenya Data Protection Act exists. The ODPC is actively enforcing it.
Institutions that haven't thought about this are exposed.

This template bakes compliance thinking in from the start — UUID primary keys,
role-scoped access, audit trails on financial records, consent tracking,
student data rights, documented retention policies. Not as a checkbox, but
as part of how the system is designed. An institution deploying this starts
ahead of where most are today.

---

## The honest reasons 🙈

Beyond all the problem statements, there are simpler reasons this exists:

**Curiosity.**
I wanted to know if I could build it. The domain is genuinely interesting —
session rollovers, fee engine logic, role hierarchies — these are not trivial problems and solving them taught
me more than any coursework.

**Frustration is a great motivator.**
I used a bad portal for years. The best way to stop complaining about a
problem is to build the solution.

**Because the template didn't exist.**
There are school management systems. There are none that are Django-native,
offline-first, built with the Kenyan institutional context in mind,
pluggable by design, and open source. This is that thing.

**Because I can.**
That's enough of a reason.

---

## What this is not 😈

This is not a finished product waiting for an institution to deploy it as-is.
It's a template — opinionated enough to give you a strong foundation,
generic enough that the institution-specific parts are clearly separated
from the core.

It's not trying to replace Ellucian or SAP or whatever enterprise ERP
your institution already has. It's trying to be the layer that students
actually interact with — and to make that layer good.

It's not claiming to have solved every problem. The analytics module is
a roadmap item. The exam scheduling optimisation is a hard problem.
The mobile app doesn't exist yet. This is honest about what it is
and what it isn't.

---

## What this could become 🤞🏿

Every Kenyan public university has a student portal.
Most of them are bad in the same ways for the same reasons.

If one institution deploys this and it works, and shares what they changed,
and another institution benefits from that — that's the point.
That's what open source is for.

If a developer somewhere finds the offline-first frontend pattern useful
and lifts it for a completely different project — also fine.

If this just ends up being the best thing I built as a student —
that's enough too.

---

_Built with curiosity and mild institutional frustration._
_by yours truly Bett🙃_
_Kenya 🇰🇪 — 2026_

<a href="README.md#️-tech-stack" >Okay back you go → </a>
